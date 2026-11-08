# Permit Clock

> For a nonprofit project manager or city housing staff in Orange County: how long permitting
> will really take in a given city, what that delay costs, and which of the city's own
> permitting promises are past their target date. Built on the state's own housing reports.

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://permit-clock.streamlit.app/)

**Prototype only. Not legal, financial or lending advice.** Ask a professional before you decide.

**Team:** seeeverything
**Members:** Mikhail Orlov
**Lane:** 2 Clear it (with a bridge to Lane 3: time becomes gap dollars)
**Built at:** Claude Impact Lab: UCI × SoCal Affordable Housing, November 7, 2026

The event's own README (schedule, rules, lanes) is now in [EVENT-README.md](EVENT-README.md).

## The real user

The users below are made up, from `lanes/2-clear-it/scenarios.json`. They are not real people.

| | Before | After |
|---|---|---|
| **Nonprofit project manager** with a small project that could go in one of two OC cities | One rule of thumb (about 4 years, land to keys, from the brief) and phone calls | Every OC city ranked by time from planning approval to move-in, a calendar timeline for a shortlist of up to three, a **likely** and a **plan-for** move-in date for each, and what the wait costs in dollars using the manager's own carrying-cost inputs. "Not enough reported data" where a city did not report enough |
| **City permit tech, housing staff or advocate** | Housing-element programs are buried in annual-report text; nobody tracks which permitting promises are overdue | Three tiles (each stage against the fastest quarter of OC cities; promises overdue), where the city sits in the county ranking, its permitting promises as cards filtered by status and type, each showing the city's own words, peers that finished the same kind of program, and a drafted (never sent) request |

## What we built

A Streamlit app with two pages, picked in the sidebar. Every number comes from the state's
Annual Progress Report tables; the app makes no network calls on page load.

**Where should I build?**

- Inputs: unit type, planning approval date, up to three cities to compare, and a
  carrying-cost calculator (see below).
- A ranked bar chart of every Orange County city with enough data: solid bar = **likely**
  (half of past projects were done by then), faded bar = **plan for** (8 in 10 were). Switch
  between the whole path and either stage. Cities with fewer than 30 usable records are listed
  under the chart as "not enough reported data" instead of being drawn.
- A calendar timeline for the shortlist (approval → permit → move-in, then the plan-for
  extension) and a one-paragraph verdict in plain words, e.g. with the defaults: "In **Santa
  Ana**, people would likely move in by **Aug 2027**; plan for **May 2028** to be safe.
  **Tustin**: likely May 2029, plan for Mar 2030, about **21 months longer**." The money line
  follows on its own: cost of the likely wait, contingency to the plan-for date, and how much
  more the slower city costs.
- Tiles per city (likely, plan for, cost of waiting, contingency), then a **How we got this**
  expander holding every caveat for that city: sample sizes, stages drawn separately
  (ASSUMPTION), the same-day reporting caution (INFERRED), stages below the minimum sample.
  Caveats live there, next to the numbers, instead of in the headline.
- "Is it getting faster?": median months by report year for all of OC and the chosen cities,
  with a gap in a city's line where it reported fewer than 30 projects that year.

**How is my city doing?**

- Three tiles: approval → permit and permit → move-in against the fastest quarter of OC cities
  ("+17 months vs fastest quarter" for Tustin; "Same day" for cities with the same-day
  reporting pattern; "Not enough reported data" below the minimum sample), and permitting
  promises overdue ("14 of 29" for Tustin as of 2026-11-08, checked against today's date).
- The county ranking chart with the city highlighted.
- Its permitting promises as a skimmable list grouped by program (Tustin's 29 rows become 11
  programs), most overdue first: a header per program with its counts, then one line per
  promise with a status dot, the promise in the city's own objective text, the target month
  and the status the city reported. Done items are greyed. Filter by status. Labels come from
  Claude Haiku and are not hand-checked, so "Look closer at one" opens the full objective, the
  city's reported status and the full program name for any promise.
- Other OC cities that report finishing the same kind of promise, and a drafted request about
  the promise picked above (template, or Claude with a key). Never sent.

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
**Where should I build?** loads with a result already showing (Tustin vs Santa Ana); pick
**How is my city doing?** in the sidebar for the other page. To stop the app, press `Ctrl+C`
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
| Program labels | Claude Haiku 5.5 reading the city's own text. Not hand-checked yet (accuracy unknown) | 2026-11-07 |
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
| Likely and plan-for move-in dates, county ranking, timeline, year trend | working |
| Carrying cost per month | working calculator; sourced rates, example dollar amounts (ASSUMPTION), user-editable |
| City stage medians vs OC fastest quarter (city page) | working |
| Program type, status and target date (city page) | working; labels by Claude, not yet hand-checked; the city's own words shown on every card |
| Overdue flag | working: target date before today and status not "completed"; "No single target date" when the target is not a date |
| Peers that completed the same category | working (self-reported by cities) |
| Draft a request | working: static template with no key; Claude draft behind a button with a key. Never sent |
| Linking records across report years | counted only, not used: durations come from same-row date pairs |
| State Controller spending per permit; LA/San Diego benchmarks; Claude memo | cut |

## Where it gets things wrong

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
- **Program labels** come from Claude reading short status text. Accuracy is unknown until the
  hand-check is done. A keyword fallback exists but agreed with Claude on only 47% of
  categories, so it is weak.
- **The cost calculator is arithmetic, not a pro forma.** It ignores loan draw schedules, the
  welfare exemption from property tax, and income earned while holding a building. Sourced
  rates are statewide or national, not Orange County.
- **Association, not cause.** A city finishing a program and having faster permits does not mean
  the program caused it. The app never says a city broke a law.

## Next steps

- Hand-check the 20 rows in `data/tableD_handcheck.csv` and publish the accuracy.
- Ask two or three OC nonprofits to test "Where should I build?" on a live project, and one city housing team to
  check "How is my city doing?" against what they know.
- Scale: the same state tables cover every California jurisdiction, so the next 100 projects
  outside OC need a different filter, not a new data source.

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
