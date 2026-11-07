# NOTES: decision for the build session

Written Sat Nov 7, 2026, during the exploration session. Read this, then CLAUDE.md, before writing code.
Prototype only. Not legal, financial or lending advice.

## The decision

**Build "Permit Clock": a city-by-city timeline benchmark for Orange County, built from the
state's own permit reports. It turns "how long will this take in this city?" into months, with
the sample size shown, and turns the difference between two cities into dollars added to the
gap.**

- Lane: 2 Clear it, with a bridge into Lane 3 (time cost becomes gap dollars).
- Runner-up: Rate-to-Gap sensitivity (Lane 3). Not picked because the affordable-cost formula
  (HSC 50052.5) has to be read by hand from a site that blocks automated fetching, and getting
  the formula wrong breaks the whole tool.

> **Status (update):** the team wants the tool to suggest actions, not only show bottlenecks. A
> second round of data search is below ("More public data, round 2"). The final scope is still
> open; the APR Table A2 work stays the base in every option.

## More public data, round 2 (checked 2026-11-07)

None of these are in the starter DATA-SOURCES lists. All loaded today with metadata or
small-sample calls only.

| Dataset | What it adds | OC coverage today | URL / ID |
|---|---|---|---|
| **APR Table D: housing-element program implementation** | Each city's promised programs (e.g. ADU streamlining, permit-time review, objective design standards, CUP removal) with objective, target date and free-text status | 1,822 OC rows in report year 2025, 35 jurisdictions; 721–1,822 rows per year 2018–2025 | data.ca.gov APR dataset, resource `37724925-2014-4646-ade8-3ba9f3ff9fb8` |
| APR Table A (applications) | `APP_SUBMIT_DT`, status. Possible submit→entitlement stage via APN or tracking-ID join | 358,228 rows statewide | `c78b769d-cc02-4050-91ef-79ded665b5a8` |
| APR Table C (rezoning sites), G (land transferred), H (surplus land), I/E/F/F2/K/L | Rezone dates, surplus parcels, other housing-element reporting | Not counted for OC yet | same dataset (IDs in the CKAN `package_show`) |
| HCD Housing Element Compliance Report | Compliance status per city | OC 6th cycle: 33 "In", 2 "Out" (jurisdiction rows) | `2dcd1cd4-1348-4fc5-9c9c-219f82daac00` |
| HCD 6th-cycle RHNA Progress | Units permitted vs target by income level | 539 jurisdictions statewide | `1e80a9cf-724c-432d-8374-e9708a6a92dc` |
| HCD SB 35 determination map | Is streamlining available in this city | ArcGIS service, updated 2025-06 | https://data.ca.gov/dataset/streamlined-ministerial-approval-process-sb35-determination-map |
| **CA State Controller, City Expenditures** | Planning and "Construction and Engineering Regulation" spending per city per fiscal year: a staffing/capacity proxy | All 34 OC cities, FY 2022–2025 | https://bythenumbers.sco.ca.gov (Socrata `ju3w-4gxp`, updated 2026-10-28) |
| **LA City LADBS permits submitted 2020–present** | Real submitted→issued→CofO dates, ADU flag. The stage OC does not publish | 2024 ADU permits: 6,957 submitted, 5,769 issued, 3,333 with CofO | https://data.lacity.org Socrata `gwh9-jnip` (updated 2026-11-02); issued view `pi9x-tg5x` |
| **San Diego development permits** | Project create, deemed-complete, approval create/issue dates, affordable unit counts | Header read only | https://data.sandiego.gov/datasets/development-permits/ |

