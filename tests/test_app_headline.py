from streamlit.testing.v1 import AppTest


def test_headline_flags_separate_draws():
    # Default view is Tustin (paired) vs Santa Ana (separate draws, n_paired=6).
    at = AppTest.from_file("app.py", default_timeout=120).run()
    assert not at.exception
    text = " ".join(m.value for m in at.markdown)
    assert "drawn separately" in text and "Santa Ana" in text.split("ASSUMPTION: too few")[1]
    assert "Tustin" not in text.split("ASSUMPTION: too few")[1]


def test_headline_flags_same_day_city():
    # Anaheim reports ~72% same-day entitlement -> permit rows; Tustin ~2%.
    at = AppTest.from_file("app.py", default_timeout=120).run()
    at.selectbox[1].select_index(at.selectbox[1].options.index("Anaheim")).run()
    assert not at.exception
    text = " ".join(m.value for m in at.markdown)
    assert "Caution: most of Anaheim's" in text
    assert "Tustin's" not in text
    at.selectbox[1].select_index(at.selectbox[1].options.index("Santa Ana")).run()
    assert "Caution: most of" not in " ".join(m.value for m in at.markdown)


def test_headline_no_same_day_caution_below_min_n():
    # Yorba Linda, mobile homes: 5 entitlement -> permit records, all same-day. n < MIN_N, so
    # the share is "unknown" and the headline must not claim "most of" its records.
    at = AppTest.from_file("app.py", default_timeout=120).run()
    at.selectbox[0].select_index(at.selectbox[0].options.index("Yorba Linda")).run()
    at.selectbox[2].set_value("MH").run()
    assert not at.exception
    text = " ".join(m.value for m in at.markdown)
    assert "Contingency for Yorba Linda is **unknown**" in text
    assert "Caution: most of" not in text


def test_headline_same_day_two_cities_plural():
    # Anaheim (~72%) and Fullerton (~85%) are both above the same-day threshold.
    at = AppTest.from_file("app.py", default_timeout=120).run()
    at.selectbox[0].select_index(at.selectbox[0].options.index("Anaheim")).run()
    at.selectbox[1].select_index(at.selectbox[1].options.index("Fullerton")).run()
    assert not at.exception
    text = " ".join(m.value for m in at.markdown)
    caution = text.split("Caution: most of")[1]
    assert "Anaheim and Fullerton's each" in caution
    assert "their speed there" in caution and "its speed" not in caution


def test_tab_b_best_quartile_shows_n():
    # UX rubric #4: every benchmark shows its n. The OC best quartile cell names its city count,
    # and that count matches peer_medians (n >= MIN_N, same-day cities left out).
    at = AppTest.from_file("app.py", default_timeout=120).run()
    assert not at.exception
    tables = [d.value for d in at.table if "OC best quartile (n)" in d.value.columns]
    assert len(tables) == 1
    cells = list(tables[0]["OC best quartile (n)"])
    assert all(c == "unknown" or c.endswith(" cities)") for c in cells)
    import analysis as A
    df = A.add_durations(A.load_a2())
    for cell, stage in zip(cells, ["ent_to_permit", "permit_to_co"]):
        peers = A.peer_medians(df, None, stage)
        assert f"({int((~peers['same_day']).sum())} cities)" in cell


def test_tab_b_explains_co():
    # UX rubric #5: Tab B's stage table says "Permit → CO"; CO is spelled out next to it.
    at = AppTest.from_file("app.py", default_timeout=120).run()
    assert not at.exception
    caps = [c.value for c in at.caption if "Best quartile" in c.value]
    assert len(caps) == 1 and "CO = certificate of occupancy" in caps[0]


def test_tab_b_target_date_beside_overdue():
    # The target date explains each "overdue" flag, so it sits right after it and stays on
    # screen at 1280 px (round 17: it was the 5th column, scrolled off to the right).
    # Status follows Program so "delayed"/"ongoing" stays on screen too (round 20).
    at = AppTest.from_file("app.py", default_timeout=120).run()
    assert not at.exception
    tables = [d.value for d in at.dataframe if "Overdue" in d.value.columns]
    assert len(tables) == 1
    assert list(tables[0].columns[:4]) == ["Overdue", "Target date", "Program", "Status"]


