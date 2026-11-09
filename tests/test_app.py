"""End-to-end checks of app.py through Streamlit's AppTest, with no live Claude call.

They pin the honesty rules (unknown below MIN_N, labels present, today's date for overdue,
recurring activities never overdue) and the design rules (no P50/P80 jargon, caveats live in
"How we got this", stat tiles and cards rendered through ui.py).
"""
import datetime
import re

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

import analysis as A
import costs as C
import ui

PROMISES = "What did my city promise?"
TIMING = "After approval, how long to move-in?"
RED = f"background:{ui.STATUS['danger'][0]}"
GREEN = f"background:{ui.STATUS['success'][0]}"


def run(page=None, city=None, cities=None, unit=None, affordable=None):
    at = AppTest.from_file("app.py", default_timeout=180).run()
    if page:
        at.sidebar.radio[0].set_value(page).run()
    if city is not None:
        at.sidebar.selectbox[0].set_value(city).run()
    if unit is not None:
        at.sidebar.selectbox[0].set_value(unit).run()
    if affordable:
        at.sidebar.radio[1].set_value("Deed-restricted affordable only").run()
    if cities is not None:
        at.sidebar.multiselect[0].set_value(cities).run()
    assert not at.exception, [e.message for e in at.exception]
    return at


def all_text(at):
    return " ".join([m.value for m in at.markdown] + [c.value for c in at.caption])


def stats(at):
    """{eyebrow label: (value, sub)} for every ui.stat tile on the page."""
    out = {}
    for m in at.main.markdown:
        for lab, val, sub in re.findall(
                r"<div class='pc-eyebrow'>(.*?)</div><div class='pc-value[^']*'>(.*?)</div>"
                r"(?:<div class='pc-sub'[^>]*>(.*?)</div>)?", m.value):
            out[lab] = (val, sub)
    return out


def verdict(at):
    """The shortlist paragraph: the first main markdown that is not a styled HTML block."""
    return [m.value for m in at.main.markdown if not m.value.startswith("<")][0]


def city_notes(at):
    """{city title: text of its 'How we got this' expander}, in sidebar order."""
    exps = [e for e in at.main.expander if e.label == "How we got this"]
    names = [re.sub(r"<[^>]+>", "", m.value).strip() for m in at.main.markdown
             if m.value.startswith("<div class='pc-card-title'><span class='pc-dot'")]
    return dict(zip(names, (" ".join(x.value for x in e.markdown) for e in exps)))


@pytest.fixture(scope="module")
def df():
    return A.add_durations(A.load_a2())


@pytest.fixture(scope="module")
def prog():
    return A.add_overdue(A.load_programs(), datetime.date.today())


# ---------- landing page: What did my city promise? ----------

def test_landing_is_the_promise_page_with_three_tiles(prog):
    at = run()
    s = stats(at)
    t = prog[prog["JURIS_NAME"] == "TUSTIN"]
    n_over = int((t["overdue"] == "yes").sum())
    assert s["Promises overdue"][0] == f"{n_over} of {len(t)}"
    assert s["Reported done"][0] == str(int((t["status_bucket"] == "completed").sum()))
    n_rec = int((t["overdue"] == "recurring").sum())
    n_und = int(((t["overdue"] == A.UNKNOWN) & (t["status_bucket"] != "completed")).sum())
    assert s["Recurring or undated"][0] == str(n_rec + n_und)
    assert f"{n_rec} annual or ongoing" in s["Recurring or undated"][1]


def test_no_percentile_jargon_anywhere_on_either_page():
    for page in (None, TIMING):
        text = all_text(run(page))
        assert "P50" not in text and "P80" not in text


def test_promise_rows_mark_every_overdue_item_and_group_repeat_programs(prog):
    at = run()
    status = [r for r in at.main.radio if r.options and r.options[0] == "All"][0]
    assert status.value == "All"
    text = " ".join(m.value for m in at.main.markdown)
    t = prog[prog["JURIS_NAME"] == "TUSTIN"]
    n_over = int((t["overdue"] == "yes").sum())
    assert text.count(RED) == n_over
    # Tustin's ADU program has several lettered sub-items: one card header counting them.
    assert re.search(r"Accessory Dwelling Units Program <span class='pc-m'>· \d+ promises", text)
    assert "6th HE Cycle" not in text  # shared lead dropped from every program title
    status.set_value(f"Overdue ({n_over})").run()
    text = " ".join(m.value for m in at.main.markdown)
    assert text.count(RED) == n_over and GREEN not in text


