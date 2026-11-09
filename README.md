# Permit Clock

> What did your city promise about permitting, and is it keeping those promises? Every Orange
> County city's permitting-related housing element programs, read from its own annual report
> to the state, with overdue ones flagged and the city's own words beside each. Plus the
> evidence page: how long permits really take after approval, city by city.

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://permit-clock.streamlit.app/)

**Prototype only. Not legal, financial or lending advice.** Ask a professional before you decide.

**Team:** seeeverything
**Members:** Mikhail Orlov
**Lane:** 2 Clear it (with a bridge to Lane 3: time becomes gap dollars)
**Built at:** Claude Impact Lab: UCI × SoCal Affordable Housing, November 7, 2026

The event's own README (schedule, rules, lanes) is now in [EVENT-README.md](EVENT-README.md).

## The real user

The scenarios in `lanes/2-clear-it/scenarios.json` are made up; nobody below is a real person.

| | Before | After |
|---|---|---|
| **Housing advocate, journalist or housing-element consultant** preparing public comment or a story on a city's housing element | Reads the city's annual progress report PDF and tallies promises and their status by hand; no view across cities | Opens the city: "10 of 29 promises overdue", each promise grouped under its program with the target date the city itself set, its reported status and its own words; which OC cities finished the same kind of program; a drafted (never sent) question to the city |
| **City housing staff or council member** before the next annual report or hearing | The same PDF, and no benchmark | The same list, plus one sentence on where the city's permit times sit against the fastest quarter of OC cities |
| **Nonprofit finance lead or lender** who needs a defensible schedule assumption | A rule of thumb (about four years, land to keys) | The evidence page: OC cities ranked on reported time from approval to move-in, a likely and a plan-for date, the extra cost of the slower city and the contingency to the plan-for date at the user's own carrying cost, a deadline-at-risk check, and a deed-restricted-only filter that mostly says "not enough reported data", honestly |

## What we built

A Streamlit app with two pages, picked in the sidebar. Every number comes from the state's
Annual Progress Report tables; the app makes no network calls on page load. The look follows
[docs/design-guidelines.md](docs/design-guidelines.md) (one accent, cards, plain words) and is
implemented once in `ui.py`.

**What did my city promise?** (landing page)

- Three tiles: promises overdue ("10 of 29" for Tustin on 2026-11-08, checked against today's
  date), recurring or undated, and reported done.
