# Iteration log: Permit Clock build and improve rounds

### Round 1 · 11:38 · Build step 1: fetch OC APR Table A2 and Table D extracts
- Category: B
- Found: no `data/`, no `app.py`; build step 1 of `prompts/01-build.md` not started.
- Changed: added `scripts/fetch_apr.py` (CKAN datastore API, 5,000-row pages, 1 s sleep; A2 keeps only the needed columns, drops address/project name/notes/coordinates; APN kept for cross-year linking only, never for the UI). Ran it once: `data/oc_apr_a2.csv`, `data/oc_apr_tableD.csv`, `data/SOURCES.json`.
- Result: check.sh pass. A2 = 53,578 OC rows 2018-2025 (2018 7,416 · 2019 5,590 · 2020 5,213 · 2021 6,811 · 2022 6,773 · 2023 7,121 · 2024 7,456 · 2025 7,198), matches NOTES' ~54k. Table D = 8,623 rows 2018-2025, 1,822 for 2025 (matches ~1.8k); 362 of the 2025 rows match the permit keywords. Table D covers all 35 jurisdictions; A2 has 34: LAGUNA WOODS has no A2 rows in this resource (treat as "unknown", not zero).
- Next: build step 2 `analysis.py` (durations, cross-year linking counts, `summary`, `monte_carlo`) with pytest tests; then step 3 Tab A.
