import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import classify_tableD as ct  # noqa: E402


def test_parse_target_date_only_exact_iso():
    assert ct.parse_target_date("2022-06-01") == "2022-06-01"
    assert ct.parse_target_date("Within 3 years.") is None
    assert ct.parse_target_date("2013-2021. Modify the Code in 2020") is None
    assert ct.parse_target_date(None) is None
    assert ct.parse_target_date("2022-13-01") is None


def test_keyword_rules():
    assert ct.keyword_category("ADU Program", "") == "ADU streamlining"
    assert ct.keyword_category("Pre-approved ADU plans", "") == "pre-approved plans"
    assert ct.keyword_category("Fee Assistance", "reduce fees") == "fees"
    assert ct.keyword_category("Remove CUP for multifamily", "") == "process/CUP removal"
    assert ct.keyword_status("Project is delayed.") == "delayed"
    assert ct.keyword_status("Ongoing.") == "ongoing"
    assert ct.keyword_status("Not started") == "not started"
    assert ct.keyword_status("") == "unclear"
    assert ct.keyword_status("The council met.") == "unclear"


def test_validate_labels_coerces_bad_values_and_drops_unknown_ids():
    items = [
        {"row_id": 1, "category": "fees", "status_bucket": "completed", "target_date": "2024-01-31"},
        {"row_id": 2, "category": "made up", "status_bucket": "done", "target_date": "soon"},
        {"row_id": 99, "category": "fees", "status_bucket": "completed", "target_date": None},
        "junk",
    ]
    got = ct.validate_labels(items, {1, 2})
    assert got[1] == {"category": "fees", "status_bucket": "completed", "target_date": "2024-01-31"}
    assert got[2] == {"category": "other", "status_bucket": "unclear", "target_date": None}
    assert 99 not in got
    assert ct.extract_json("no json here") == []
    assert ct.extract_json('x [{"row_id": 1}] y') == [{"row_id": 1}]


def test_load_rows_filters_latest_year_and_keywords(tmp_path):
    p = tmp_path / "d.csv"
    pd.DataFrame({
        "JURIS_NAME": ["A", "A", "B"], "YEAR": [2024, 2025, 2025],
        "PROGRAM_NAME": ["ADU", "ADU guidance", "Parks"],
        "PROGRAM_OBJECTIVE": ["", "", "plant trees"],
        "ACCOMPLISHED_DT": ["", "2022-06-01", ""], "PROGRAM_STATUS": ["", "delayed", ""],
    }).to_csv(p, index=False)
    rows = ct.load_rows(p)
    assert len(rows) == 1 and rows.loc[0, "PROGRAM_NAME"] == "ADU guidance"
    out = ct.keyword_classify(rows)
    assert out.loc[0, "method"] == ct.KEYWORD_METHOD
    assert out.loc[0, "target_date"] == "2022-06-01"
