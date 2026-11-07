"""Download the Orange County extracts of the state Annual Progress Report (APR) tables.

Source: California Department of Housing and Community Development (HCD) Annual Progress
Report data on data.ca.gov, read through the documented CKAN datastore API
(https://data.ca.gov/api/3/action/datastore_search). Pages politely (sleep between pages).

Writes:
  data/oc_apr_a2.csv      APR Table A2 rows for CNTY_NAME = 'Orange' (address, project name,
                          notes and coordinates dropped)
  data/oc_apr_tableD.csv  APR Table D rows for the 34 OC cities plus ORANGE COUNTY
  data/SOURCES.json       URLs, resource ids, pulled-at time, row counts

Skips the download if the CSVs already exist. Run: python scripts/fetch_apr.py
"""
from __future__ import annotations

import csv
import json
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
API = "https://data.ca.gov/api/3/action/datastore_search"
PAGE = 5000
SLEEP_S = 1.0

A2_ID = "fe505d9b-8c36-42ba-ba30-08bc4f34e022"
D_ID = "37724925-2014-4646-ade8-3ba9f3ff9fb8"

INCOME_COLS = [
    p + s
    for p in ("", "BP_", "CO_")
    for s in (
        "ACUTELY_LOW_INCOME_DR", "ACUTELY_LOW_INCOME_NDR",
        "EXTREMELY_LOW_INCOME_DR", "EXTREMELY_LOW_INCOME_NDR",
        "VLOW_INCOME_DR", "VLOW_INCOME_NDR",
        "LOW_INCOME_DR", "LOW_INCOME_NDR",
        "MOD_INCOME_DR", "MOD_INCOME_NDR",
        "ABOVE_MOD_INCOME",
    )
]
# APN is kept only to link records across report years in analysis.py. It is never shown in the UI.
A2_KEEP = [
    "JURIS_NAME", "YEAR", "APN", "JURS_TRACKING_ID", "UNIT_CAT", "TENURE",
    "ENT_APPROVE_DT1", "BP_ISSUE_DT1", "CO_ISSUE_DT1",
    "NO_ENTITLEMENTS", "NO_BUILDING_PERMITS", "NO_OTHER_FORMS_OF_READINESS", "APPROVE_SB35",
] + INCOME_COLS
D_KEEP = [
    "JURIS_NAME", "YEAR", "PROGRAM_NAME", "PROGRAM_OBJECTIVE", "ACCOMPLISHED_DT",
    "PROGRAM_STATUS", "QUANTIFIED_OUTCOMES_CATEGORY", "QUANTIFIED_OUTCOMES_COUNT",
]
KEYWORDS = ["adu", "accessory", "permit", "streamlin", "pre-approved", "objective design", "fee", "cup"]


def oc_names() -> list[str]:
    cities = json.loads((ROOT / "lanes/2-clear-it/data/oc-cities.json").read_text())["cities"]
    return [c["name"].upper() for c in cities] + ["ORANGE COUNTY"]


def fetch(resource_id: str, filters: dict, keep: list[str]) -> list[dict]:
    rows, offset, total = [], 0, None
    while total is None or offset < total:
        params = {
            "resource_id": resource_id,
            "filters": json.dumps(filters),
            "fields": ",".join(keep),
            "limit": PAGE,
            "offset": offset,
        }
        r = requests.get(API, params=params, timeout=120)
        r.raise_for_status()
        res = r.json()["result"]
        total = res["total"]
        rows.extend(res["records"])
        offset += PAGE
        print(f"  {resource_id[:8]}: {len(rows)}/{total}", file=sys.stderr)
        time.sleep(SLEEP_S)
    return rows


def write_csv(path: Path, rows: list[dict], cols: list[str]) -> None:
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def keyword_hits(rows: list[dict]) -> int:
    pat = re.compile(r"\b(" + "|".join(re.escape(k) for k in KEYWORDS) + ")", re.I)
    return sum(
        1 for r in rows
        if pat.search(f"{r.get('PROGRAM_NAME') or ''} {r.get('PROGRAM_OBJECTIVE') or ''}")
    )


def report(a2: list[dict], d: list[dict]) -> None:
    print("A2 rows by year:", dict(sorted(Counter(str(r["YEAR"]) for r in a2).items())), "total", len(a2))
    print("D rows by year:", dict(sorted(Counter(str(r["YEAR"]) for r in d).items())), "total", len(d))
    d25 = [r for r in d if str(r["YEAR"]) == "2025"]
    print(f"2025 Table D rows matching permit keywords: {keyword_hits(d25)} of {len(d25)}")


def main() -> None:
    DATA.mkdir(exist_ok=True)
    a2_path, d_path = DATA / "oc_apr_a2.csv", DATA / "oc_apr_tableD.csv"
    if a2_path.exists() and d_path.exists():
        print("CSVs already exist; skipping download.")
        with a2_path.open() as f:
            a2 = list(csv.DictReader(f))
        with d_path.open() as f:
            d = list(csv.DictReader(f))
        report(a2, d)
        return

    a2 = fetch(A2_ID, {"CNTY_NAME": "Orange"}, A2_KEEP)
    d = fetch(D_ID, {"JURIS_NAME": oc_names()}, D_KEEP)
    write_csv(a2_path, a2, A2_KEEP)
    write_csv(d_path, d, D_KEEP)

    pulled = datetime.now(timezone.utc).isoformat(timespec="seconds")
    sources = {
        "publisher": "California Department of Housing and Community Development (HCD), via data.ca.gov",
        "api": API,
        "pulled_at_utc": pulled,
        "tables": {
            "oc_apr_a2.csv": {
                "name": "APR Table A2 (housing development applications, entitlements, permits, completions)",
                "resource_id": A2_ID,
                "url": f"https://data.ca.gov/api/3/action/datastore_search?resource_id={A2_ID}",
                "filter": "CNTY_NAME = 'Orange'",
                "dropped_columns": "STREET_ADDRESS, STD_ADDRESS, PROJECT_NAME, NOTES, LATITUDE, LONGITUDE and others not needed",
                "rows": len(a2),
            },
            "oc_apr_tableD.csv": {
                "name": "APR Table D (housing element program implementation status)",
                "resource_id": D_ID,
                "url": f"https://data.ca.gov/api/3/action/datastore_search?resource_id={D_ID}",
                "filter": "JURIS_NAME in the 34 OC cities (lanes/2-clear-it/data/oc-cities.json) plus ORANGE COUNTY",
                "rows": len(d),
            },
        },
    }
    (DATA / "SOURCES.json").write_text(json.dumps(sources, indent=2) + "\n")
    report(a2, d)


if __name__ == "__main__":
    main()
