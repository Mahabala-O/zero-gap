import pandas as pd
import analysis as an


def _df(rows):
    return pd.DataFrame(rows, columns=["JURIS_NAME", "YEAR", "APN", "JURS_TRACKING_ID", "UNIT_CAT",
                                       "ENT_APPROVE_DT1", "BP_ISSUE_DT1", "CO_ISSUE_DT1"])


def test_durations_negative_and_same_day():
    d = an.add_durations(_df([
        ["A", "2023", "1", "t1", "ADU", "2023-01-01", "2023-01-31", "2023-03-02"],
        ["A", "2023", "2", "t2", "ADU", "2023-02-01", "2023-02-01", None],
        ["A", "2023", "3", "t3", "ADU", "2023-03-01", "2023-02-01", None],
    ]))
    assert d["ent_to_permit_days"].tolist()[0] == 30
    assert d["ent_to_permit_same_day"].tolist() == [False, True, False]
    assert an.count_negatives(d) == {"ent_to_permit": 1, "permit_to_co": 0}
    assert d["ent_to_permit_days"].isna().tolist() == [False, False, True]
    assert d["permit_to_co_days"].tolist()[0] == 30


def test_summary_unknown_below_min_n_and_percentiles():
    rows = [["A", "2023", str(i), f"t{i}", "ADU", "2023-01-01", f"2023-01-{1 + i % 28:02d}", None]
            for i in range(40)]
    d = an.add_durations(_df(rows))
    s = an.summary(d, "a", "ADU", "ent_to_permit")
    assert s["n"] == 40 and s["coverage_pct"] == 100.0
    assert isinstance(s["P50"], float) and s["P25"] <= s["P50"] <= s["P75"] <= s["P80"]
    small = an.summary(d, "A", "ADU", "ent_to_permit", min_n=50)
    assert small["P50"] == "unknown" and small["n"] == 40
    assert isinstance(s["same_day_pct"], float) and small["same_day_pct"] == "unknown"
    none = an.summary(d, "B", "ADU", "ent_to_permit")
    assert none["n"] == 0 and none["coverage_pct"] == "unknown" and none["P80"] == "unknown"


def test_link_counts():
    d = _df([["A", "2022", "1", "t1", "ADU", None, None, None],
             ["A", "2023", "1", "t9", "ADU", None, None, None],
             ["A", "2023", "2", "t1", "ADU", None, None, None],
             ["B", "2023", "3", "", "ADU", None, None, None]])
    assert an.link_counts(d) == {"tracking_id": 1, "apn": 1}


def _mc_df(rows):
    return an.add_durations(_df(rows))


def test_monte_carlo_paired_dates_costs_and_shares():
    # 40 records, each 30 days ent->permit and 60 days permit->CO: every draw is identical.
    rows = [["A", "2023", str(i), f"t{i}", "ADU", "2023-01-01", "2023-01-31", "2023-04-01"]
            for i in range(40)]
    r = an.monte_carlo(_mc_df(rows), "A", "ADU", "2026-01-01", 1000.0, draws=500)
    assert r["method"] == "paired" and r["n_paired"] == 40
    assert r["permit_date"]["P50"] == pd.Timestamp("2026-01-31")
    assert r["co_date"]["P80"] == pd.Timestamp("2026-04-01")
    assert abs(r["cost"]["P50"] - 90 / an.DAYS_PER_MONTH * 1000) < 1e-6
    assert r["contingency"] == 0.0
    assert r["spread_share"] == {"ent_to_permit": 0.0, "permit_to_co": 0.0}


def test_monte_carlo_independent_fallback_and_spread():
    # Stage 1 varies (0-39 days), stage 2 fixed; no record has both stages.
    rows = [["A", "2023", str(i), f"t{i}", "ADU", "2023-01-01",
             str(pd.Timestamp("2023-01-01") + pd.Timedelta(days=i))[:10], None] for i in range(40)]
    rows += [["A", "2023", f"x{i}", f"x{i}", "ADU", None, "2023-01-01", "2023-03-02"]
             for i in range(40)]
    r = an.monte_carlo(_mc_df(rows), "A", "ADU", "2026-01-01", 1000.0)
    assert r["n_paired"] == 0 and r["method"].startswith("independent (ASSUMPTION")
    assert r["spread_share"]["ent_to_permit"] == 1.0
    assert r["contingency"] > 0
    assert r["co_date"]["P80"] >= r["co_date"]["P50"]


def test_monte_carlo_unknown_when_stage_missing_or_no_data():
    rows = [["A", "2023", str(i), f"t{i}", "ADU", "2023-01-01", "2023-01-31", None]
            for i in range(40)]
    r = an.monte_carlo(_mc_df(rows), "A", "ADU", "2020-01-01", 1000.0)
    assert r["permit_date"]["P50"] == pd.Timestamp("2020-01-31")  # start in the past is fine
    assert r["co_date"]["P50"] == "unknown" and r["contingency"] == "unknown"
    empty = an.monte_carlo(_mc_df(rows), "NOWHERE", "ADU", "2026-01-01", 1000.0)
    assert empty["permit_date"]["P80"] == "unknown" and empty["cost"]["P50"] == "unknown"


