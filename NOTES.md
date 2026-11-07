# NOTES: decision for the build session

Written Sat Nov 7, 2026, during the exploration session. Read this, then CLAUDE.md, before writing code.
Prototype only. Not legal, financial or lending advice.

## Start here: build on API credits, then let it improve itself unattended

**What is in the repo for this:**

| File | What it does |
|---|---|
| `prompts/01-build.md` | The build prompt (6 steps). Paste it for an attended build |
| `.claude/loop.md` | The prompt for one round. Each round does the next build step or makes one improvement (honesty, UX, function, docs) and logs it in `ITERATION_LOG.md` |
| `docs/ux-rubric.md` | The 13-point "minimalist, function first" checklist. Rounds score screenshots against it |
| `scripts/run_loop.sh` | The unattended loop. Each round is `claude -p` with a fresh context and a $ cap. Then `scripts/check.sh` runs: **push if it passes, revert if it fails**, so `main` always holds a working version. Stops at `STOP_AT` (default 13:30), at the total $ cap (default $40), after 3 failed rounds in a row, or when a `STOP` file appears. Never pushes after 14:20 |
| `scripts/check.sh` | The gate: no key in tracked files, every file compiles, tests pass, and `app.py` runs top to bottom **with no API key** (Streamlit AppTest) |
| `scripts/screenshot.py` | Captures each tab at desktop and phone width into `.ux/` for the UX review |
| `setup/claude-settings.json` | Permission rules to copy to `.claude/settings.json`. They allow the routine dev commands, block reading `.env`, force-push and `rm -rf`, and stop Claude editing the loop and check scripts |

All tested on 2026-11-07 against a dummy app, a stand-in `claude` command and a local git
remote: a good round was pushed, a broken round was reverted, and the budget, `STOP` file and
`STOP_AT` each ended the loop.

**Steps on your laptop (about 15 minutes):**

1. **Credits.** In the Claude Console (platform.claude.com), claim the event credits and create an
   API key for the app. Optional but recommended: set a spend limit on the "Claude Code"
   workspace (Console → workspace limits). That workspace is created when Claude Code first
   signs in with the Console, so set the limit after step 3.
2. **Repo and Python.**
   ```bash
   git clone https://github.com/Mahabala-O/zero-gap && cd zero-gap
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt -r requirements-dev.txt
   python -m playwright install chromium
   cp .env.example .env            # then paste the app's API key into .env
   cp setup/claude-settings.json .claude/settings.json
   ```
3. **Sign Claude Code in to your credits.** Run `claude`, type `/login`, and choose the
   Anthropic Console (API billing) account. Type `/model` and pick Sonnet; it costs less than
   Opus and is enough for this build. Exit with `/exit`.
   - Signed in this way, **Remote Control is not available** (it needs a claude.ai plan, not
     API keys), so you cannot steer it from your phone. You can still **watch** it: commits
     appear on GitHub and `ITERATION_LOG.md` updates after every round.
4. **Optional, recommended: one attended step (5–10 min).** Run `claude`, paste
   `prompts/01-build.md` and add "Do step 1 only". Confirm the CSVs and row counts look right,
   commit, `/exit`.
5. **Start the unattended loop, then leave:**
   ```bash
   bash scripts/run_loop.sh
   ```
   - The defaults are `STOP_AT=1330`, `MAX_TOTAL_USD=40`, `MODEL=sonnet`,
     `PERMISSION_MODE=auto`. Override them inline, e.g.
     `STOP_AT=1345 MAX_TOTAL_USD=35 bash scripts/run_loop.sh`.
   - If the preflight says auto mode is unavailable, run
     `PERMISSION_MODE=acceptEdits bash scripts/run_loop.sh`. That mode relies on the allowlist
     from step 2.
   - Keep the laptop **plugged in, awake and online**. On a Mac, run it as
     `caffeinate -i bash scripts/run_loop.sh`.
   - To stop it early from the laptop, `touch STOP` in another terminal (it is checked between
     rounds).
6. **When you're back:**
   - Read `ITERATION_LOG.md`. It is your before/after story.
   - Run `streamlit run app.py` and click through both tabs.
   - Check the 20 rows in `data/tableD_handcheck.csv` by hand and put the accuracy in the
     README.
   - Deploy to Streamlit Community Cloud, with the key in Secrets.
   - Then do the README and video steps of the plan below.