- One sentence on the city's permit times against the fastest quarter of OC cities.
- The promises as one full-width card per program (Tustin's 29 rows become 11 programs), most
  overdue first: a header with counts, then one line per promise with a status dot, the promise
  in the city's own objective wording, its target and the status the city reported. Done rows
  are muted. Filter by status.
- **Target dates** come from the city's own wording where it gives one ("no later than October
  2024" → Oct 2024). Otherwise the report's date field is used when it is a specific date; a
  date in 2029 or later (the end of the housing-element cycle) or the report year's December 31
  is not treated as a promise (ASSUMPTION) and shows "no single target date". Objectives that
  describe a repeating activity ("annually", "per year", "ongoing", "continue to") are
  **recurring** and never marked overdue. This cut Tustin's overdue count from 14 to 10 and
  the county's from 93 to 82.
- Status and type labels were read by Claude Haiku and are **unverified**: the page says so
  until `data/tableD_handcheck.csv` is filled in, then prints the measured accuracy. "Look
  closer at one" shows the full objective, the city's reported status, the full program name
  and the report date field for any promise, and the drafted request below is about that
  promise.

**After approval, how long to move-in?** (evidence page)

- The lead sentence says what is measured (planning approval → building permit → move-in) and
  what is not (rezoning and the entitlement process, often the longest part).
- Every OC city ranked: solid bar = **likely** (half of past projects done by then), faded bar
  = **plan for** (8 in 10). Cities below the 30-record minimum appear as labelled rows without
  a bar ("not enough reported data (n=12)") so Irvine reads as unknown, not fast.
- Filters: unit type, and **all projects / deed-restricted affordable only** (the BP_*_DR
  columns). Only 517 of 53,578 OC rows carry deed-restricted units, so the affordable filter
  mostly says "not enough reported data"; that is the honest answer, and the all-projects
  figures are dominated by ADUs and single-family homes.
- A shortlist of up to three cities: a calendar timeline, a verdict in plain words ("In **Santa
  Ana**, people would likely move in by **Aug 2027**; plan for **May 2028** to be safe.
  **Tustin**: likely May 2029, plan for Mar 2030, about **21 months longer**."), and per-city
  cards with the likely and plan-for dates, the **contingency** to the plan-for date, the
  **extra wait** versus the fastest city on the list, and an optional **deadline at risk**
  check (red when even the likely date misses it). Costs are differences, never the whole
  carrying cost of a project. Every card has a "How we got this" expander with its caveats:
  sample sizes, stages drawn separately (ASSUMPTION), same-day reporting (INFERRED), and the
  same-row-pairs bias toward faster projects.
- "Go deeper": median months by report year, in an expander.

**What a month of waiting costs** (sidebar calculator)

Carrying cost per month = loan balance × interest rate ÷ 12 + assessed value × property tax
rate ÷ 12 + construction not yet built × cost escalation ÷ 12 + insurance, staff and other.
The **rates are sourced** (prime rate 7.00%, FRED series DPRIME, 2026-10-27; property tax 1.1%,
Prop 13's 1% plus about 0.1% voter-approved debt, Legislative Analyst's Office; construction
cost +5.5% a year, Turner Building Cost Index Q3 2026, national). The **dollar amounts default
to the made-up one-home example** in `lanes/3-fund-it/data/synthetic-example-deal.json`
($360,000 acquisition, $40,000 construction; ASSUMPTION) and the user replaces them. Insurance
and staff have no public source and start at $0. With the defaults it comes to about $2,600 a
month. Untick "Show costs in dollars" to see months and dates only.

**Demo video:** uploaded with the submission form on the event hub
**Live demo:** https://permit-clock.streamlit.app/ (free hosting; if it has been idle it can take up to a minute to wake up). It also runs locally (see Try it)

## How Claude is used

- **Built with Claude Code**, in an attended start and then an unattended loop: one small change
  per round, `scripts/check.sh` must pass before anything is pushed. Every round is logged in
  [ITERATION_LOG.md](ITERATION_LOG.md).
- **Classifying programs (once, at build time).** `scripts/classify_tableD.py` sent 367
  keyword-filtered 2025 OC Table D rows to Claude Haiku 5.5 (`claude-haiku-5-5`) in batches of 20
  (estimated cost $0.022, printed before sending). It labels category, status and target date,
  using only the text given. The result is committed in `data/tableD_classified.csv`; the app
  makes no live call for this. **A person checks:** `data/tableD_handcheck.csv` holds 20 random
  rows for hand-checking. Accuracy: **unknown** until someone fills in the `correct?` column.
- **Drafting a request (live, behind a button).** On the city page, with an API key set, "Draft with
  Claude" writes a short polite note that quotes the city's own program text. It is labelled
  "Draft: review before use", cached, and **never sent**. With no key, the app shows a static
  template built only from the city's own row.

## Try it

Runs on a laptop in about two minutes. **No API key is needed**: the data and the program
labels are cached CSVs in `data/`.

**You need:** Python 3.11 or newer (tested with 3.13) and git. Check them with
`python3 --version` and `git --version`.

**1. Get the code**

```bash
git clone https://github.com/Mahabala-O/zero-gap
cd zero-gap
```

**2. Make a virtual environment and install the pinned packages** (one time)

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows (PowerShell):

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**3. Start the app**

```bash
streamlit run app.py
```

Your browser opens at <http://localhost:8501>. If it does not, open that address yourself.
**What did my city promise?** loads with Tustin already showing; pick **After approval, how
long to move-in?** in the sidebar for the evidence page. To stop the app, press `Ctrl+C`
in the terminal.

**Next time:** `cd zero-gap`, activate the environment again (`source .venv/bin/activate`, or
`.venv\Scripts\Activate.ps1` on Windows), then `streamlit run app.py`.

**Optional, the live Claude draft on the city page:** copy `.env.example` to `.env` and put your key
after `ANTHROPIC_API_KEY=`. Without a key, the button shows a template instead. Never commit
`.env`.

**If something goes wrong**

| You see | Do this |
|---|---|
| `streamlit: command not found` | The environment is not active. Run the activate command from step 2, then try again |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` with the environment active |
| `Port 8501 is already in use` | Another copy is running. Stop it, or run `streamlit run app.py --server.port 8502` |
| Windows blocks `Activate.ps1` | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then activate again |

**Run the checks** (key scan, compile, tests, app runs with no key): `bash scripts/check.sh`.
The tests need `pip install -r requirements-dev.txt` first.

## Sources and assumptions

| Item | Source or assumption | Date checked |
|---|---|---|
| Permit timelines | HCD Annual Progress Report **Table A2**, data.ca.gov resource `fe505d9b-8c36-42ba-ba30-08bc4f34e022`, filtered to `CNTY_NAME = 'Orange'`, 53,578 rows. Addresses, project names, notes and coordinates dropped | 2026-11-07 |
| Permitting programs | HCD Annual Progress Report **Table D**, data.ca.gov resource `37724925-2014-4646-ade8-3ba9f3ff9fb8`, filtered to the 34 OC cities plus Orange County, 8,623 rows (367 permitting-related 2025 rows classified) | 2026-11-07 |
| Program labels | Claude Haiku 5.5 reading the city's own text. Not hand-checked yet (accuracy unknown); the app says "unverified" until `data/tableD_handcheck.csv` is filled | 2026-11-07 |
| Target dates and "recurring" | City's own objective wording first; report date field as fallback. **ASSUMPTION**: a date in 2029 or later is the cycle end and the report year's Dec 31 a report date, not a promise; repeating-activity wording means no single deadline | 2026-11-08 |
| Deed-restricted filter | Rows with units in the APR's BP_*_DR columns (very-low, low, moderate; deed-restricted). 517 of 53,578 OC rows | 2026-11-08 |
| City of Orange ADU permit → completion | BackyardADU.net reports 263 days; the APR data gives a different median. Both are shown in the app; we do not pick one | 2026-11-07 |
| Interest rate 7.00% | Bank prime loan rate, Federal Reserve H.15 via FRED `DPRIME`, observation 2026-10-27, https://fred.stlouisfed.org/series/DPRIME. A nonprofit's loan may price differently; editable | 2026-11-08 |
| Property tax 1.1% | Prop 13 limit of 1% of assessed value plus about 0.1% voter-approved debt rates, Legislative Analyst's Office, https://lao.ca.gov/reports/2012/tax/property-tax-primer-112912.aspx. Local rates differ; editable | 2026-11-08 |
| Construction cost +5.5%/yr | Turner Building Cost Index Q3 2026 (1575) against Q3 2025 (1493), https://turnerconstruction.com/uploads/cost-index-Q3-2026.pdf. National, not OC; editable | 2026-11-08 |
| Loan balance $360,000, assessed value $360,000, construction $40,000 | **ASSUMPTION**: the SYNTHETIC deal in `lanes/3-fund-it/data/synthetic-example-deal.json`. Not a real project; replace with yours | 2026-11-08 |
| Insurance, staff, other $0/month | **Unknown**: no public source. The user enters theirs | 2026-11-08 |
| Minimum sample n = 30 | **ASSUMPTION**: below 30 records a cell shows "unknown" | 2026-11-07 |
| Stages drawn separately | **ASSUMPTION**: when fewer than 30 records hold both stages, the two stages are drawn independently, which ignores any link between them. The app labels every result that uses this | 2026-11-07 |
| OC best quartile | **ASSUMPTION**: 25th percentile of city medians (cities with n ≥ 30), excluding cities whose median is same-day (0 days), and "unknown" with fewer than 4 cities | 2026-11-07 |
| Same-day pattern (Anaheim, Fullerton) | **INFERRED**: most of their records show the entitlement date equal to the permit date. Probably a reporting pattern, not speed | 2026-11-07 |

Every number we made up is labelled ASSUMPTION here and in the tool.

## What is real and what is mocked

| Part | Status |
|---|---|
| OC permit timelines (Table A2, cached) | working, real data |
| Likely and plan-for move-in dates, county ranking (unknown cities listed), timeline, deadline check, year trend | working |
| Carrying cost per month | working calculator; sourced rates, example dollar amounts (ASSUMPTION), user-editable. Shown only as differences (contingency, extra wait vs the fastest city) |
| City stage medians vs OC fastest quarter (city page) | working |
| Program type, status and target date (city page) | working; labels by Claude, not yet hand-checked; the city's own words shown on every card |
| Overdue flag | working: target (city wording, else specific report date) before today and status not "completed"; recurring activities never flagged; cycle-end dates are "no single target date" |
| Peers that completed the same category | working (self-reported by cities) |
| Draft a request | working: static template with no key; Claude draft behind a button with a key. Never sent |
| Linking records across report years | counted only, not used: durations come from same-row date pairs |
| State Controller spending per permit; LA/San Diego benchmarks; Claude memo | cut |

## Where it gets things wrong

- **Mostly not affordable projects.** Only 517 of 53,578 OC rows carry deed-restricted units,
  and deed-restricted projects take far longer (median approval → permit 325 days against 37
  overall). The all-projects rankings describe ADUs and single-family homes; the affordable
  filter is honest and mostly empty.
- **Leans toward faster projects.** Durations use same-row date pairs, so a project that took
  several report years to permit can be missed. The app says so under every city.
- **Reporting, not reality.** Every figure is what cities reported to the state. Irvine reports
  very few entitlement dates, Costa Mesa few, and Huntington Beach reports no completion dates,
  so those cells show "not enough reported data".
- **Same-day cities** (Anaheim, Fullerton) look fast from entitlement to permit because of how
  they report. When a picked city has 50% or more same-day entitlement → permit records
  (ASSUMPTION threshold) out of at least 30 (MIN_N; below that the share is unknown), its "How we got this" notes carry a caution and the city tile says "Same day"; do not read those cities as fastest.
- **Thin cells.** Affordable-only projects are too few for benchmarks, so the app uses all
  projects of a unit type. Many city × unit-type cells are "not enough reported data".
- **Separate draws.** Where few records hold both stages (Santa Ana: 6 for all types), the
  forecast assumes the stages are independent. Such cities carry a * in the ranking, the
  verdict calls their figures rough, and "How we got this" says why. Treat them as rough.
- **Program labels** come from Claude reading short status text and are shown as unverified. Accuracy is unknown until the
  hand-check is done. A keyword fallback exists but agreed with Claude on only 47% of
  categories, so it is weak.
- **The cost calculator is arithmetic, not a pro forma.** It ignores loan draw schedules, the
  welfare exemption from property tax, and income earned while holding a building. Sourced
  rates are statewide or national, not Orange County.
- **Association, not cause.** A city finishing a program and having faster permits does not mean
  the program caused it. The app never says a city broke a law.

## Next steps

- Hand-check the 20 rows in `data/tableD_handcheck.csv`; the app will print the accuracy.
- Expand Table D beyond Orange County and across report years (the same state table covers
  every California jurisdiction) to show how each city's promises drift year to year. This is
  the believable scale story.
- Ask two OC housing advocates and one city housing team to use the promise page on a real
  annual report and tell us where a flag is wrong.
- Link A2 records across report years (APN or tracking ID) so slow projects are not missed.

## Data and privacy

This project uses only public data from data.ca.gov. Addresses, project names, notes and
coordinates are dropped when the data is fetched, and APNs are used only to link records, never
shown. It contains no personal information about real tenants, buyers or residents. It does not
file applications or contact any city or person.

Pre-submission scan (2026-11-07, 13:08): full git history searched for API-key patterns
(`sk-ant-`, AWS, GitHub tokens): none found; `.env` is not tracked. Tracked files outside
`lanes/` and `docs/` searched for email addresses and phone numbers: the only hit is a city
ride-share program's public toll-free number quoted inside the state's Table D text (not a
person).

## License

MIT, see [LICENSE](LICENSE).
