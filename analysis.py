"""Permit Clock analysis: stage durations and summaries from cached APR Table A2 (OC).

Source: HCD Housing Element APR Table A2, data.ca.gov, resource fe505d9b-8c36-42ba-ba30-08bc4f34e022
(see data/SOURCES.json). Prototype only.

Stage 1 = entitlement approval -> building permit issued (days).
Stage 2 = building permit issued -> certificate of occupancy (days).
Only same-row date pairs are used here. Cross-year linking is reported by link_counts().
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).parent / "data"
# ASSUMPTION: minimum sample size for a benchmark. Below this a cell is "unknown".
MIN_N = 30
DAYS_PER_MONTH = 30.4375  # average Gregorian month length
STAGES = {"ent_to_permit": ("ENT_APPROVE_DT1", "BP_ISSUE_DT1"),
          "permit_to_co": ("BP_ISSUE_DT1", "CO_ISSUE_DT1")}
UNKNOWN = "unknown"


def load_a2(path: Path | str = DATA_DIR / "oc_apr_a2.csv") -> pd.DataFrame:
    return pd.read_csv(path, dtype=str)


def add_durations(df: pd.DataFrame) -> pd.DataFrame:
    """Add parsed dates, day counts per stage, and flags. Does not drop rows.

    <stage>_days is NaN when either date is missing or the duration is negative.
    <stage>_negative marks negative durations (dropped from stats, counted by count_negatives).
    <stage>_same_day marks a 0-day duration (e.g. Anaheim/Fullerton pattern; reporting pattern
    is INFERRED, not confirmed).
    """
    out = df.copy()
    for col in {c for pair in STAGES.values() for c in pair}:
        out[col + "_parsed"] = pd.to_datetime(out[col], errors="coerce")
    for name, (a, b) in STAGES.items():
        days = (out[b + "_parsed"] - out[a + "_parsed"]).dt.days
        out[name + "_negative"] = days < 0
        out[name + "_same_day"] = days == 0
        out[name + "_days"] = days.where(days >= 0)
    return out


def count_negatives(df: pd.DataFrame) -> dict[str, int]:
    return {name: int(df[name + "_negative"].sum()) for name in STAGES}


def _pcts(values: np.ndarray) -> dict[str, float]:
    return {f"P{p}": float(np.percentile(values, p)) / DAYS_PER_MONTH for p in (25, 50, 75, 80)}


def summary(df: pd.DataFrame, city: str, unit_cat: str | None, stage: str,
            min_n: int = MIN_N) -> dict:
    """Months P25/P50/P75/P80, n, coverage % and same-day share for a city x unit category.

    df must come from add_durations. unit_cat None means all categories. Returns
    {"n", "coverage_pct", "same_day_pct", "P25".."P80"} with the percentiles set to "unknown"
    when n < min_n. coverage_pct = rows with a usable duration / rows for that city and category.
    """
    sub = df[df["JURIS_NAME"].str.upper() == city.upper()]
    if unit_cat is not None:
        sub = sub[sub["UNIT_CAT"] == unit_cat]
    vals = sub[stage + "_days"].dropna().to_numpy()
    n = len(vals)
    res = {"n": n,
           "rows": len(sub),
           "coverage_pct": round(100 * n / len(sub), 1) if len(sub) else UNKNOWN,
           "same_day_pct": round(100 * float((vals == 0).mean()), 1) if n else UNKNOWN}
    if n < min_n:
        res.update({k: UNKNOWN for k in ("P25", "P50", "P75", "P80")})
    else:
        res.update(_pcts(vals))
    return res


def link_counts(df: pd.DataFrame) -> dict[str, int]:
    """How many records appear in more than one report year, by key.

    Method 1: (JURIS_NAME, JURS_TRACKING_ID). Method 2: (JURIS_NAME, APN).
    Counts keys seen in 2+ distinct YEARs. Blank keys are ignored. These are matches of
    identifiers only; the app does not use them yet (same-row pairs only).
    """
    res = {}
    for label, key in (("tracking_id", "JURS_TRACKING_ID"), ("apn", "APN")):
        sub = df[df[key].notna() & (df[key].str.strip() != "")]
        years = sub.groupby(["JURIS_NAME", key])["YEAR"].nunique()
        res[label] = int((years >= 2).sum())
    return res


if __name__ == "__main__":
    d = add_durations(load_a2())
    print("negative durations dropped:", count_negatives(d))
    print("cross-year links:", link_counts(d))
    for city in ("TUSTIN", "SANTA ANA"):
        for st in STAGES:
            print(city, st, summary(d, city, None, st))