Notes:
- Table D statuses are free text ("Project is delayed.", "Ongoing as projects are submitted
  and reviewed.", "Completed. In December 2024, the City adopted Objective Design Standards…").
  Classifying it needs Claude. Do it once at build time and cache it to CSV, then hand-check a sample.
- Example (2025 APR, Tustin): objective "Update website with ADU permit guidance", target
  2022-06-01, status "Project is delayed." Show it beside the A2 timeline, but never claim the
  delay *caused* slower permits.
- LA and San Diego are SoCal but not OC. Use them only as a labelled reference for the stages
  OC does not measure, never as an OC number.
- LADBS, San Diego and APR tables C/G/H include street addresses. Keep everything at city level.
  Drop address and free-text notes columns at fetch time.

## The user (made up, from `lanes/2-clear-it/scenarios.json`, C02)

A nonprofit project manager with a small project (ADU or 2–4 units) that could go in one of two
OC cities. "Which city gets me to a ministerial approval faster?"

| | Before | After |
|---|---|---|
| Timeline | One rule of thumb: about 4 years, land to keys (brief; ASSUMPTION, not a measurement) | Median and middle-50% range, in months, per stage, per city, from the state's permit reports, with sample size n |
| Comparing two cities | Phone calls and anecdotes. No open permit data in OC (Lane 2 DATA-SOURCES) | Side by side for City A and City B. "Unknown" where a city did not report the dates |
| Money | Time cost is a vague line on the pro forma | Months of difference × carrying cost per month (ASSUMPTION, editable) = $ added to the gap |
| Trust | No way to tell if a number is solid | A data-coverage score per city: how many of its rows have the dates needed |

Portfolio "before vs after" to quantify on the day: number of OC cities with a usable benchmark
(n ≥ 30) per stage, and the dollar gap difference for one city pair.

## What we found in the data today (preliminary, checked 2026-11-07)

Source: HCD Housing Element APR Table A2 via the data.ca.gov CKAN API (resource
`fe505d9b-8c36-42ba-ba30-08bc4f34e022`). These are quick unfiltered queries: every unit type and
tenure, 2018–2025 report years, and only rows that hold both dates in the same row. The build has
to redo them properly.

- About 54,000 Orange County rows, 2018–2025 (5,213 to 7,456 per year).
- Entitlement-to-permit, in rows that hold both dates: median 616 days in Tustin (n=573), 602 in
  Buena Park (n=443), 789 in Stanton (n=129), 993 in Los Alamitos (n=38), 99.5 in Orange (n=162),
  52 in Santa Ana (n=109).
- **Anaheim (n=2,663) and Fullerton (n=1,626) show a median of 0 days.** The entitlement and
  permit dates are the same. That probably reflects how they report (for example ministerial
  ADUs). This is INFERRED, not confirmed. Show it as a reporting pattern, not "fastest city".
- **Gaps in the big cities.** Irvine has 16,084 rows but only 62 entitlement dates. Huntington
  Beach has 954 rows with a permit date and **0** completion (CO) dates. Costa Mesa has 56
  entitlement dates in 1,192 rows. For these cities the entitlement stage is "unknown" unless rows
  can be linked across years by APN or tracking ID.
- Permit-to-completion (build) is the best-covered stage: median 262 days in Anaheim, 373 in
  Fullerton, 701 in Mission Viejo.
- **Sources disagree:** BackyardADU.net says the City of Orange ADU median from permit to CO is
  263 days. Our unfiltered all-types query gave 190 days (n=162). They are different populations
  (ADU only vs all types, different linking). Show both, and do not pick one silently.
- 17 jurisdictions have at least 30 same-row entitlement-plus-permit pairs (2 of them show the
  0-day pattern). Preliminary.
- APR Table A (`c78b769d-cc02-4050-91ef-79ded665b5a8`, 358,228 rows statewide) has
  `APP_SUBMIT_DT` and `APPLICATION_STATUS` but no approval date. Joining it to A2 by APN or
  tracking ID could add an application-to-entitlement stage. Stretch goal only.

## Scope

**Must work (the demo):**
1. A cached OC extract of APR Table A2 in the repo (only the needed columns; see Data and privacy).
2. Stage durations per city: entitlement→permit, permit→CO. Show median, P25, P75, n, and %
   coverage. Filter by unit category (`UNIT_CAT`, e.g. ADU vs 2-4 vs 5+) and by year.
3. Compare two cities side by side, with "unknown" when n < 30 (ASSUMPTION: threshold chosen by
   us, editable).
4. A cost-of-delay panel: months of difference × carrying cost per month = $ on the gap.
   - The default carrying cost per month is an ASSUMPTION: the brief's synthetic $85k of time
     costs ÷ 48 months ≈ $1,771 per home per month. Label it SYNTHETIC/ASSUMPTION, and let the
     user type their own.
5. A sources panel on screen: dataset URL, resource ID, date pulled, row counts, and the caveats
   above.

**Cut first, in this order (and label it "mocked" or "not built" in the README):**
1. Claude memo: replace with a static template sentence.
2. Cross-year record linking by APN or tracking ID: fall back to same-row pairs only, and say so.
3. Survival curve (Kaplan-Meier for projects with a permit but no CO yet): skip it and show medians only.
4. Table A join (application-to-entitlement): skip it.
5. Map: skip it. A table and bar chart are enough.

**Never:** invent a city timeline, fee or deadline. Never claim a city "violates" a law. The data
cannot show that.

## How Claude is used inside the tool

- Claude Haiku 5.5 (`claude-haiku-5-5`) writes a 3–4 sentence plain-language memo for the PM
  from the computed comparison table. The app sends only the small table (numbers, n, coverage,
  source date), never raw rows. The prompt says to use only the numbers given and to say
  "unknown" where n is too small.
- Cache by (city A, city B, unit type, years) with `st.cache_data`, so each combination is called
  once. Expect cents for the whole day.
- The app works without an API key. The memo panel says "memo unavailable" instead.
- **A person checks** that every number in the memo matches the table shown beside it. The memo
  is labelled "Drafted by Claude: check against the table."
- Optional: Claude drafts (does not send) a short question to a city's permit desk about missing
  data. The rules allow drafting only.

## Plan (assumes the build starts around 10:45; shift if later)

| Time | Do | Done when |
|---|---|---|
| 10:45–11:15 | Repo skeleton, `requirements.txt`, `scripts/fetch_apr.py` pulls OC A2 via API (paged), saves `data/oc_apr_a2.csv` | CSV committed, row count printed and matches about 54k |
| 11:15–12:00 | `analysis.py`: clean dates, stage durations, coverage, medians/P25/P75/n by city × unit type | A table printed for Tustin vs Santa Ana. **Commit.** |
| 12:00–12:30 | `app.py` (Streamlit): city pickers, unit-type filter, side-by-side table, bar chart, sources panel | Runs locally. **Commit + push.** Lunch while it deploys |
| 12:30–1:00 | Cost-of-delay panel with the ASSUMPTION carrying cost. Deploy to Streamlit Community Cloud | Live URL works signed out |
| 1:00–1:30 | Claude memo (cached), or cut it. Cross-year linking if time allows | **Demo freeze at 1:30.** |
| 1:30–2:00 | README from `templates/TEAM-README.md`: user, before/after, Try it, sources table, real vs mocked, where it's wrong | README on `main` |
| 2:00–2:15 | 30-second video: one user, two cities, the months, the dollars, the sources | MP4 ready |
| 2:15–2:30 | Check: repo public (open it signed out), no keys (`git log -p | grep -i "sk-ant"`), no personal info, everything on `main`. Submit the form | Submitted before 2:30 |

## Stack

- **Streamlit (Python)**. It is analyst-native: pandas, plotting and a UI in one file, with no
  frontend work. That suits a solo analyst better than Next.js.
- **Deploy:** Streamlit Community Cloud (share.streamlit.io). Connect the public GitHub repo, set
  main file `app.py`, add `ANTHROPIC_API_KEY` under app Secrets (never in git). Fallback: run
  locally and screen-record.
- **Pinned deps** (`requirements.txt`). These are known-good versions. In the terminal session,
  install them, run `pip freeze`, and pin exactly what you tested:
  ```
  streamlit==1.40.0
  pandas==2.2.3
  plotly==5.24.1
  requests==2.32.3
  anthropic==0.39.0
  ```
  Use Python 3.11 or 3.12. Add a `runtime.txt` or set the Python version in Community Cloud. The
  `anthropic` pin is old: if `claude-haiku-5-5` is rejected, upgrade the SDK and re-pin.
- `.env.example` holds the line `ANTHROPIC_API_KEY=` only. `.env` is already git-ignored (check
  `.gitignore`).

## Datasets (all checked 2026-11-07 unless noted)

| Dataset | URL | Status today |
|---|---|---|
| HCD APR Table A2 (entitlements, permits, COs) | https://data.ca.gov/dataset/housing-element-annual-progress-report-apr-data-by-jurisdiction-and-year · API `https://data.ca.gov/api/3/action/datastore_search?resource_id=fe505d9b-8c36-42ba-ba30-08bc4f34e022` and `datastore_search_sql` | Works. 927,011 rows statewide. Filter `CNTY_NAME='Orange'`. Field is `JURIS_NAME` (not `JURS_NAME`) |
| HCD APR Table A (applications) | same dataset, resource `c78b769d-cc02-4050-91ef-79ded665b5a8` | Works. 358,228 rows. Stretch only |
| BackyardADU.net build_times.csv (third party, cross-check only) | https://backyardadu.net/data/build_times.csv | 200 OK. Cite the APR for anything official |
| Brief's 4-year baseline (ASSUMPTION) | `lanes/2-clear-it/data/timeline.json`, `docs/challenge-brief.pdf` | Rounded estimates, not measurements |
| Synthetic deal ($85k time cost) | `lanes/3-fund-it/data/synthetic-example-deal.json` | SYNTHETIC. Never present it as real |
| Freddie Mac PMMS (only if the rate-sensitivity stretch is built) | https://www.freddiemac.com/pmms/docs/PMMS_history.csv | 200 OK. Latest row 11/5/2026, 30-yr 7.18% |
| HCD 2026 State Income Limits (only for the runner-up idea) | https://www.hcd.ca.gov/sites/default/files/docs/grants-and-funding/income-limits-2026.pdf | 200 OK (PDF). Revised June 23, 2026 |

## Data and privacy

- A2 rows contain `STREET_ADDRESS`, `PROJECT_NAME` and a free-text `NOTES` field. **Drop
  `STREET_ADDRESS`, `PROJECT_NAME`, `NOTES`, `STD_ADDRESS`, `LATITUDE` and `LONGITUDE` in the
  fetch script.** Free text could contain a person's name. The tool needs only city, year, unit
  category, tenure, unit counts, dates, SB 35 flag, and APN or tracking ID for linking.
- APNs are public parcel identifiers, not personal information, but nothing in the UI is needed at
  parcel level. Show city-level aggregates only.
- Be kind to data.ca.gov: fetch once, cache to CSV, commit the CSV. Page with `limit` and
  `offset` and add a short sleep.

## Open questions

1. Is a same-day entitlement and permit (Anaheim, Fullerton) a ministerial path or a reporting
   habit? Ask a planner in the room. Until then, show it as "same-day (reporting pattern?)".
2. Should linking across report years use `JURS_TRACKING_ID` or `APN`? Test which gives more
   matches in Irvine and Huntington Beach.
3. Which `UNIT_CAT` values exist (ADU, SFD, 2 to 4, 5+, MH)? Confirm from the data before
   building filters.
4. Carrying cost per month: can someone in the room give a sourced figure? Until then, the
   synthetic-derived ASSUMPTION stays.
5. Team: the brief template was left as a placeholder. This plan assumes solo. A teammate could
   own the README, the video and the "where it's wrong" section.

## Ideas considered (scores 1–5: Impact / Works / Scale / Innovation / Portfolio)

| # | Idea | Lane | I | W | S | In | Port |
|---|---|---|---|---|---|---|---|
| 1 | **Permit Clock**: city stage-duration benchmarks plus cost of delay | 2→3 | 4 | 5 | 5 | 4 | 5 |
| 2 | Rate-to-Gap sensitivity (tornado / scenario) | 3 | 4 | 3 | 4 | 3 | 5 |
| 3 | Stale-site detector: housing-element sites already permitted | 1 | 4 | 4 | 4 | 4 | 4 |
| 4 | Site shortlist ranker with constraint flags | 1 | 5 | 2 | 4 | 3 | 4 |
| 5 | Surplus-land notice cleaner and ranker | 1 | 3 | 4 | 3 | 2 | 3 |
| 6 | City reporting-quality scorecard (fold into #1) | 2 | 3 | 5 | 5 | 3 | 4 |
| 7 | Funding-round timing planner | 3 | 4 | 1 | 3 | 4 | 3 |
| 8 | Stale-statute checker for city ADU checklists | 2 | 3 | 3 | 3 | 3 | 2 |

Details are in the exploration chat. Short reasons for the top two are under "The decision".

## Portfolio framing (one line)

*Business question:* how long does it really take to get a small housing project permitted and
built in each Orange County city, and what does the difference cost? *Finding:* in the state's own
reports, stage times differ by many months between cities, and several of the largest cities do
not report the dates needed to measure them. *Recommendation:* nonprofits should pick sites with
city timelines in hand and price the delay into the gap, and HCD and the cities should close the
reporting gaps so the benchmark covers all 34.

## Starter prompt for Claude Code (paste this in the terminal)

```
Read CLAUDE.md and NOTES.md in this repo first. NOTES.md is the decision; follow it.

Build "Permit Clock", a Streamlit app, solo, on main, committing after each step.

1. scripts/fetch_apr.py: page through the data.ca.gov CKAN datastore API for HCD APR
   Table A2 (resource_id fe505d9b-8c36-42ba-ba30-08bc4f34e022), filter CNTY_NAME = 'Orange'
   (field names: JURIS_NAME, YEAR, APN, JURS_TRACKING_ID, UNIT_CAT, TENURE, ENT_APPROVE_DT1,
   BP_ISSUE_DT1, CO_ISSUE_DT1, NO_ENTITLEMENTS, NO_BUILDING_PERMITS, NO_OTHER_FORMS_OF_READINESS,
   APPROVE_SB35, plus income-category unit counts). DROP STREET_ADDRESS, STD_ADDRESS,
   PROJECT_NAME, NOTES, LATITUDE, LONGITUDE. Sleep 1s between pages. Save data/oc_apr_a2.csv and
   data/SOURCE.json (URL, resource id, pulled-at timestamp, row count). Print the row count by
   year; it should be roughly 54k total for 2018-2025.
2. analysis.py (pure pandas, unit-testable): parse dates; compute per-record stage durations
   (entitlement->permit, permit->CO) first from same-row pairs, then try linking across report
   years by (JURIS_NAME, JURS_TRACKING_ID) and fall back to APN; drop negative durations and
   count them; flag 0-day entitlement->permit as "same-day". Output a table by city x UNIT_CAT x
   stage: n, median, P25, P75 in months, coverage % (rows with the needed dates / all rows).
   Mark any cell with n < 30 as "unknown" (the 30 threshold is an ASSUMPTION; make it a
   parameter).
3. app.py (Streamlit): pick City A and City B, unit category, year range. Show a side-by-side
   table and a bar chart with P25-P75 bars. Add a cost-of-delay panel: months difference x
   carrying cost per month. The default of $1,771/month is ASSUMPTION derived from the SYNTHETIC
   deal ($85k / 48 months) in lanes/3-fund-it/data/synthetic-example-deal.json; it must be
   editable and labelled on screen. Add a "Sources and caveats" panel: dataset URL, date pulled,
   row counts, the Anaheim/Fullerton same-day pattern, the Huntington Beach 0-CO gap, the
   BackyardADU disagreement for City of Orange. Add a footer saying it is a prototype and not
   legal or financial advice.
4. Optional memo: if ANTHROPIC_API_KEY is set, call claude-haiku-5-5 with ONLY the small
   comparison table and ask for a 3-4 sentence plain-language memo that uses only those numbers
   and says "unknown" where a cell is unknown. Cache with st.cache_data. With no key, show
   "memo unavailable". Label the memo "Drafted by Claude: check against the table".
5. requirements.txt with pinned versions, .env.example (ANTHROPIC_API_KEY= only), and a README
   following templates/TEAM-README.md, with a Try it section and a real-vs-mocked table.

Never invent a number, fee, deadline or statute. Say "unknown". Get a runnable version first
(steps 1-3), then improve. Tell me when each step works and commit it.
```
