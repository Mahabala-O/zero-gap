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