def test_tab_b_program_column_is_wide():
    # Round 19: the Program label (with its objective snippet) was cut off at 1280 px.
    import json
    at = AppTest.from_file("app.py", default_timeout=120).run()
    assert not at.exception
    d = [d for d in at.dataframe if "Overdue" in d.value.columns][0]
    assert json.loads(d.proto.columns)["Program"]["width"] == "large"


def test_tab_b_gap_matches_shown_values():
    # Round 26: Tustin Permit -> CO showed "9 months" vs "6 months" with a gap of "2.5 months"
    # (gap taken from unrounded medians). The gap must equal the two shown numbers' difference.
    import re
    at = AppTest.from_file("app.py", default_timeout=120).run()
    assert not at.exception
    t = [d.value for d in at.table if "OC best quartile (n)" in d.value.columns][0]
    num = lambda c: float(re.match(r"([\d.]+) month", c).group(1))
    checked = 0
    for _, row in t.iterrows():
        gap = row["Gap"]
        if gap.endswith("behind"):
            assert num(gap) == num(row[[c for c in t.columns if "median" in c][0]]) - num(row["OC best quartile (n)"])
            checked += 1
    assert checked >= 1


def tab_a_table(at):
    return [t.value for t in at.table if "Method" in t.value.index][0]


def test_tab_a_table_wraps_at_phone_width():
    # At 390 px st.dataframe scrolled City B's column off the right edge; st.table wraps.
    at = AppTest.from_file("app.py", default_timeout=120).run()
    assert not at.exception
    assert not [d for d in at.dataframe if "Method" in d.value.index]
    assert len(tab_a_table(at).columns) == 2


def test_tab_a_contingency_matches_shown_costs():
    # Default view: Santa Ana's unrounded contingency rounds to $16,800, but the shown costs are
    # $16,300 / $33,000. The contingency shown must be the difference of the shown costs.
    at = AppTest.from_file("app.py", default_timeout=120).run()
    assert not at.exception
    table = tab_a_table(at)
    money = lambda s: int(s.replace("$", "").replace(",", ""))
    for col in table.columns:
        cost = table.loc["Carrying cost, P50 / P80", col]
        cont = table.loc["Contingency (P80 − P50)", col]
        if "unknown" in cost or cont == "unknown":
            continue
        p50, p80 = (money(x) for x in cost.split(" / "))
        assert money(cont) == p80 - p50, (col, cost, cont)


def test_tab_a_chart_buffer_matches_shown_months():
    # Default view: Santa Ana entitlement -> permit shows 1.5 / 12 months, so its bar must be
    # 10.5 (the unrounded difference was 10.41).
    import json
    at = AppTest.from_file("app.py", default_timeout=120).run()
    assert not at.exception
    table = tab_a_table(at)
    spec = json.loads(at.get("plotly_chart")[0].proto.spec)
    num = lambda s: float(s.split(" month")[0])
    for trace in spec["data"]:
        col = trace["name"]
        for row, y in zip([r for r in table.index if r.endswith("P50 / P80 (n)")], trace["y"]):
            cell = table.loc[row, col]
            if "unknown" in cell:
                assert y is None, (col, row, y)
                continue
            p50, p80 = (num(x) for x in cell.split(" (n=")[0].split(" / "))
            assert y == p80 - p50, (col, row, cell, y)


def test_tab_a_move_in_p80_not_sum_of_stage_p80s_and_says_so():
    # Tustin (default City A): stage P80s add to about 42 months, the simulated move-in P80 is
    # earlier. The table must explain why so a reader adding the column is not misled.
    import datetime as dt
    import pandas as pd
    import analysis as A
    df = A.add_durations(A.load_a2())
    start = dt.date.today().isoformat()
    r = A.monte_carlo(df, "TUSTIN", None, start, 1771.0)
    p80_sum = sum(A.summary(df, "TUSTIN", None, s)["P80"] for s in ["ent_to_permit", "permit_to_co"])
    sim = (r["co_date"]["P80"] - pd.Timestamp(start)).days / A.DAYS_PER_MONTH
    assert sim < p80_sum
    at = AppTest.from_file("app.py", default_timeout=120).run()
    assert not at.exception
    assert any("earlier than adding the two stage P80s" in c.value for c in at.caption)