**Budget (our choices, not measurements):**
- About $40 for the loop and the $0.25 preflight. The rest of the $100 covers the Table D
  classification run (Haiku, estimated by the script before it sends anything), live drafts,
  and any attended work.
- `--max-budget-usd` is checked against Claude Code's own estimate, and spend can pass the cap
  a little, so the defaults leave headroom.
- Check spend anytime on the Console's Cost page.

## The decision (locked)

**Build "Permit Clock", one Streamlit app with two tabs, both built on the state's own housing
reports for Orange County:**

- **Tab A, Plan my project.** For a nonprofit project manager: a Monte Carlo schedule forecast
  from real permit timelines. It gives likely (P50) and safe-to-plan (P80) dates, the carrying
  cost at each, a contingency to budget, which stage drives the risk, and which of two cities is
  faster.
- **Tab B, City promise tracker.** For city staff or an advocate: the city's slowest stage
  versus its OC peers, and what the city **promised** in its housing element about permitting
  (APR Table D), sorted by Claude into type and status, with overdue items flagged. It also
  lists the peer cities that finished the same kind of program, and drafts (does not send) a
  request that quotes the city's own commitment.

Lane: 2 Clear it, with a bridge to Lane 3 (time cost becomes gap dollars).

Why both: Tab A is the analytics core. Tab B turns the finding into an action that someone could
take next month. They share the same stage-time table, so B is an extra view of the same data,
not a second project.

## The users (made up, from `lanes/2-clear-it/scenarios.json`)

| | Before | After |
|---|---|---|
| **C02, nonprofit project manager**, small project (ADU, 2–4 or 5+ units) that could go in one of two OC cities | One rule of thumb: about 4 years, land to keys (brief; ASSUMPTION, not a measurement). Phone calls. No open permit data in OC | P50/P80 dates per stage for City A vs City B, with sample size n. Contingency $ = P80 cost − P50 cost. "City B is about N months faster at P80, about $Y less carrying cost." "Unknown" where a city did not report |
| **C03, city permit tech, housing staff or advocate** | Housing-element programs are buried in annual-report text. Nobody tracks which permitting promises are overdue | "Your slowest stage is X, N months behind the fastest quarter of OC cities. You have K permitting programs; J are past their target date. Peers A and B completed the same kind of program." Plus a drafted, unsent request quoting the promise |

Portfolio "before vs after" to measure on the day:
- How many OC cities have a usable benchmark (n ≥ 30) per stage.
- The P80 contingency $ for one city pair.
- How many OC permitting promises are past their target date.
- How accurate Claude's classification was on a hand-checked sample (e.g. 18 of 20 correct).

## Data findings so far (preliminary, checked 2026-11-07)

From quick, unfiltered queries on APR Table A2 (`fe505d9b-8c36-42ba-ba30-08bc4f34e022`). These
count only rows that hold both dates in the same row. Redo them properly in the build.

- About 54,000 OC rows for 2018–2025. Unit categories: SFD 26,165, ADU 18,808, SFA 4,176,
  5+ 2,875, 2 to 4 1,458, MH 96.
- **Comparing legal paths is not possible:** only 32 OC rows carry an SB 35 approval
  (`APPROVE_SB35='Y'`) and about 113 rows carry SB 9. Do not build a "file under law X" feature.
- Only 513 OC rows hold building permits with deed-restricted affordable units (5,947 units).
  Benchmarks for affordable projects alone will be thin, so fall back to all projects and say so.
- Entitlement→permit medians: Tustin 616 days (n=573), Buena Park 602 (n=443), Stanton 789
  (n=129), Los Alamitos 993 (n=38), Orange 99.5 (n=162), Santa Ana 52 (n=109).
- **Anaheim (n=2,663) and Fullerton (n=1,626) show a median of 0 days.** The entitlement date
  equals the permit date. This is probably how those cities report; that reading is INFERRED.
  Show it as "same-day (reporting pattern?)", never as "fastest".
- **Reporting gaps:** Irvine has 16,084 rows but only 62 entitlement dates. Huntington Beach has
  954 permit dates and 0 completion (CO) dates. Costa Mesa has 56 entitlement dates in 1,192 rows.
- ADU permit→CO medians among cities with n ≥ 30 run from San Clemente 147 days (n=41) to
  Fullerton 328 (n=932). Yorba Linda shows 31 days (n=31), which looks suspicious.
