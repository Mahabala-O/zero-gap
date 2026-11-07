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

### Round 4 · 11:52 · Step 3: app.py Tab A "Plan my project"
- Category: B
- Found: no app.py (build step 3 not started).
- Changed: app.py (new). Tab A: 4 visible inputs (City A, City B, unit type, entitlement approval date) plus carrying cost in an expander labelled ASSUMPTION (SYNTHETIC deal, $85k / 48 months). Headline sentence (contingency for City A + which city is faster at P80), P50/P80 table per city with n, move-in dates, carrying cost, contingency and method (paired vs separate draws = ASSUMPTION), "unknown" info boxes with what to try, one grouped bar chart (P80 − P50 months per stage, fixed city colors), Sources and caveats expander (A2 source from SOURCES.json; Anaheim/Fullerton same-day %, Huntington Beach permit→CO n, Orange ADU median vs BackyardADU 263 days, all computed live except the third-party figure). Tab B is a placeholder. Footer disclaimer. All data via st.cache_data, no network calls.
- Result: check.sh pass (6 tests, app ok). Default view: Tustin vs Santa Ana, all types: "Budget $16,100 contingency in Tustin. Santa Ana is about 21 months faster than Tustin at P80." First AppTest load 0.9 s, input change re-render 0.35 s.
- Next: step 4 scripts/classify_tableD.py (Haiku batch; only if data/tableD_classified.csv missing, needs API key — if no key, build keyword-rule fallback labelled "keyword match, not reviewed"); then step 5 Tab B. Note: Santa Ana all-types uses separate draws (n_paired=6), so its 21-month lead is an ASSUMPTION-heavy figure; consider flagging that in the headline.

### Round 5 · 11:58 · Step 4: classify_tableD.py, Haiku labels for 2025 OC Table D
- Category: B
- Found: no scripts/classify_tableD.py and no data/tableD_classified.csv (build step 4 not started). First run crashed: anthropic 0.39.0 + httpx 0.28.1 → `TypeError: unexpected keyword argument 'proxies'`.
- Changed: scripts/classify_tableD.py (new): keyword-filters 2025 OC Table D rows, counts tokens and prints an estimate before sending (refuses above $2), batches of 20 to claude-haiku-5-5 with a "use only the text given; unclear if the status does not say" prompt, validates every label (unknown category → other, unknown status → unclear, target_date only if the target text is one exact ISO date), keeps the source text. With no key it writes data/tableD_keyword.csv labelled "keyword match, not reviewed" instead. Writes data/tableD_handcheck.csv (20 random rows, blank "correct?" column). tests/test_classify.py (4 tests). requirements.txt: pinned httpx==0.27.2 (fixes the crash without a major SDK upgrade). data/tableD_classified.csv and data/tableD_handcheck.csv committed.
- Result: check.sh pass; tests 6 -> 10. 367 rows, 34 jurisdictions, 19 batches, 107,777 input tokens counted, estimated $0.022; 367/367 labelled. Categories: other 162, ADU streamlining 64, permit-time review 42, objective standards 31, process/CUP removal 29, fees 27, pre-approved plans 12. Status: ongoing 211, completed 97, unclear 26, delayed 25, not started 8. target_date parsed for 321/367. Keyword rules agree with Claude on only 47% of categories and 41% of statuses, so the keyword fallback is weak: say so wherever it is used. Hand-check accuracy: unknown until a person fills tableD_handcheck.csv.
- Next: step 5 Tab B (city stage medians vs OC best quartile, classified programs with source text + overdue flag, peers that completed the same category, draft-request button with static template when no key). Possibly split: 5a medians + program table, 5b peers + draft.

### Round 6 · 12:00 · Step 5 (part 1): Tab B city promise tracker (medians vs best quartile, programs, overdue, peers)
- Category: B
- Found: Tab B was a placeholder ("not built yet").
- Changed: analysis.py: peer_medians(), best_quartile() (25th pct of city medians, n ≥ MIN_N, excludes same-day median-0 cities: ASSUMPTION, needs ≥ 4 cities else "unknown"), load_programs(), add_overdue() (yes / no / unknown when no single target date), peers_completed(). app.py Tab B: city picker, one headline (slowest stage gap vs OC best quartile + programs past target), stage table with n, Claude-labelled program table with the city's own status text beside each row and the label method stated, peers that report completing the same category, sources and caveats expander (association not cause; no "broke a law" claim). tests/test_analysis.py: 2 new tests.
- Result: check.sh pass; tests 10 -> 12. All 35 Tab B cities render without exception (AppTest loop). OC best quartile: ent→permit 3.0 months (17 cities, 3 same-day excluded), permit→CO 6.2 months (23 cities). Overdue across 367 programs: 93 yes, 232 no, 42 unknown. Tustin: ent→permit ~17 months behind best quartile; 29 programs, 14 past target and not completed.
- Next: step 5 part 2: "Draft a request" button (claude-haiku-5-5 behind a button + st.cache_data, label "Draft: review before use", static template when no key, never sends). Then step 6 README/packaging and .claude/BUILD_COMPLETE.

### Round 7 · 12:03 · Step 5 (part 2): "Draft a request" in Tab B (never sent)
- Category: B
- Found: Tab B had no draft-request feature (build step 5, last item).
- Changed: drafts.py (new): static_template() quotes the city's own program name, objective, target date and status text from the 2025 Table D row (missing fields say "unknown"; [Your name]/[Organization] placeholders); claude_draft() calls claude-haiku-5-5 with a "use only the text given, no new numbers/laws, no violation or cause claims" system prompt. app.py: api_key() (env, .env via python-dotenv, or st.secrets; never shown), live_draft() under st.cache_data; Tab B picker "Program to ask about" (shows overdue flag), "Draft with Claude" button only when a key is set, API errors fall back to the template with a warning, text area labelled "Draft: review before use" and whether it is template or Claude. Nothing is sent. tests/test_drafts.py: 2 tests.
- Result: check.sh pass; tests 12 -> 14. AppTest: no key → no button, template shown, 0 exceptions across all 35 Tab B cities; fake key + mocked claude_draft → button click shows Claude-labelled draft, 0 exceptions. No live API call made this round.
- Next: step 6 packaging (README from templates/TEAM-README.md with Try it, sources, real vs mocked, where it's wrong; check .env.example), then create .claude/BUILD_COMPLETE. After that: flag in the Tab A headline when a city's figure uses separate (ASSUMPTION) draws.