def test_tab_a_chart_title_wraps_at_phone_width():
    # A Plotly title is clipped at 390 px; the chart title must be Streamlit text that wraps.
    import json
    at = AppTest.from_file("app.py", default_timeout=120).run()
    assert not at.exception
    spec = json.loads(at.get("plotly_chart")[0].proto.spec)
    assert not spec["layout"].get("title", {}).get("text")
    assert any("Which stage adds the most buffer" in m.value for m in at.markdown)


def test_tab_a_headline_gap_matches_shown_move_in_dates():
    # Round 33: default view showed P80 move-in "Mar 2030" (Tustin) vs "May 2028" (Santa Ana),
    # 22 months apart, but the headline said "about 21 months faster" (gap taken from exact
    # days). The headline gap must equal the difference of the two shown months.
    import re
    import pandas as pd
    at = AppTest.from_file("app.py", default_timeout=120).run()
    assert not at.exception
    t = tab_a_table(at)
    row = [i for i in t.index if i.startswith("Move-in")][0]
    p80 = [pd.Timestamp(t.loc[row, c].split(" / ")[1]) for c in t.columns]
    shown = abs((p80[0].year - p80[1].year) * 12 + p80[0].month - p80[1].month)
    head = [m.value for m in at.markdown if "faster than" in m.value][0]
    said = float(re.search(r"about \*\*([\d.]+) months?\*\* faster", head).group(1))
    assert said == shown


def test_tab_b_headline_counts_unknown_overdue():
    # Costa Mesa: every program's target is not a single date, so overdue is "unknown" for all.
    # The headline must not read as "0 overdue" without saying the rest are unknown.
    import datetime as dt
    import analysis as A
    p = A.add_overdue(A.load_programs(), dt.date.today())
    cm = p[p["JURIS_NAME"] == "COSTA MESA"]
    n_unk = int((cm["overdue"] == "unknown").sum())
    assert n_unk > 0
    at = AppTest.from_file("app.py", default_timeout=120).run()
    at.selectbox(key="city_b_tab").select("COSTA MESA").run()
    assert not at.exception
    text = " ".join(m.value for m in at.markdown)
    assert f"for **{n_unk}**, whether they are overdue is **unknown**" in text
    # Tustin has no unknown targets: no unknown clause there.
    at.selectbox(key="city_b_tab").select("TUSTIN").run()
    assert "whether they are overdue is" not in " ".join(m.value for m in at.markdown)


def test_tab_b_city_with_no_programs_has_no_zero_count_headline():
    # Laguna Niguel has no permitting-related 2025 programs: the info box says so, and the
    # headline must not also claim "0 ... are past their target date".
    import analysis as A
    p = A.load_programs()
    assert (p["JURIS_NAME"] == "LAGUNA NIGUEL").sum() == 0
    at = AppTest.from_file("app.py", default_timeout=120).run()
    at.selectbox(key="city_b_tab").select("LAGUNA NIGUEL").run()
    assert not at.exception
    text = " ".join(m.value for m in at.markdown)
    assert "past their target date" not in text
    assert any("No permitting-related programs found" in i.value for i in at.info)


def test_tab_a_same_city_twice_says_so():
    # Picking the same city in both boxes used to drop the comparison sentence silently.
    at = AppTest.from_file("app.py", default_timeout=120).run()
    at.selectbox[1].select_index(at.selectbox[1].options.index("Tustin")).run()
    assert not at.exception
    text = " ".join(m.value for m in at.markdown)
    assert "pick a different City B to compare" in text
    assert "faster than" not in text
    at.selectbox[1].select_index(at.selectbox[1].options.index("Santa Ana")).run()
    assert "pick a different City B" not in " ".join(m.value for m in at.markdown)