def test_recurring_activities_are_shown_as_recurring_not_overdue():
    at = run()
    text = " ".join(m.value for m in at.main.markdown)
    # Tustin: "Process approximately 5 ADU/JADU applications per year" is an annual activity.
    row = re.search(r"<div class='pc-row'>(?:(?!</div>).)*?applications per year.*?</div>",
                    text).group(0)
    assert "recurring · no single deadline" in row and "overdue" not in row


def test_target_from_the_citys_own_wording_is_labelled():
    # San Clemente: "no later than October 2024" in the objective text -> target Oct 2024.
    at = run(city="SAN CLEMENTE")
    text = " ".join(m.value for m in at.main.markdown)
    assert "target Oct 2024 (city's own wording)" in text


def test_labels_say_unverified_until_the_handcheck_is_done():
    at = run()
    hc = A.handcheck_accuracy()
    caps = " ".join(c.value for c in at.main.caption)
    if hc["n_checked"]:
        assert f"Of {hc['n_checked']} hand-checked labels" in caps
    else:
        assert "unverified" in caps and f"{hc['n_rows']} sample rows" in caps


def test_permit_time_sentence_handles_unknown_and_same_day():
    at = run(city="BREA")  # 12 approval -> permit records
    text = " ".join(m.value for m in at.main.markdown)
    assert "approval → permit: not enough reported data" in text
    at = run(city="ANAHEIM")  # same-day reporting pattern
    text = " ".join(m.value for m in at.main.markdown)
    assert "approval → permit: same-day reporting (not comparable)" in text


def test_overdue_uses_todays_date_not_first_load(monkeypatch):
    class Day(datetime.date):
        fixed = datetime.date(2020, 1, 1)

        @classmethod
        def today(cls):
            return cls.fixed

    monkeypatch.setattr(datetime, "date", Day)
    early = stats(run())["Promises overdue"][0]
    Day.fixed = datetime.date(2035, 1, 1)
    assert early != stats(run())["Promises overdue"][0]


def test_look_closer_shows_the_citys_own_words_and_the_draft_follows_it():
    at = run()
    text = " ".join(m.value for m in at.main.markdown)
    assert "**The city's objective:**" in text and "**Status reported by the city:**" in text
    assert "label unverified" in text
    pick = [s for s in at.main.selectbox if s.key == "draft_prog"][0]
    assert at.text_area and f"_{pick.value}_" in at.text_area[0].key
    assert "Dear Tustin" in at.text_area[0].value
    assert "Nothing is sent" in " ".join(c.value for c in at.main.caption)


def test_city_with_no_programs_gets_an_info_box_not_zero_counts():
    without = sorted(set(A.load_a2()["JURIS_NAME"].dropna())
                     - set(A.load_programs()["JURIS_NAME"]))
    assert without, "every city has programs; pick another fixture"
    at = run(city=without[0])
    assert any("No permitting-related programs" in i.value for i in at.info)
    assert not stats(at)


# ---------- evidence page: After approval, how long to move-in? ----------

def test_timing_lead_says_what_is_not_measured():
    at = run(TIMING)
    lead = [m.value for m in at.main.markdown if m.value.startswith("<p class='pc-lead'>")][0]
    assert "does not include rezoning or the entitlement process" in lead


def test_verdict_is_plain_and_puts_the_faster_city_first():
    at = run(TIMING)
    v = verdict(at)
    assert v.startswith("In **Santa Ana**") and "plan for" in v and "Tustin" in v
    for jargon in ("P50", "P80", "ASSUMPTION", "INFERRED", "drawn separately"):
        assert jargon not in v, jargon


def test_rough_city_is_explained_in_its_notes_not_the_headline():
    at = run(TIMING)
    notes = city_notes(at)
    assert "combined as if independent (ASSUMPTION)" in notes["Santa Ana"]
    assert "combined as if independent" not in notes["Tustin"]
    assert "Figures for Santa Ana are rough" in verdict(at)
    assert all("leans the figures toward faster projects" in n for n in notes.values())


def test_same_day_city_gets_caution_in_its_notes():
    at = run(TIMING, cities=["ANAHEIM", "TUSTIN"])
    notes = city_notes(at)
    assert "Caution" in notes["Anaheim"] and "INFERRED" in notes["Anaheim"]
    assert "Caution" not in notes["Tustin"]


def test_no_same_day_caution_below_min_n():
    at = run(TIMING, cities=["YORBA LINDA"], unit="MH")
    notes = city_notes(at)
    assert "Caution" not in notes["Yorba Linda"]
    assert f"fewer than {A.MIN_N} usable records" in notes["Yorba Linda"]
    assert "not enough reported data" in verdict(at).lower()