- **Sources disagree:** BackyardADU.net gives 263 days permit→CO for City of Orange ADUs. Our
  ADU-only query gave 187.5 (n=86), and the all-types query gave 190. Show both.
- Table D example (2025 APR, Tustin): objective "Update website with ADU permit guidance", target
  2022-06-01, status "Project is delayed." Show it beside the timeline, but never claim it caused
  the delay.

## Scope

**Must work:**
1. Cached OC extracts in `data/`: APR Table A2 (needed columns only) and APR Table D (OC only).
   Plus `data/SOURCES.json` with URL, resource ID, pulled-at time and row counts.
2. `analysis.py`: stage durations per record (entitlement→permit, permit→CO). Summary by city ×
   unit category with n, P25/P50/P75/P80 and coverage %. Cells with n < 30 show "unknown"
   (ASSUMPTION: the threshold is a parameter).
3. **Tab A:**
   - Inputs: City A and City B, unit category, start date, carrying cost per month.
   - Monte Carlo (e.g. 5,000 draws): resample stage durations from that city × unit category.
     Where a record has both stages, draw them together, which keeps the link between the
     stages. Otherwise draw them independently, labelled ASSUMPTION.
   - Outputs: P50/P80 dates for permit and CO, carrying cost P50/P80, contingency, a chart of
     which stage adds the most spread, and a side-by-side for the two cities.
   - The default carrying cost is $1,771/month: ASSUMPTION derived from the SYNTHETIC deal
     ($85k ÷ 48 months). It must be editable and labelled on screen.
4. **Tab B:**
   - Pick a city. Show its stage medians versus the OC peer best quartile.
   - Show its Table D permitting-related programs with Claude's classification:
     - category: ADU streamlining, pre-approved plans, permit-time review, objective standards,
       fees, process/CUP removal, other
     - status bucket: completed, ongoing, delayed, not started, unclear
     - overdue flag: target date before today and not completed
     - the source text beside each row
   - List peers that completed the same category.
5. A sources and caveats panel on both tabs, and a "prototype, not legal or financial advice"
   footer.