def test_peer_medians_and_best_quartile_excludes_same_day():
    rows = []
    for c, gap in (("A", 0), ("B", 10), ("C", 20), ("D", 30), ("E", 40), ("F", 5)):
        n = 30 if c != "F" else 10  # F below MIN_N -> left out
        rows += [[c, "2023", f"{c}{i}", f"{c}{i}", "ADU", "2023-01-01",
                  (pd.Timestamp("2023-01-01") + pd.Timedelta(days=gap)).strftime("%Y-%m-%d"),
                  None] for i in range(n)]
    d = an.add_durations(_df(rows))
    p = an.peer_medians(d, "ADU", "ent_to_permit")
    assert sorted(p["JURIS_NAME"]) == ["A", "B", "C", "D", "E"]
    assert p.set_index("JURIS_NAME").loc["A", "same_day"]
    # same-day A excluded -> 25th pct of [10, 20, 30, 40] days = 17.5 days
    assert abs(an.best_quartile(p) - 17.5 / an.DAYS_PER_MONTH) < 1e-9
    assert an.best_quartile(p[p["JURIS_NAME"].isin(["A", "B", "C"])]) == an.UNKNOWN


def test_overdue_and_peers_completed():
    prog = pd.DataFrame({
        "JURIS_NAME": ["X", "X", "X", "Y", "Z", "Z"],
        "category": ["fees", "fees", "fees", "fees", "fees", "other"],
        "status_bucket": ["ongoing", "completed", "delayed", "completed", "completed", "completed"],
        "target_date": ["2024-01-01", "2024-01-01", None, "2030-01-01", "2020-01-01", None],
    })
    o = an.add_overdue(prog, "2026-11-07")
    assert o["overdue"].tolist() == ["yes", "no", an.UNKNOWN, "no", "no", "no"]
    assert an.peers_completed(prog, "x", "fees") == ["Y", "Z"]


def test_program_labels_tell_same_named_rows_apart():
    prog = pd.DataFrame({
        "JURIS_NAME": ["A", "A", "A", "B"],
        "PROGRAM_NAME": ["ADU  Program\n\na. Promote", "ADU  Program\n\na. Promote", "Fees", "Fees"],
        "PROGRAM_OBJECTIVE": ["Update ordinance", "Update website", "Cut fees", None],
    })
    lab = an.program_labels(prog).tolist()
    assert lab[0] == "ADU Program a. Promote — Update ordinance"
    assert lab[1] == "ADU Program a. Promote — Update website"
    assert lab[2] == "Fees" and lab[3] == "Fees"   # unique within each city: name only
    long = an.program_labels(pd.DataFrame({"JURIS_NAME": ["A"], "PROGRAM_NAME": ["x" * 200],
                                           "PROGRAM_OBJECTIVE": ["y"]})).iloc[0]
    assert len(long) == 60 and long.endswith("…")


def test_program_labels_names_differing_only_at_the_end():
    head = "Analyze the potential of an overlay to permit homes in the "
    prog = pd.DataFrame({"JURIS_NAME": ["A", "A"],
                         "PROGRAM_NAME": [head + "Airport Area", head + "17th Street Area"],
                         "PROGRAM_OBJECTIVE": ["Evaluate the overlay"] * 2})
    lab = an.program_labels(prog)
    assert lab.nunique() == 2
    assert "Airport Area" in lab.iloc[0] and "17th Street Area" in lab.iloc[1]


def test_program_labels_drop_words_every_name_in_a_city_shares():
    prog = pd.DataFrame({
        "JURIS_NAME": ["A", "A", "A", "B", "B"],
        "PROGRAM_NAME": ["6th HE Cycle  Goal 1: Supply", "6th HE Cycle 1.5 Zoning",
                         "6th HE Cycle 1.7 ADU", "PP-B.5: Staff", "PP-G.2: Ordinances"],
        "PROGRAM_OBJECTIVE": ["a", "b", "c", "d", "e"],
    })
    lab = an.program_labels(prog).tolist()
    assert lab[:3] == ["Goal 1: Supply", "1.5 Zoning", "1.7 ADU"]
    assert lab[3:] == ["PP-B.5: Staff", "PP-G.2: Ordinances"]   # 2 rows, no whole shared word
    # A name made only of the shared words is never emptied.
    same = an.program_labels(pd.DataFrame({"JURIS_NAME": ["A"] * 3,
                                           "PROGRAM_NAME": ["Fees", "Fees x", "Fees y"],
                                           "PROGRAM_OBJECTIVE": ["a", "b", "c"]}))
    assert same.tolist()[0].startswith("Fees")