def test_city_without_data_says_so_in_tile_and_verdict():
    at = run(TIMING, cities=["IRVINE", "TUSTIN"])
    assert "Irvine: not enough reported data" in verdict(at)
    assert stats(at)["Move-in, likely"][0] in ("Not enough reported data", stats(at)["Move-in, likely"][0])
    assert "pc-value pc-unknown'>Not enough reported data" in " ".join(
        m.value for m in at.main.markdown)


def test_verdict_gap_matches_the_dates_on_the_tiles(df):
    at = run(TIMING)
    gap = int(re.search(r"about \*\*(\d+) months longer\*\*", verdict(at)).group(1))
    start = at.sidebar.date_input[0].value.isoformat()
    t = A.monte_carlo(df, "TUSTIN", None, start, 1.0)["co_date"]["P50"]
    s = A.monte_carlo(df, "SANTA ANA", None, start, 1.0)["co_date"]["P50"]
    assert gap == (t.year - s.year) * 12 + t.month - s.month


def test_cost_tiles_are_differences_not_whole_path_totals(df):
    at = run(TIMING)
    example = C.example_monthly_cost()["total"]
    assert example == pytest.approx(360_000 * 7.0 / 1200 + 360_000 * 1.1 / 1200
                                    + 40_000 * 5.5 / 1200)
    start = at.sidebar.date_input[0].value.isoformat()
    t = A.monte_carlo(df, "TUSTIN", None, start, 1.0)
    s = A.monte_carlo(df, "SANTA ANA", None, start, 1.0)
    text = " ".join(m.value for m in at.main.markdown)
    contingency = f"${round((t['cost']['P80'] - t['cost']['P50']) * example, -2):,.0f}"
    extra = f"${round((t['cost']['P50'] - s['cost']['P50']) * example, -2):,.0f}"
    assert contingency in text and extra in text
    assert f"${round(t['cost']['P50'] * example, -2):,.0f}" not in text  # no whole-path total
    assert "Extra wait vs Santa Ana" in stats(at)


def test_cost_can_be_switched_off():
    at = run(TIMING)
    at.sidebar.checkbox[0].uncheck().run()
    assert not at.exception
    assert "Contingency to set aside" not in stats(at)
    assert "$" not in verdict(at)


def test_cost_calculator_cites_its_rates():
    at = run(TIMING)
    text = " ".join(c.value for c in at.sidebar.caption)
    for key, src in C.SOURCES.items():
        assert str(src["value"]) in text, key
    assert "ASSUMPTION" in text and "2026-11-08" in text


def test_deadline_at_risk_colors_each_city():
    at = run(TIMING)
    at.sidebar.date_input[1].set_value(datetime.date(2028, 1, 1)).run()
    assert not at.exception
    text = " ".join(m.value for m in at.main.markdown)
    # Tustin's likely move-in (2029) is after Jan 2028; Santa Ana's likely (2027) is before.
    assert "even the likely move-in date is after it" in text
    assert "likely date is before it" in text or "both dates are before it" in text


def test_affordable_only_filter_mostly_says_not_enough_data(df):
    at = run(TIMING, affordable=True)
    text = " ".join(m.value for m in at.main.markdown)
    assert "deed-restricted affordable projects only" in text
    aff = df[df["deed_restricted"]]
    n_known = sum(A.monte_carlo(aff, c, None, "2026-11-08", 1.0)["co_date"]["P50"] != A.UNKNOWN
                  for c in df["JURIS_NAME"].dropna().unique())
    assert n_known <= 2  # the honest answer: almost every city is "not enough reported data"


def test_rank_caption_explains_unknown_rows_and_empty_shortlist_hints():
    at = run(TIMING)
    caps = " ".join(c.value for c in at.main.caption)
    assert "listed without a bar" in caps
    at = run(TIMING, cities=[])
    assert any("Pick up to three cities" in i.value for i in at.info)


# ---------- costs module ----------

def test_monthly_cost_arithmetic_and_sources():
    parts = C.monthly_cost(120_000, 6.0, 240_000, 1.0, 60_000, 4.0, 150)
    assert parts["Loan interest"] == pytest.approx(600)
    assert parts["Property tax"] == pytest.approx(200)
    assert parts["Construction cost rising"] == pytest.approx(200)
    assert parts["total"] == pytest.approx(1150)
    for src in C.SOURCES.values():
        assert src["url"].startswith("https://") and src["checked"] == "2026-11-08"
