# Permit Clock iteration log

### Round 1 · 11:37 · Step 1: fetch_apr.py and cached CSVs
- Category: B
- Found: build not started. Result: data/oc_apr_a2.csv (53,578 rows) and data/oc_apr_tableD.csv (8,623 rows, all years) cached with SOURCES.json.
- Changed: scripts/fetch_apr.py (committed in round 1; CSVs were left untracked).
- Result: see round 2 for commit of the CSVs.
- Next: step 2 analysis.py.

### Round 2 · 11:50 · Step 2 (part 1): analysis.py durations, summary, link counts + tests
- Category: B
- Found: no analysis.py. CSVs untracked; committed now (address, project name, notes, lat/long columns already dropped; APN kept for linking, never shown in UI).
- Changed: analysis.py (add_durations, count_negatives, summary with MIN_N=30 ASSUMPTION -> "unknown", link_counts); tests/test_analysis.py (3 tests); data/*.
- Result: check.sh pass; 3 tests. Negatives dropped: 96 ent->permit, 73 permit->CO. Cross-year links: 11,461 by tracking ID vs 6,670 by APN (identifier matches only, not used yet). Tustin ent->permit n=573, median 20.2 months (= ~616 days, matches NOTES.md).
- Next: monte_carlo() in analysis.py (paired draws, independent fallback labelled ASSUMPTION) with tests; then app.py Tab A.

### Round 3 · 11:55 · Step 2 (part 2): monte_carlo() with paired/independent draws + tests
- Category: B
- Found: analysis.py had no monte_carlo(). Stale .claude/last_failure.txt (pytest missing under system Python) deleted; check.sh now passes with .venv Python.
- Changed: analysis.py: monte_carlo(df, city, unit_cat, start_date, monthly_cost, draws=5000, seed=42). Uses paired whole-record draws when n_paired >= MIN_N, else independent per-stage draws labelled "ASSUMPTION". A stage with n < MIN_N gives "unknown" CO date, cost and contingency. spread_share = each stage's (P80-P50) / sum. tests/test_analysis.py: 3 new tests (paired exact dates/costs, independent fallback + spread, unknown stage / no-data city / past start date).
- Result: check.sh pass; tests 3 -> 6. Tustin (all types) paired n=346: contingency ~$16.1k at $1,771/mo (ASSUMPTION cost), ent->permit adds 77% of spread. Santa Ana only 6 paired -> independent fallback, contingency ~$16.8k.
- Next: step 3 app.py Tab A (inputs, headline sentence, P50/P80 table with n, one chart, sources expander, footer).