**Cut first, in this order (and label what's cut in the README):**
1. State Controller spending per permit (capacity proxy).
2. The LA and San Diego reference benchmarks for the submitted→issued stage.
3. The drafted request in Tab B: replace it with a static template.
4. Linking records across report years: use same-row pairs only and say so.
5. The Claude memo on Tab A.
6. If Claude classification fails or runs late, use keyword rules, labelled "keyword match, not
   reviewed".

**Never:**
- invent a timeline, fee, deadline or statute
- say a city "violates" a law
- say a program caused a speed-up (the data only shows association)
- show individual addresses

## How Claude is used inside the tool

| Use | Model | When | What a person checks |
|---|---|---|---|
| Classify Table D programs (category, status bucket, target date parsed) | Claude Haiku 5.5 (`claude-haiku-5-5`) | **Once at build time**, in a batch script. Keyword-filter first, about 20 rows per call, JSON out, results committed to `data/tableD_classified.csv`. The app reads the CSV and makes no live calls | Hand-check 20 random rows; record the accuracy in the README. The UI shows source text next to every label |
| Draft a request quoting the city's own program (not sent) | Haiku 5.5, live, cached | Tab B button | The user reads and edits it; the tool never sends anything |
| Optional 3-sentence memo from the Tab A comparison table | Haiku 5.5, live, cached | Tab A | Numbers must match the table shown beside it |

- The app must run with no API key: classifications come from the CSV, and the live features
  show "unavailable".
- Before running the batch, estimate its cost with the token-counting endpoint. Prompts must say
  "use only the text given; answer `unclear` if the status does not say."

## Plan (assumes the build starts around 11:00; shift everything if later)

| Time | Do | Done when |
|---|---|---|
| 11:00–11:25 | Skeleton, `requirements.txt`, `scripts/fetch_apr.py` for A2 and Table D (OC, paged, sleep between pages, drop address/notes columns) | CSVs committed; row counts match about 54k (A2) and about 1.8k for 2025 (D) |
| 11:25–12:05 | `analysis.py`: durations, summary table, Monte Carlo function | Tustin vs Santa Ana P50/P80 printed. **Commit + push** |
| 12:05–12:35 | `app.py` Tab A | Runs locally. **Commit + push**. Deploy to Streamlit Community Cloud now (lunch while it builds) |
| 12:35–1:05 | `scripts/classify_tableD.py` (Haiku batch) → CSV; hand-check 20 rows | CSV committed, accuracy noted |
| 1:05–1:30 | Tab B: peer comparison, program table, overdue flags, drafted request | **Demo freeze at 1:30.** Live URL works signed out |
| 1:30–2:00 | README from `templates/TEAM-README.md`: users, before/after, Try it, sources, real vs mocked, where it's wrong | On `main` |
| 2:00–2:15 | 30-second video: project manager picks a city (Tab A), then the overdue promise (Tab B) | MP4 ready |
| 2:15–2:30 | Repo public (check signed out). No keys (`git log -p \| grep -i sk-ant`). No personal info. Everything on `main`. Submit the form | Submitted |

## Stack

- **Streamlit (Python)**, one `app.py` using `st.tabs`. pandas and numpy for the Monte Carlo,
  plotly for the charts.
- **Deploy:** Streamlit Community Cloud from the public repo. Main file `app.py`. Put
  `ANTHROPIC_API_KEY` in the app's Secrets, never in git.
- **Pinned deps** (`requirements.txt`). These are known-good starting versions. Install them,
  then pin exactly what you tested with `pip freeze`. If the old `anthropic` pin rejects
  `claude-haiku-5-5`, upgrade the SDK and re-pin.
  ```
  streamlit==1.40.0
  pandas==2.2.3
  numpy==2.1.3
  plotly==5.24.1
  requests==2.32.3
  anthropic==0.39.0
  ```
- Python 3.11 or 3.12. `.env.example` holds only the line `ANTHROPIC_API_KEY=`.

## Phone control (Remote Control) vs credits

- Remote Control (driving the laptop session from the Claude phone app) needs Claude Code signed
  in with a claude.ai Pro, Max, Ultra, Team or Enterprise plan. **API keys are not supported.**
  Source: https://code.claude.com/docs/en/remote-control ("Requirements"), checked 2026-11-07.
- This plan runs Claude Code on the **event API credits**, so there is no Remote Control. Watch
  progress on GitHub (commits and `ITERATION_LOG.md`) instead. The loop stops on its own at
  `STOP_AT`, at the $ cap, or after 3 failed rounds.
- If you would rather steer from your phone and use the plan's usage instead of credits: sign
  in with `/login` using your claude.ai account and run
  `claude --remote-control "Permit Clock"`, then use `/loop 20m` in that session (it reads
  `.claude/loop.md`). That route has no per-round $ cap, so watch `/usage`.

## Datasets (all checked 2026-11-07)

| Dataset | URL / ID | Status today |
|---|---|---|
| HCD APR Table A2 (entitlement, permit, CO dates) | https://data.ca.gov/dataset/housing-element-annual-progress-report-apr-data-by-jurisdiction-and-year · resource `fe505d9b-8c36-42ba-ba30-08bc4f34e022` · `datastore_search` / `datastore_search_sql` | Works. 927,011 rows statewide. Filter `CNTY_NAME='Orange'`. The city field is `JURIS_NAME` |
| **HCD APR Table D (housing-element program implementation)** | same dataset, resource `37724925-2014-4646-ade8-3ba9f3ff9fb8` | Works. 147,691 rows statewide. 1,822 OC rows in 2025, 35 jurisdictions. Fields: `JURIS_NAME`, `YEAR`, `PROGRAM_NAME`, `PROGRAM_OBJECTIVE`, `ACCOMPLISHED_DT` (target), `PROGRAM_STATUS` (free text). Filter OC by the list of 34 city names plus `ORANGE COUNTY` (no county column) |
| HCD APR Table A (applications, `APP_SUBMIT_DT`) | resource `c78b769d-cc02-4050-91ef-79ded665b5a8` | Works. 358,228 rows. Stretch only |
| HCD Housing Element Compliance Report | resource `2dcd1cd4-1348-4fc5-9c9c-219f82daac00` | Works. OC 6th cycle: 33 In, 2 Out |
| HCD 6th-cycle RHNA progress | resource `1e80a9cf-724c-432d-8374-e9708a6a92dc` | Works. Context only |
| CA State Controller, City Expenditures (Planning; Construction and Engineering Regulation) | https://bythenumbers.sco.ca.gov Socrata `ju3w-4gxp` | Works. All 34 OC cities, FY2022–2025. Stretch (cut 1) |
| LA City LADBS permits submitted 2020–present | https://data.lacity.org Socrata `gwh9-jnip` (issued view `pi9x-tg5x`) | Works, updated 2026-11-02. `adu_changed` is text. Reference only, not OC (cut 2) |
| San Diego development permits | https://data.sandiego.gov/datasets/development-permits/ | CSV header read only. Reference only (cut 2) |
| BackyardADU.net build_times.csv (third party, cross-check) | https://backyardadu.net/data/build_times.csv | 200 OK. Cite the APR for anything official |
| Brief's 4-year baseline (ASSUMPTION) | `lanes/2-clear-it/data/timeline.json` | Rounded estimates |
| Synthetic deal ($85k time cost) | `lanes/3-fund-it/data/synthetic-example-deal.json` | SYNTHETIC. Never present it as real |

## Data and privacy

- **Table A2: drop** `STREET_ADDRESS`, `STD_ADDRESS`, `PROJECT_NAME`, `NOTES`, `LATITUDE` and
  `LONGITUDE` at fetch time. Keep city, year, unit category, tenure, unit counts, dates, the
  SB 35 flag, and APN or tracking ID for linking.
- **Table D:** keep program name, objective, target date and status. Program text describes city
  programs, not people. If a row looks like it names a private person, stop and tell an
  organizer.
- Show city-level aggregates only, and no addresses in the UI.
- Be kind to data.ca.gov: fetch once, cache the CSVs, commit them, page with `limit`/`offset`,
  and sleep 1 second between pages.

## Open questions

1. Same-day entitlement and permit in Anaheim and Fullerton: is it a ministerial path or a
   reporting habit? Ask a planner in the room.
2. Linking across report years: `JURS_TRACKING_ID` or `APN`? Test which gives more matches in
   Irvine and Huntington Beach.
3. How many OC Table D programs are actually about permit speed? Measure it in step 1 of the
   build. If it is under about 50, Tab B leans on peer benchmarks more than on promises.
4. Carrying cost per month: can someone in the room give a sourced figure? Until then the
   synthetic-derived ASSUMPTION stays.
5. Team: this plan assumes solo. A teammate could own the README, the video and the classifier
   hand-check.

## Ideas considered (scores 1–5: Impact / Works / Scale / Innovation / Portfolio)

| # | Idea | Lane | I | W | S | In | Port |
|---|---|---|---|---|---|---|---|
| A | **Schedule and contingency planner (Monte Carlo)**: picked, Tab A | 2→3 | 4 | 5 | 5 | 4 | 5 |
| B | **City promise tracker (Table D plus peer benchmark)**: picked, Tab B | 2 | 4 | 4 | 5 | 4 | 4 |
| C | Stalled-project radar (entitled 5+ projects that look stuck) | 2→1 | 4 | 2 | 4 | 5 | 4 |
| 2 | Rate-to-Gap sensitivity | 3 | 4 | 3 | 4 | 3 | 5 |
| 3 | Stale-site detector | 1 | 4 | 4 | 4 | 4 | 4 |
| 4 | Site shortlist ranker | 1 | 5 | 2 | 4 | 3 | 4 |
| 5 | Surplus-land cleaner | 1 | 3 | 4 | 3 | 2 | 3 |
| 7 | Funding-round timing planner | 3 | 4 | 1 | 3 | 4 | 3 |
| 8 | Stale-statute checker | 2 | 3 | 3 | 3 | 3 | 2 |

## Portfolio framing (one line)

*Business question:* how long does a small housing project really take to permit and build in
each Orange County city, what does the uncertainty cost, and are cities delivering on their own
plans to speed it up? *Finding:* stage times differ by months between cities. Several large cities
don't report the dates needed to measure them, and many permitting promises are past their target
dates. *Recommendation:* nonprofits should budget P80, not P50, and choose cities with the data in
hand. Advocates and city staff should use the city's own commitments to push the slowest stage
first.

## Starter prompt for Claude Code

The build prompt is `prompts/01-build.md` (paste it into `claude` for an attended build). The
unattended loop prompt is `.claude/loop.md`. Edits to either take effect on the next round.
