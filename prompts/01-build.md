# Build prompt: Permit Clock v1

Paste this into Claude Code in the terminal for an attended build. The unattended loop
(`scripts/run_loop.sh` with `.claude/loop.md`) works through the same steps one per round.

---

Read CLAUDE.md and NOTES.md in this repo first. NOTES.md is the decision; follow it exactly.
Build "Permit Clock", a Streamlit app with two tabs. Commit after each step and tell me when
each step works. Run `bash scripts/check.sh` after each step; it must pass before you move on.
Design every screen to pass docs/ux-rubric.md: answer first, few inputs, one message per tab.

1. **scripts/fetch_apr.py.** Page through the data.ca.gov CKAN datastore API (limit and offset,
   sleep 1 second between pages) and save:
   - **`data/oc_apr_a2.csv`**, from APR Table A2 (resource fe505d9b-8c36-42ba-ba30-08bc4f34e022),
     filtered to CNTY_NAME = 'Orange'.
     - Keep: JURIS_NAME, YEAR, APN, JURS_TRACKING_ID, UNIT_CAT, TENURE, ENT_APPROVE_DT1,
       BP_ISSUE_DT1, CO_ISSUE_DT1, NO_ENTITLEMENTS, NO_BUILDING_PERMITS,
       NO_OTHER_FORMS_OF_READINESS, APPROVE_SB35, and the income-category unit counts.
     - Drop: STREET_ADDRESS, STD_ADDRESS, PROJECT_NAME, NOTES, LATITUDE, LONGITUDE.
   - **`data/oc_apr_tableD.csv`**, from APR Table D (resource 37724925-2014-4646-ade8-3ba9f3ff9fb8).
     Table D has no county column, so filter JURIS_NAME to the 34 OC cities plus ORANGE
     COUNTY. Take the names from lanes/2-clear-it/data/oc-cities.json, uppercased.
   - **`data/SOURCES.json`**, with URLs, resource ids, a pulled-at timestamp and row counts.

   Then print:
   - row counts by year. A2 should be about 54k for 2018-2025; D should be about 1.8k for 2025.
   - how many 2025 Table D rows match permit-related keywords (ADU, accessory, permit,
     streamlin, pre-approved, objective design, fee, CUP).

   Skip the download if the CSVs already exist.
2. **analysis.py.** Pure functions with pytest tests in tests/.
   - Parse dates. Compute per-record entitlement->permit and permit->CO days from same-row
     pairs.
   - Then try linking across report years by (JURIS_NAME, JURS_TRACKING_ID), falling back to
     APN. Report how many links each method finds.
   - Drop negative durations and count them. Flag a 0-day entitlement->permit as "same-day".
   - `summary(city, unit_cat)` returns n, P25/P50/P75/P80 in months and coverage %. It returns
     "unknown" when n < MIN_N (default 30, an ASSUMPTION).
   - `monte_carlo(city, unit_cat, start_date, monthly_cost, draws=5000, seed=42)` resamples
     durations. Draw both stages together when one record has both; otherwise draw them
     independently, labelled as an ASSUMPTION. It returns P50/P80 dates, P50/P80 carrying cost,
     contingency = P80 cost - P50 cost, and each stage's share of the spread.
3. **app.py, Tab A "Plan my project".**
   - Inputs:
     - City A and City B
     - unit category
     - start date
     - carrying cost, in an expander. Default $1,771/month, labelled "ASSUMPTION derived from
       the SYNTHETIC deal in lanes/3-fund-it/data/synthetic-example-deal.json: $85k / 48
       months; replace with yours".
   - On load, show a real result with defaults: one headline sentence ("Budget $X contingency.
     City B is about N months faster at P80"), a small P50/P80 table with n, and one chart.
   - Show "unknown" where n is too small, with what to try instead.
   - Add a "Sources and caveats" expander covering:
     - the Anaheim/Fullerton same-day pattern
     - the Huntington Beach 0-CO gap
     - the BackyardADU disagreement for City of Orange
   - Footer: "Prototype. Not legal, financial or lending advice."
   - Read only the CSVs in data/; make no network calls on page load. Cache with st.cache_data.
4. **scripts/classify_tableD.py.** This is the only step that spends the app's API credits.
   Skip it if data/tableD_classified.csv exists.
   - Keyword-filter the 2025 OC Table D rows.
   - Send batches of about 20 rows to claude-haiku-5-5, loading the key from .env with
     python-dotenv. Never print or log the key.
   - Ask for JSON per row:
     - category: ADU streamlining | pre-approved plans | permit-time review | objective
       standards | fees | process/CUP removal | other
     - status_bucket: completed | ongoing | delayed | not started | unclear
     - target_date: ISO date or null
   - Tell it to use only the text given, and to answer "unclear" when the status does not say.
   - Count tokens first and print the estimated cost before sending anything.
   - Save data/tableD_classified.csv with the source text kept.
   - Write data/tableD_handcheck.csv with 20 random rows for a person to check.
5. **Tab B "City promise tracker".**
   - Pick a city. Show its stage medians against the OC best quartile.
   - Show its classified programs with source text, target date and an overdue flag (target
     date before today and status not completed).
   - Show the peer cities that completed the same category.
   - Add a "Draft a request" button: claude-haiku-5-5 drafts (never sends) a short, polite note
     quoting the city's own program text and date. Cache it, and label it "Draft: review before
     use". With no API key, show a static template.
6. **Packaging.**
   - requirements.txt already exists with pins; add to it only if needed.
   - .env.example holds ANTHROPIC_API_KEY= only.
   - Write a README following templates/TEAM-README.md, with Try it, sources, real vs mocked,
     and where it's wrong.
   - When steps 1-6 all work, create .claude/BUILD_COMPLETE.

Rules:
- Never invent a number, fee, deadline or statute; say "unknown".
- Never say a program caused a change, or that a city violated a law.
- No addresses, APNs or project names in the UI.
- Get steps 1-3 running before anything else.
