import math

import drafts as D

ROW = {"PROGRAM_NAME": "ADU guidance", "PROGRAM_OBJECTIVE": "Update website with ADU permit guidance",
       "ACCOMPLISHED_DT": "2022-06-01", "PROGRAM_STATUS": "Project is delayed."}


def test_template_quotes_row_and_sends_nothing():
    t = D.static_template("Tustin", ROW)
    for v in ROW.values():
        assert v in t
    assert "[Your name]" in t and "violat" not in t.lower()


def test_missing_fields_say_unknown():
    t = D.static_template("Tustin", {"PROGRAM_NAME": "X", "PROGRAM_OBJECTIVE": math.nan,
                                     "ACCOMPLISHED_DT": None, "PROGRAM_STATUS": "  "})
    assert t.count("unknown") == 3
    assert "unknown" in D.program_text("Tustin", {})


def test_quoted_text_is_one_line_with_same_words():
    name = "6th HE Cycle  1.7 (Modified) ADU Program\n\na.    Promote ADUs"
    t = D.static_template("Tustin", {**ROW, "PROGRAM_NAME": name})
    line = next(ln for ln in t.splitlines() if ln.startswith("- Program:"))
    assert line == '- Program: "6th HE Cycle 1.7 (Modified) ADU Program a. Promote ADUs"'
    assert "- Objective:" in t.splitlines()[t.splitlines().index(line) + 1]
