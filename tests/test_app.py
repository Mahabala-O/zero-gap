"""End-to-end checks of app.py through Streamlit's AppTest, with no API key.

They pin the honesty rules (unknown below MIN_N, labels present, today's date for overdue) and
the plain-language rules (no P50/P80 jargon, caveats live in "How we got this", not headlines).
"""
import re

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

import analysis as A
import costs as C

PAGE_2 = "How is my city doing?"


def run(page=None, cities=None, unit=None):
    at = AppTest.from_file("app.py", default_timeout=180).run()
    if page:
        at.sidebar.radio[0].set_value(page).run()
    if unit is not None:
        at.sidebar.selectbox[0].set_value(unit).run()
    if cities is not None:
        at.sidebar.multiselect[0].set_value(cities).run()
    assert not at.exception, [e.message for e in at.exception]
    return at


def all_text(at):
    return " ".join([m.value for m in at.markdown] + [c.value for c in at.caption]
                    + [m.label for m in at.metric] + [m.value for m in at.metric])


def city_notes(at):
    """{city title: text of its 'How we got this' expander}, in sidebar order."""
    exps = [e for e in at.main.expander if e.label == "How we got this"]
    names = [re.sub(r"<[^>]+>|\*|●", "", m.value).strip() for m in at.main.markdown
             if m.value.startswith("<span")]
    return dict(zip(names, (" ".join(x.value for x in e.markdown) for e in exps)))


@pytest.fixture(scope="module")
def df():
    return A.add_durations(A.load_a2())


# ---------- page 1: Where should I build? ----------

def test_default_verdict_is_plain_and_puts_the_faster_city_first():
    at = run()
    verdict = at.main.markdown[0].value
    assert verdict.startswith("In **Santa Ana**")
    assert "plan for" in verdict and "Tustin" in verdict
    for jargon in ("P50", "P80", "ASSUMPTION", "INFERRED", "drawn separately"):
        assert jargon not in verdict, jargon


def test_no_percentile_jargon_anywhere_on_either_page():
    for page in (None, PAGE_2):
        text = all_text(run(page))
        assert "P50" not in text and "P80" not in text


def test_rough_city_is_explained_in_its_notes_not_the_headline():
    # Santa Ana has 6 records with both stages, so its stages are drawn separately.
    at = run()
    notes = city_notes(at)
    assert "combined as if independent (ASSUMPTION)" in notes["Santa Ana"]
    assert "combined as if independent" not in notes["Tustin"]
    assert "Figures for Santa Ana are rough" in at.main.markdown[0].value


def test_same_day_city_gets_caution_in_its_notes():
    # Anaheim reports ~72% same-day approval -> permit rows; Tustin ~2%.
    at = run(cities=["ANAHEIM", "TUSTIN"])
    notes = city_notes(at)
    assert "Caution" in notes["Anaheim"] and "INFERRED" in notes["Anaheim"]
    assert "Caution" not in notes["Tustin"]


def test_no_same_day_caution_below_min_n():
    # Yorba Linda mobile homes: 5 records, all same-day. A share of 5 is not a pattern.
    at = run(cities=["YORBA LINDA"], unit="MH")
    notes = city_notes(at)
    assert "Caution" not in notes["Yorba Linda"]
    assert f"fewer than {A.MIN_N} usable records" in notes["Yorba Linda"]
    assert "not enough reported data" in at.main.markdown[0].value.lower()


def test_city_without_data_says_so_in_metric_and_verdict():
    at = run(cities=["IRVINE", "TUSTIN"])
    assert "Irvine: not enough reported data" in at.main.markdown[0].value
    assert any(m.value == "Not enough reported data" for m in at.metric)


def test_verdict_gap_matches_the_dates_on_the_tiles():
    at = run()
    verdict = at.main.markdown[0].value
    gap = int(re.search(r"about \*\*(\d+) months longer\*\*", verdict).group(1))
    likely = {m.label: m.value for m in at.metric}
    assert likely["Move-in, likely"]  # label exists
    dates = [pd.Timestamp(m.value) for m in at.metric if m.label == "Move-in, likely"]
    tustin, santa_ana = dates  # sidebar order: Tustin, Santa Ana
    assert gap == (tustin.year - santa_ana.year) * 12 + tustin.month - santa_ana.month


def test_cost_tiles_use_the_sidebar_calculator(df):
    at = run()
    example = C.example_monthly_cost()["total"]
    assert example == pytest.approx(360_000 * 7.0 / 1200 + 360_000 * 1.1 / 1200
                                    + 40_000 * 5.5 / 1200)
    r = A.monte_carlo(df, "TUSTIN", None, at.sidebar.date_input[0].value.isoformat(), 1.0)
    shown = [m.value for m in at.metric if m.label == "Cost of waiting, likely"][0]
    assert shown == f"${round(r['cost']['P50'] * example, -2):,.0f}"
    contingency = [m.value for m in at.metric if m.label == "Contingency to set aside"][0]
    assert contingency == f"${round(r['cost']['P80'] * example - r['cost']['P50'] * example, -2):,.0f}"


def test_cost_can_be_switched_off():
    at = run()
    at.sidebar.checkbox[0].uncheck().run()
    assert not at.exception
    assert not [m for m in at.metric if m.label.startswith("Cost of waiting")]
    assert "$" not in at.main.markdown[0].value


