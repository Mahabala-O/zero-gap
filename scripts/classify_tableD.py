"""Classify OC 2025 APR Table D permitting programs (build step 4).

The only script that spends API credits. Skips if data/tableD_classified.csv exists.

  python scripts/classify_tableD.py            # Claude Haiku if a key is set, else keyword rules
  python scripts/classify_tableD.py --keyword  # keyword rules only, no API call

Outputs:
  data/tableD_classified.csv  Claude labels (method = "claude-haiku-5-5"), source text kept
  data/tableD_keyword.csv     keyword-rule labels (method = "keyword match, not reviewed"),
                              written when no API key is available
  data/tableD_handcheck.csv   20 random rows for a person to check (blank "correct?" column)

The key is read from the environment or .env (python-dotenv). It is never printed or logged.
Prototype only. Labels describe what the city wrote; they do not judge compliance.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SRC = DATA / "oc_apr_tableD.csv"
OUT_CLAUDE = DATA / "tableD_classified.csv"
OUT_KEYWORD = DATA / "tableD_keyword.csv"
OUT_HANDCHECK = DATA / "tableD_handcheck.csv"

MODEL = "claude-haiku-5-5"
# Price per 1M tokens for claude-haiku-5-5 (prompts under 100K tokens), from the Claude API
# skill model table cached 2026-10-06. Used only for the printed estimate.
PRICE_IN, PRICE_OUT = 0.10, 0.50
MAX_EST_USD = 2.00  # refuse to send if the estimate is above this (our cap, not a measurement)
BATCH = 20

CATEGORIES = ["ADU streamlining", "pre-approved plans", "permit-time review",
              "objective standards", "fees", "process/CUP removal", "other"]
STATUSES = ["completed", "ongoing", "delayed", "not started", "unclear"]

KEYWORDS = re.compile(r"ADU|accessory|permit|streamlin|pre-?approved|objective design|"
                      r"objective standard|\bfees?\b|\bCUP\b|conditional use", re.I)

KEYWORD_METHOD = "keyword match, not reviewed"


def load_rows(path: Path = SRC) -> pd.DataFrame:
    """2025 OC Table D rows whose name or objective matches permitting keywords."""
    d = pd.read_csv(path)
    d = d[d["YEAR"] == d["YEAR"].max()].copy()
    text = d["PROGRAM_NAME"].fillna("") + " " + d["PROGRAM_OBJECTIVE"].fillna("")
    d = d[text.str.contains(KEYWORDS)].reset_index(drop=True)
    d.insert(0, "row_id", range(len(d)))
    return d


def parse_target_date(text) -> str | None:
    """ISO date only when the target text holds one unambiguous date; else None."""
    if not isinstance(text, str):
        return None
    m = re.fullmatch(r"\s*(\d{4})-(\d{2})-(\d{2})\s*", text)
    if m:
        try:
            return pd.Timestamp(text.strip()).date().isoformat()
        except ValueError:
            return None
    return None


def keyword_category(name, objective) -> str:
    t = f"{name or ''} {objective or ''}".lower()
    if re.search(r"pre-?approved|standard plan", t):
        return "pre-approved plans"
    if re.search(r"\badus?\b|accessory dwelling", t):
        return "ADU streamlining"
    if re.search(r"objective (design|development)? ?standard|objective design", t):
        return "objective standards"
    if re.search(r"\bcup\b|conditional use", t):
        return "process/CUP removal"
    if re.search(r"\bfees?\b", t):
        return "fees"
    if re.search(r"permit|streamlin|processing time|review time", t):
        return "permit-time review"
    return "other"


def keyword_status(status) -> str:
    if not isinstance(status, str) or not status.strip():
        return "unclear"
    t = status.lower()
    if re.search(r"not (yet )?(started|begun|initiated)", t):
        return "not started"
    if re.search(r"delay|behind schedule|postpone", t):
        return "delayed"
    if re.search(r"\bcomplete[d]?\b|adopted|accomplished", t):
        return "completed"
    if re.search(r"ongoing|in progress|continu|underway", t):
        return "ongoing"
    return "unclear"


def keyword_classify(rows: pd.DataFrame) -> pd.DataFrame:
    out = rows.copy()
    out["category"] = [keyword_category(n, o) for n, o in
                       zip(out["PROGRAM_NAME"], out["PROGRAM_OBJECTIVE"])]
    out["status_bucket"] = out["PROGRAM_STATUS"].map(keyword_status)
    out["target_date"] = out["ACCOMPLISHED_DT"].map(parse_target_date)
    out["method"] = KEYWORD_METHOD
    return out


def validate_labels(items, row_ids) -> dict:
    """Keep only well-formed labels for known row ids; coerce anything else to safe values."""
    good = {}
    for it in items if isinstance(items, list) else []:
        if not isinstance(it, dict) or it.get("row_id") not in row_ids:
            continue
        cat = it.get("category") if it.get("category") in CATEGORIES else "other"
        st = it.get("status_bucket") if it.get("status_bucket") in STATUSES else "unclear"
        td = it.get("target_date")
        td = parse_target_date(td) if isinstance(td, str) else None
        good[it["row_id"]] = {"category": cat, "status_bucket": st, "target_date": td}
    return good


def extract_json(text: str):
    m = re.search(r"\[.*\]", text, re.S)
    if not m:
        return []
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return []


SYSTEM = (
    "You label California housing-element programs from a city's annual progress report. "
    "Use only the text given. Do not guess. For each row return an object with: row_id; "
    f"category, one of {CATEGORIES}; status_bucket, one of {STATUSES} (answer \"unclear\" if "
    "the status text does not say); target_date, an ISO date YYYY-MM-DD only if the target "
    "text states one exact date, otherwise null. Reply with a JSON array only."
)


def batch_prompt(batch: pd.DataFrame) -> str:
    recs = [{"row_id": int(r.row_id), "program": r.PROGRAM_NAME, "objective": r.PROGRAM_OBJECTIVE,
             "target": r.ACCOMPLISHED_DT, "status": r.PROGRAM_STATUS}
            for r in batch.itertuples()]
    return json.dumps(recs, default=str, ensure_ascii=False)


def count_tokens(client, text: str) -> int:
    kwargs = dict(model=MODEL, system=SYSTEM, messages=[{"role": "user", "content": text}])
    try:
        return client.messages.count_tokens(**kwargs).input_tokens
    except AttributeError:
        return client.beta.messages.count_tokens(**kwargs).input_tokens


def claude_classify(rows: pd.DataFrame, client) -> pd.DataFrame:
    batches = [rows.iloc[i:i + BATCH] for i in range(0, len(rows), BATCH)]
    prompts = [batch_prompt(b) for b in batches]
    tin = sum(count_tokens(client, p) for p in prompts)
    tout = len(rows) * 60  # ASSUMPTION: ~60 output tokens per labelled row
    est = tin / 1e6 * PRICE_IN + tout / 1e6 * PRICE_OUT
    print(f"{len(rows)} rows in {len(batches)} batches; {tin:,} input tokens counted, "
          f"~{tout:,} output tokens assumed; estimated cost ${est:.3f}")
    if est > MAX_EST_USD:
        raise SystemExit(f"Estimate above ${MAX_EST_USD:.2f} cap; not sending.")

    labels = {}
    for i, (b, p) in enumerate(zip(batches, prompts), 1):
        ids = set(int(x) for x in b["row_id"])
        resp = client.messages.create(model=MODEL, max_tokens=8000, system=SYSTEM,
                                      messages=[{"role": "user", "content": p}])
        text = "".join(getattr(c, "text", "") for c in resp.content if c.type == "text")
        got = validate_labels(extract_json(text), ids)
        labels.update(got)
        print(f"batch {i}/{len(batches)}: {len(got)}/{len(ids)} labelled")

    out = rows.copy()
    out["category"] = out["row_id"].map(lambda r: labels.get(r, {}).get("category", "other"))
    out["status_bucket"] = out["row_id"].map(
        lambda r: labels.get(r, {}).get("status_bucket", "unclear"))
    out["target_date"] = out["row_id"].map(lambda r: labels.get(r, {}).get("target_date"))
    out["method"] = [MODEL if r in labels else "missing label" for r in out["row_id"]]
    return out


def write_handcheck(df: pd.DataFrame) -> None:
    hc = df.sample(n=min(20, len(df)), random_state=7).copy()
    hc["correct?"] = ""
    hc.to_csv(OUT_HANDCHECK, index=False)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keyword", action="store_true", help="keyword rules only, no API call")
    args = ap.parse_args()

    if OUT_CLAUDE.exists():
        print(f"{OUT_CLAUDE.name} exists; skipping (it spends API credits).")
        return 0
    rows = load_rows()
    print(f"2025 OC Table D permitting-keyword rows: {len(rows)} "
          f"in {rows['JURIS_NAME'].nunique()} jurisdictions")

    key = None
    if not args.keyword:
        try:
            from dotenv import load_dotenv
            load_dotenv(ROOT / ".env")
        except ImportError:
            pass
        key = os.environ.get("ANTHROPIC_API_KEY") or None

    if key:
        import anthropic
        df = claude_classify(rows, anthropic.Anthropic())
        df.to_csv(OUT_CLAUDE, index=False)
        print(f"wrote {OUT_CLAUDE.name}")
    else:
        print("No API key (or --keyword): using keyword rules, labelled "
              f"'{KEYWORD_METHOD}'.")
        df = keyword_classify(rows)
        df.to_csv(OUT_KEYWORD, index=False)
        print(f"wrote {OUT_KEYWORD.name}")
    write_handcheck(df)
    print(df["category"].value_counts().to_string())
    print(df["status_bucket"].value_counts().to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
