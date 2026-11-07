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

### Round 8 · 12:04 · Step 6: team README and BUILD_COMPLETE
- Category: B
- Found: README.md was still the event README; no team README (build step 6). Hand-check file has 0 of 20 rows filled, so classifier accuracy is unknown.
- Changed: git mv README.md -> EVENT-README.md (event info kept, links still resolve from root). New README.md from templates/TEAM-README.md: made-up users with before/after, what it does (default headlines re-rendered via AppTest: $16,100 Tustin contingency, Santa Ana ~21 months faster at P80; Tustin Tab B 17 months behind best quartile, 14 of 29 programs past target), how Claude is used, Try it, sources table with ASSUMPTION/INFERRED rows, real vs mocked, where it's wrong, next steps, privacy. Team name, members, video and live-demo links left as "to fill". Created .claude/BUILD_COMPLETE (in + cut list). .env.example not inspected: reading it is denied by permissions; it is tracked and check.sh's key scan passes.
- Result: check.sh pass; 14 tests; build steps 1-6 done.
- Next: (1) Tab A headline: flag when a city's figure uses separate (ASSUMPTION) draws (Santa Ana default). (2) UX round: screenshot.py and score against docs/ux-rubric.md. (3) A person should check .env.example holds only ANTHROPIC_API_KEY= and fill tableD_handcheck.csv.

### Round 9 · 12:06 · Tab A headline flags cities whose P80 uses separate (ASSUMPTION) draws
- Category: C
- Found: default Tab A headline said "Santa Ana is about 21 months faster than Tustin at P80" with no sign that Santa Ana's figure uses separate per-stage draws (n_paired=6 < MIN_N); the ASSUMPTION label only appeared in the table's Method row.
- Changed: app.py: headline appends "ASSUMPTION: too few records hold both stages for <city>, so its stages were drawn separately; treat its P80 as rough." for each picked city with a known P80 and method != paired. tests/test_app_headline.py (new AppTest): Santa Ana flagged, Tustin (paired) not.
- Result: check.sh pass; tests 14 -> 15. Default view now carries the ASSUMPTION flag in the headline.
- Next: (1) UX round: screenshot.py, score against docs/ux-rubric.md. (2) Edge cases: City A = City B, unit type with n = 0 in Tab A. (3) README: mention the headline flag in "where it's wrong".

### Round 10 · 12:12 · Tab A headline cautions when a picked city reports mostly same-day entitlement → permit
- Category: C
- Found: (1) Edge-case sweep: AppTest over all 34 cities × 7 unit types (238 runs), plus City A = City B: 0 exceptions, so there was nothing to fix in category E. (2) Ran screenshot.py and read the desktop/phone fold PNGs for both tabs: headline above the fold on desktop and phone, 4 inputs, ASSUMPTION next to the numbers. No full rubric score this round (full-page shots not read). (3) Honesty gap: choosing Anaheim (72.2% same-day, n=2,663) or Fullerton (85.1%, n=1,626) in Tab A gives a "faster" headline, but the same-day caveat appeared only in the Sources expander. Santa Ana is 0.0% same-day, so the default view is unaffected.
- Changed: app.py: SAME_DAY_FLAG_PCT = 50 (ASSUMPTION). The headline adds "Caution: most of <city>'s entitlement → permit records give the same date for both (likely a reporting pattern, INFERRED)…" for any picked city at or above it. tests/test_app_headline.py: new test (Anaheim flagged, Tustin not, Santa Ana not).
- Result: check.sh pass; tests 15 -> 16.
- Next: (1) Tab B program table: two Tustin rows show the same truncated name "1.7 (Modified) Accessory Dwelling Units Program a. Promote the const…" with different categories, so the reader cannot tell them apart. Show more of the objective or a distinct sub-item. (2) Full UX rubric score from the *-full.png shots. (3) Headline grammar when both cities use separate draws ("its" -> "their").