def test_cost_calculator_cites_its_rates():
    at = run()
    text = " ".join(c.value for c in at.sidebar.caption)
    for key, src in C.SOURCES.items():
        assert str(src["value"]) in text, key
    assert "ASSUMPTION" in text and "2026-11-08" in text


def test_rank_chart_lists_every_city_below_min_n(df):
    at = run()
    start = at.sidebar.date_input[0].value.isoformat()
    missing = [c.title() for c in sorted(df["JURIS_NAME"].dropna().unique())
               if A.monte_carlo(df, c, None, start, 1.0)["co_date"]["P50"] == A.UNKNOWN]
    cap = [c.value for c in at.main.caption if c.value.startswith("Not enough reported data")]
    assert len(cap) == 1
    listed = [x.strip(" .") for x in cap[0].split(":", 1)[1].split(",")]
    assert listed == missing
    assert "Irvine" in listed and "Huntington Beach" in listed


def test_empty_shortlist_gives_a_hint_not_an_error():
    at = run(cities=[])
    assert any("Pick up to three cities" in i.value for i in at.info)


# ---------- page 2: How is my city doing? ----------

def test_tiles_match_analysis_for_tustin(df):
    at = run(PAGE_2)
    tiles = {m.label: m for m in at.metric}
    for stage, label in (("ent_to_permit", "Approval → permit"), ("permit_to_co", "Permit → move-in")):
        sm = A.summary(df, "TUSTIN", None, stage)
        bq = A.best_quartile(A.peer_medians(df, None, stage))
        gap = round(sm["P50"] * 2) / 2 - round(bq * 2) / 2
        assert tiles[label].value.startswith(f"{round(sm['P50'] * 2) / 2:g} month")
        assert tiles[label].delta == f"+{gap:g} months vs fastest quarter"
    prog = A.add_overdue(A.load_programs(), __import__("datetime").date.today())
    tustin = prog[prog["JURIS_NAME"] == "TUSTIN"]
    assert tiles["Permitting promises overdue"].value == \
        f"{int((tustin['overdue'] == 'yes').sum())} of {len(tustin)}"


def test_tile_shows_not_enough_data_below_min_n():
    # Brea: 12 approval -> permit records, 57 permit -> move-in.
    at = run(PAGE_2)
    at.sidebar.selectbox[0].set_value("BREA").run()
    tiles = {m.label: m for m in at.metric}
    assert tiles["Approval → permit"].value == "Not enough reported data"
    assert tiles["Permit → move-in"].delta.endswith("fastest quarter")


def test_same_day_city_tile_says_same_day_not_fast():
    at = run(PAGE_2)
    at.sidebar.selectbox[0].set_value("ANAHEIM").run()
    tiles = {m.label: m for m in at.metric}
    assert tiles["Approval → permit"].value == "Same day"


def test_overdue_uses_todays_date_not_first_load(monkeypatch):
    import datetime

    class Day(datetime.date):
        fixed = datetime.date(2020, 1, 1)

        @classmethod
        def today(cls):
            return cls.fixed

    def overdue_tile():
        at = run(PAGE_2)
        return [m.value for m in at.metric if m.label == "Permitting promises overdue"][0]

    monkeypatch.setattr(datetime, "date", Day)
    early = overdue_tile()
    Day.fixed = datetime.date(2035, 1, 1)
    assert early != overdue_tile()


def test_filter_defaults_to_overdue_and_cards_show_the_citys_words():
    at = run(PAGE_2)
    status = [r for r in at.main.radio if r.options and r.options[0] == "All"][0]
    assert status.value.startswith("Overdue (")
    n_over = int(re.search(r"\((\d+)\)", status.value).group(1))
    cards = [m for m in at.main.markdown if m.value.startswith("<span style='color:#d62728'>")]
    assert len(cards) == n_over
    words = [e for e in at.main.expander if e.label == "The city's own words"]
    assert len(words) == n_over
    first = " ".join(m.value for m in words[0].markdown)
    assert "**Status reported:**" in first and "**Objective:**" in first


def test_city_with_no_programs_gets_an_info_box_not_zero_counts():
    prog = A.load_programs()
    without = sorted(set(A.load_a2()["JURIS_NAME"].dropna()) - set(prog["JURIS_NAME"]))
    assert without, "every city has programs; pick another fixture"
    at = run(PAGE_2)
    at.sidebar.selectbox[0].set_value(without[0]).run()
    assert not at.exception
    assert any("No permitting-related programs" in i.value for i in at.info)
    assert [m.value for m in at.metric if m.label == "Permitting promises"] == ["None found"]


def test_draft_starts_as_a_template_and_is_never_sent():
    # Before any button click the draft is the static template, whether or not a key is set
    # (a local .env may hold one). Nothing in the app sends it anywhere.
    at = run(PAGE_2)
    assert at.text_area and "template" in at.text_area[0].label
    assert "Dear Tustin" in at.text_area[0].value
    assert "Nothing is sent" in " ".join(c.value for c in at.main.caption)


# ---------- costs module ----------

def test_monthly_cost_arithmetic_and_sources():
    parts = C.monthly_cost(120_000, 6.0, 240_000, 1.0, 60_000, 4.0, 150)
    assert parts["Loan interest"] == pytest.approx(600)
    assert parts["Property tax"] == pytest.approx(200)
    assert parts["Construction cost rising"] == pytest.approx(200)
    assert parts["total"] == pytest.approx(1150)
    for src in C.SOURCES.values():
        assert src["url"].startswith("https://") and src["checked"] == "2026-11-08"