### Round 11 · 12:13 · Tab B: same-looking program names now distinguishable
- Category: C
- Found: In the 2025 Table D data, 15 cities list the same or near-same PROGRAM_NAME on several rows (e.g. Tustin 12 rows, La Habra 29). After the selectbox's 110-char cut, Tustin's "1.7 (Modified) Accessory Dwelling Units Program a. Promote the const…" appeared twice with different categories/objectives, so a reader could not tell which program was overdue or which one the draft was about.
- Changed: analysis.py: `program_labels()`: collapse whitespace, shorten names to 60 chars; where two of a city's shortened names match, add the start of that row's own PROGRAM_OBJECTIVE; if still equal (Costa Mesa overlays differ only at the end), show the end of the name. app.py: Tab B program table "Program" column and the "Program to ask about" picker use these labels (no new text, only the city's own words). tests/test_analysis.py: 2 tests.
- Result: check.sh pass; tests 16 -> 18. Rows sharing an exact PROGRAM_NAME with another row in the same city: 122 (15 cities); rows with an identical label after this change: 0 of 367.
- Next: (1) Full UX rubric score from the *-full.png shots. (2) Headline grammar when both cities use separate draws ("its" -> "their"). (3) README: mention the headline flags (separate draws, same-day caution) in "where it's wrong".

### Round 12 · 12:14 · Tab A headline flags read correctly when both cities are flagged
- Category: C
- Found: Round 11 queue item. When both picked cities triggered a flag, the headline said "for X and Y, so its stages were drawn separately; treat its P80 as rough" and "most of Anaheim and Fullerton's … records … so its speed there may be overstated", which reads as one combined city.
- Changed: app.py: both flags use "its" for one city and "their" for two; the same-day caution says "Anaheim and Fullerton's each" for two cities. tests/test_app_headline.py: new AppTest (Anaheim vs Fullerton → plural wording).
- Result: check.sh pass; tests 18 -> 19. Single-city wording unchanged (existing tests still pass).
- Next: (1) Full UX rubric score from the *-full.png shots. (2) README: mention the headline flags (separate draws, same-day caution) in "where it's wrong". (3) A person should fill data/tableD_handcheck.csv.

### Round 13 · 12:17 · Tab B: OC best-quartile benchmark shows how many cities it is built from
- Category: D
- Found: screenshot.py → .ux/tab2-desktop-full.png: the Tab B stage table showed "OC best quartile: 3 months" with no n, failing UX rubric #4 ("every benchmark shows its n beside it"). Also found the *-full.png shots stop at 800 px (Streamlit scrolls inside its own container), so a full 13-point score cannot be read from them; scored items visible above the fold only.
- Changed: app.py: `best_q_n()` (cached) counts the cities behind the benchmark; column renamed "OC best quartile (n)", cell reads e.g. "3 months (14 cities)", "unknown" when the benchmark is unknown. tests/test_app_headline.py: AppTest checks the cell's city count equals peer_medians (n ≥ MIN_N, same-day excluded).
- Result: check.sh pass; tests 19 -> 20. Rubric #4 fail -> pass on Tab B. Counts: entitlement → permit 14 cities (17 with n ≥ 30, 3 same-day left out; round 6's "17 cities" counted those 3), permit → CO 23 cities.
- Next: (1) Fix screenshot.py full-page capture (scroll Streamlit's main container) so a full rubric score is possible — note: scripts/ edits other than run_loop.sh/check.sh are allowed. (2) README: mention the headline flags (separate draws, same-day caution) in "where it's wrong". (3) A person should fill data/tableD_handcheck.csv.

### Round 14 · 12:18 · screenshot.py captures whole pages, so the full UX rubric can be scored
- Category: D
- Found: Round 13: the *-full.png shots stopped at the viewport (800 px desktop) because Streamlit scrolls inside its own container, so items below the fold (#7 chart, #11 ends in an action, #13 disclaimer) could not be scored.
- Changed: scripts/screenshot.py: `content_height()` reads the scrollHeight of Streamlit's main container (capped at 8,000 px); the "full" shot grows the viewport to that height, captures, then restores it. Fold shots unchanged.
- Result: check.sh pass; 20 tests. Full-shot height: desktop tab 1 800 -> 1583 px, tab 2 800 -> 2169 px; phone tab 1 -> 1943 px, tab 2 -> 2705 px. First full rubric score (both tabs, desktop + phone): 12/13. Passing: answer first, 4 inputs, one headline per tab, n beside every benchmark, ASSUMPTION next to numbers, one chart with labelled axes and fixed A/B colors, phone headline in first screen, Tab B ends with an unsent draft, no clutter, one small disclaimer. Failing: #5 plain language: Tab B's stage table says "Permit → CO" with no explanation of CO on that tab (Tab A explains it as "Move-in (CO)"). Not timed: #10.
- Next: (1) Tab B: explain "CO" (certificate of occupancy, move-in) on first use, e.g. in the medians caption (rubric #5). (2) Tab B program table: Program column cuts off the objective snippet at 1280 px; consider a wider column or shorter label. (3) Time a re-render after an input change (rubric #10).

### Round 15 · 12:19 · Tab B spells out "CO" (certificate of occupancy) beside its stage table
- Category: D
- Found: Round 14 full UX score 12/13; failing #5 plain language: Tab B's stage table says "Permit → CO" with no explanation on that tab (Tab A explains it only in a date-input help tooltip and "Move-in (CO)" column).
- Changed: app.py: Tab B medians caption now starts "CO = certificate of occupancy, the sign-off that people can move in." (same wording as Tab A's help text). tests/test_app_headline.py: AppTest checks the caption carries the definition.
- Result: check.sh pass; tests 20 -> 21. UX rubric 12/13 -> 13/13 on scored items (#10 timing still not measured).
- Next: (1) Time a re-render after an input change (rubric #10). (2) Tab B program table: Program column cuts off the objective snippet at 1280 px. (3) README: mention the headline flags (separate draws, same-day caution) in "where it's wrong".

### Round 16 · 12:21 · README states when the Tab A headline flags appear; re-render timed
- Category: F (after an E/D check found nothing to fix)
- Found: (1) Rubric #10 timed with AppTest: first run 1.44 s; changing City A 0.17–0.24 s, unit type 0.38 s, so #10 passes and needs no change. (2) README "Where it gets things wrong" said the app "flags" same-day cities and mentioned separate draws, but not when or where: the Tab A headline cautions at ≥ 50% same-day records (SAME_DAY_FLAG_PCT, ASSUMPTION) and flags separate draws below MIN_N = 30 paired records.
- Changed: README.md: the two bullets now give the trigger, the threshold (labelled ASSUMPTION) and that the warning is in the Tab A headline.
- Result: check.sh pass; 21 tests. UX rubric 13/13 (#10 now measured: < 0.4 s per input change).
- Next: (1) Tab B program table: Program column cuts off the objective snippet at 1280 px. (2) A person should fill data/tableD_handcheck.csv. (3) Phone-width check of Tab B draft section.

### Round 17 · 12:23 · Tab B program table shows the target date next to the overdue flag
- Category: D
- Found: screenshot.py → .ux/tab2-desktop-full.png (Tustin, 1280 px): only Overdue, Program and Category fit on screen; "Target date" was the 5th column, scrolled off the right edge, so a reader saw "yes" (overdue) with no date to explain it.
- Changed: app.py: Tab B program table column order is now Overdue, Target date, Program, Category, Status, city's own text (no data or wording change). tests/test_app_headline.py: AppTest checks the first three columns.
- Result: check.sh pass; tests 21 -> 22. Overdue rows with their target date visible without scrolling at 1280 px: 0 -> all (14 of 14 overdue for Tustin).
- Next: (1) Program column still cuts the objective snippet at 1280 px (e.g. "— Update ADU Ordinar…"); consider column_config width or a shorter name_len. (2) Phone-width check of Tab B draft section. (3) A person should fill data/tableD_handcheck.csv.

### Round 18 · 12:26 · Tab B stage table keeps the OC benchmark on screen at phone width
- Category: D
- Found: screenshot.py → .ux/tab2-phone-full.png (390 px): the Tab B stage table was a scrolling st.dataframe; only Stage and "Tustin median (n)" fit, so the "OC best quartile (n)" benchmark and "Gap" were off the right edge (UX rubric #4, n beside every benchmark, failed on phone).
- Changed: app.py: the stage table is rendered with st.table, which wraps text, instead of st.dataframe; no data or wording change. tests/test_app_headline.py: the best-quartile test reads at.table instead of at.dataframe (same assertions).
- Result: check.sh pass; 22 tests. Phone stage-table columns visible without scrolling: 2 of 4 -> 4 of 4 (.ux/tab2-phone-fold.png); desktop unchanged in layout.
- Next: (1) Program column still cuts the objective snippet at 1280 px. (2) Peer list category labels mix case ("ADU streamlining" vs "fees"); consider a display label map. (3) A person should fill data/tableD_handcheck.csv.

### Round 19 · 12:27 · Tab B Program column is wide enough to read at 1280 px
- Category: D (a C/E pass over app.py found nothing new: the overdue logic, the best-quartile n and the unknown paths were already tested)
- Found: queued by rounds 16–18: in .ux/tab2-desktop-full.png (Tustin, 1280 px), Program was a default-width column, so labels were cut well before the objective snippet that tells same-named rows apart.
- Changed: app.py: the Tab B program table sets `column_config={"Program": TextColumn(width="large")}` (no data or wording change). tests/test_app_headline.py: an AppTest checks the Program column width is "large".
- Result: check.sh pass; tests 22 -> 23. In the new .ux/tab2-desktop-full.png the full ~60-character name and the start of the objective ("— Up…", "— Est…") are visible. Trade-off: Status is now cut off at the right edge at 1280 px. Overdue already says whether a program is reported completed, and Status is one scroll away.
- Next: (1) If Status matters on screen, shorten program_labels name_len (e.g. 45) so Status fits too. (2) The peer list's category labels mix case ("ADU streamlining" vs "fees"). (3) A person should fill data/tableD_handcheck.csv.

### Round 20 · 12:30 · Tab B program table keeps Status on screen at 1280 px
- Category: D
- Found: screenshot.py → .ux/tab2-desktop-full.png (Tustin, 1280 px): after round 19 widened Program, the Status column ("ongoing", "delayed", "unclear") was cut to "on|", "del|" at the right edge, while Category took the visible space. Status tells a reader whether an overdue program is being worked on, so it helps the decision more than Category does.
- Changed: app.py: Tab B program table column order is now Overdue, Target date, Program, Status, Category, city's own text (no data or wording change). tests/test_app_headline.py: the column-order AppTest now checks the first four columns.
- Result: check.sh pass; 23 tests. Columns fully readable at 1280 px: Overdue, Target date, Program, Category -> Overdue, Target date, Program, Status (Category is now the one at the edge).
- Next: (1) Tustin labels all start "6th HE Cycle …", which uses up the 60-char name budget; consider removing a prefix that every row in a city shares from the label (city's own words, just shorter). (2) The peer list's category labels mix case ("ADU streamlining" vs "fees"). (3) A person should fill data/tableD_handcheck.csv.

### Round 21 · 12:31 · Tab B program labels drop leading words every one of a city's names shares
- Category: D
- Found: Round 20 queue: all 29 Tustin program names start "6th HE Cycle", which used 13 of the 60-character label budget on every row (e.g. "6th HE Cycle 1.7 (Modified) Accessory Dwelling Un…"). A scan of data/tableD_classified.csv found 9 more cities whose names all start with the same words ("Program ", "Policy Action ").
- Changed: analysis.py: new `_drop_shared_lead()`; `program_labels()` leaves out leading whole words shared by every name in a city with ≥ 3 programs and never empties a name. The draft, the city's own status text and the data are unchanged; only the on-screen label is shorter. tests/test_analysis.py: new test (Tustin-style prefix dropped; "PP-B.5"/"PP-G.2" kept because no whole word is shared; a name made only of shared words is kept).
- Result: check.sh pass; tests 23 -> 24. Cities whose labels start with words that differ: 10 more (Tustin, Garden Grove, Laguna Woods, Lake Forest, Los Alamitos, Mission Viejo, Orange County, San Clemente, Seal Beach, Westminster). Tustin label now e.g. "1.7 (Modified) Accessory Dwelling Units Program a. Promote… — Update ADU Ordinance…".
- Next: (1) Re-screenshot Tab B (Tustin, 1280 px) to confirm the labels read well. (2) A person should fill data/tableD_handcheck.csv. (3) README: note that program labels are shortened (city's own words, shared lead words left out).

### Round 22 · 12:32 · README says how Tab B shortens program names
- Category: F
- Found: Round 21 queue: Round 21 shortened the on-screen program labels (it leaves out lead words that every name in a city shares), but README.md line 37 only said "Every program label sits next to the city's own status text". Nothing told a reader that the names on screen are shortened, or that the draft uses the full name (drafts.py uses PROGRAM_NAME, not program_labels).
- Changed: README.md: the City promise tracker bullet now says names on screen are the city's own words, shortened (shared lead words left out, e.g. Tustin's "6th HE Cycle"; same-looking names add the start of their own objective), and that the data and the draft keep the full names.
- Result: check.sh pass; 24 tests. Ways the app changes on-screen text that the README describes: missing -> described.
- Next: (1) Re-screenshot Tab B (Tustin, 1280 px) to confirm the shortened labels read well. (2) The peer list's category labels mix case ("ADU streamlining" vs "fees"). (3) A person should fill data/tableD_handcheck.csv.

### Round 23 · 12:34 · Draft quotes the city's text on one line per field
- Category: D
- Found: screenshot.py → .ux/tab2-desktop-full.png (Tustin, 1280 px): the static draft's "- Program:" bullet broke over three lines ("6th HE Cycle  1.7 (Modified) Accessory Dwelling Units Program", blank line, "a.    Promote…"), so the quoted name ran into what looked like a new paragraph. 218 of 367 rows in data/tableD_classified.csv have a line break or double space in name, objective or status.
- Changed: drafts.py: `_field()` joins the city's words with single spaces (same words, same order; nothing added or removed). Applies to the static draft and the text sent to Claude. tests/test_drafts.py: new test that a multi-line name becomes one quoted line and the Objective bullet follows it.
- Result: check.sh pass; tests 24 -> 25. Lines in the Tustin draft's Program bullet: 3 -> 1.
- Next: (1) Some Tustin labels still start "Goal 1: Adequate Housing Supply 6th HE Cycle 1.1…" (not every name shares that lead), so the Program column is filled by the same words; consider it. (2) The peer list's category labels mix case ("ADU streamlining" vs "fees"). (3) A person should fill data/tableD_handcheck.csv.

### Round 24 · 12:37 · Same-day share is "unknown" below MIN_N, so no caution from 5 records
- Category: C (found during an E sweep: every city with Unit type = Mobile home and a 2020 start date ran with no exception)
- Found: Yorba Linda + Mobile home: the Tab A headline said contingency was unknown (too few records) but also "Caution: most of Yorba Linda's entitlement → permit records give the same date…". `A.summary` returned same_day_pct = 100.0 from n = 5 (MIN_N = 30): a statistic from a cell below MIN_N that was not shown as "unknown".
- Changed: analysis.py: `summary()` sets same_day_pct to "unknown" when n < min_n (docstring says so). tests/test_analysis.py: asserts same_day_pct is a number at n = 40 and "unknown" with min_n = 50. tests/test_app_headline.py: new AppTest (Yorba Linda, MH): no "Caution: most of". README.md: the same-day bullet says the caution needs at least 30 records.
- Result: check.sh pass; tests 25 -> 26. Same-day cautions drawn from n < 30: possible -> none. Anaheim/Fullerton all-types cautions unchanged (existing tests pass).
- Next: (1) Some Tustin labels start "Goal 1: Adequate Housing Supply 6th HE Cycle…" and fill the Program column with the same words. (2) Check other on-screen percentages (coverage_pct) for n < MIN_N. (3) A person should fill data/tableD_handcheck.csv.

### Round 25 · 12:39 · Tab B labels start at the program line, not the goal heading
- Category: D
- Found: Round 23/24 queue: 4 of 29 Tustin labels began "Goal 1: Adequate Housing Supply 6th HE C…" (raw names put a goal heading, then repeat "6th HE Cycle" before the program line), so the Program column showed the same heading words and cut off the program number.
- Changed: analysis.py: `_drop_shared_lead()` labels from after the last repeat of the city's shared lead when words follow it (on-screen label only; data and draft keep full names). tests/test_analysis.py: new test (heading skipped; a trailing repeat with nothing after it leaves the name as is). README.md: label bullet says so.
- Result: check.sh pass; tests 26 -> 27. Tustin labels starting "Goal": 4 -> 0; labels still unique 29/29; no empty labels across all 367 rows.
- Next: (1) Re-screenshot Tab B (Tustin, 1280 px) to confirm the labels read well. (2) The peer list's category labels mix case ("ADU streamlining" vs "fees"). (3) A person should fill data/tableD_handcheck.csv.

### Round 26 · 12:41 · Tab B gap equals the difference of the numbers shown beside it
- Category: D (rubric #4, numbers readable)
- Found: screenshot.py → .ux/tab2-desktop-full.png (Tustin, 1280 px): the Permit → CO row showed "9 months (n=634)" vs OC best quartile "6 months (23 cities)" with Gap "2.5 months behind". The gap came from unrounded medians, so the row did not add up for a reader. (Round 24 queue item "coverage_pct below MIN_N" checked: coverage_pct is not shown anywhere in the UI, so nothing to fix.) UX score: 12/13 -> 13/13 (only #4 failed).
- Changed: app.py: Tab B gap = shown (half-month) median − shown best quartile; the headline "slowest stage" uses the same gap. tests/test_app_headline.py: new AppTest `test_tab_b_gap_matches_shown_values` (fails on the old code: 2.5 != 9 − 6).
- Result: check.sh pass; tests 27 -> 28. Tustin Permit → CO gap: 2.5 -> 3 months; Entitlement → permit unchanged (17).
- Next: (1) The peer list's category labels mix case ("ADU streamlining" vs "fees"). (2) A person should fill data/tableD_handcheck.csv. (3) Check Tab A's numbers add up the same way (P80 − P50 contingency vs shown months).

### Round 27 · 12:43 · Tab A contingency equals the difference of the costs shown beside it
- Category: C (statistic shown inconsistently; Round 26 queue item 3)
- Found: a scan of all 15 cities with a known contingency (All types) found 2 whose shown contingency did not equal shown P80 − shown P50: Santa Ana (default City B) showed "$16,300 / $33,000" with contingency "$16,800"; Orange showed $3,100 vs a $3,000 difference. Cause: the contingency was rounded from unrounded costs.
- Changed: app.py: new `shown_contingency()` = round(P80, -2) − round(P50, -2); used in the headline and the table. tests/test_app_headline.py: new AppTest `test_tab_a_contingency_matches_shown_costs` (fails on the old code: 16800 != 33000 − 16300).
- Result: check.sh pass; tests 28 -> 29. Cities whose contingency row does not add up: 2/15 -> 0/15. Santa Ana contingency: $16,800 -> $16,700.
- Next: (1) The peer list's category labels mix case ("ADU streamlining" vs "fees"). (2) A person should fill data/tableD_handcheck.csv. (3) Check the Tab A chart (P80 − P50 buffer per stage) uses the same shown values as the table.

### Round 28 · 12:45 · Tab A buffer chart equals the difference of the months shown in the table
- Category: C (statistic shown inconsistently; Round 27 queue item 3)
- Found: the default view's chart plotted unrounded P80 − P50: Santa Ana entitlement → permit bar = 10.41 months while the table shows "1.5 months / 12 months" (difference 10.5); Tustin 10.81 vs 31 − 20 = 11; Santa Ana permit → CO 1.81 vs 7.5 − 6 = 1.5. A bar was also drawn when only P80 was unknown.
- Changed: app.py: new `half()` (nearest half month, used by `months()` and the Tab B gap); chart bars = half(P80) − half(P50), and no bar if either one is unknown. tests/test_app_headline.py: new AppTest `test_tab_a_chart_buffer_matches_shown_months` (fails on the old code, passes now).
- Result: check.sh pass; tests 29 -> 30. Default-view bars that do not match the table: 4/4 -> 0/4.
- Next: (1) The peer list's category labels mix case ("ADU streamlining" vs "fees"). (2) A person should fill data/tableD_handcheck.csv. (3) Check the Tab A move-in dates against the shown P50/P80 months (start + months).
