# Permit Clock

> For a nonprofit project manager or city housing staff in Orange County: how long permitting
> will really take in a given city, what that delay costs, and which of the city's own
> permitting promises are past their target date. Built on the state's own housing reports.

**Prototype only. Not legal, financial or lending advice.** Ask a professional before you decide.

**Team:** [team name: to fill]
**Members:** [names: to fill]
**Lane:** 2 Clear it (with a bridge to Lane 3: time becomes gap dollars)
**Built at:** Claude Impact Lab: UCI × SoCal Affordable Housing, November 7, 2026

The event's own README (schedule, rules, lanes) is now in [EVENT-README.md](EVENT-README.md).

## The real user

The users below are made up, from `lanes/2-clear-it/scenarios.json`. They are not real people.

| | Before | After |
|---|---|---|
| **Nonprofit project manager** with a small project that could go in one of two OC cities | One rule of thumb (about 4 years, land to keys, from the brief) and phone calls | Likely (P50) and safe-to-plan (P80) move-in dates for City A vs City B, with sample size n, and a contingency in dollars to budget. "Unknown" where a city did not report enough |
| **City permit tech, housing staff or advocate** | Housing-element programs are buried in annual-report text; nobody tracks which permitting promises are overdue | The city's slowest stage vs the fastest quarter of OC cities, its permitting programs sorted by type and status with overdue ones flagged, peers that finished the same kind of program, and a drafted (never sent) request quoting the city's own promise |

## What we built

A Streamlit app with two tabs.

- **Plan my project.** Pick two cities, a unit type and an entitlement approval date. A Monte
  Carlo (5,000 draws) resamples real entitlement → permit → completion times from that city's
  reports. With the defaults (Tustin vs Santa Ana, all types) it says: "Budget **$16,100**
  contingency in Tustin. **Santa Ana** is about **22 months** faster than Tustin at P80" (start date 2026-11-07; the gap is the difference of the two move-in months shown). Santa
  Ana's figure uses stages drawn separately, which is an ASSUMPTION (see below). Move-in dates
  are the P50/P80 of whole simulated projects, so the P80 date is usually earlier than adding
  the two stage P80s in the table (few projects are slow at both stages); the app says so under
  the table.
- **City promise tracker.** Pick a city. For Tustin it says: "Slowest stage: Entitlement →
  permit, about 17 months behind the fastest quarter of OC cities. 29 permitting-related
  programs in its 2025 report; 14 are past their target date and not reported completed" (as of
  2026-11-07; the overdue count is checked against today's date). Where a target is not a single date,
  the headline counts those programs as "overdue: unknown" (Costa Mesa: 17 of 17) instead of
  implying none are late; a city with no permitting programs gets only an info box. Every
  program label sits next to the city's own status text. Program names on screen are the city's
  own words, shortened: leading words that every name in a city shares (e.g. Tustin's "6th HE
  Cycle") are left out; if that lead appears again inside a name (a heading such as "Goal 1: …"
  came first), the label starts after it; same-looking names add the start of their own objective. The data
  and the draft keep the full names.

**Demo video:** [to add]
**Live demo:** [to add, e.g. Streamlit Community Cloud]

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
- **Drafting a request (live, behind a button).** In Tab B, with an API key set, "Draft with
  Claude" writes a short polite note that quotes the city's own program text. It is labelled
  "Draft: review before use", cached, and **never sent**. With no key, the app shows a static
  template built only from the city's own row.

## Try it

```bash
git clone <this repo>
cd zero-gap
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Tested with Python 3.13. The app runs fully with **no API key**: the data and the program labels
are cached CSVs in `data/`. For the optional live draft, copy `.env.example` to `.env` and set
`ANTHROPIC_API_KEY` (or put it in Streamlit Secrets). Never commit a key.

Run the checks: `bash scripts/check.sh` (key scan, compile, `pytest`, app runs with no key).

## Sources and assumptions

| Item | Source or assumption | Date checked |
|---|---|---|
| Permit timelines | HCD Annual Progress Report **Table A2**, data.ca.gov resource `fe505d9b-8c36-42ba-ba30-08bc4f34e022`, filtered to `CNTY_NAME = 'Orange'`, 53,578 rows. Addresses, project names, notes and coordinates dropped | 2026-11-07 |
| Permitting programs | HCD Annual Progress Report **Table D**, data.ca.gov resource `37724925-2014-4646-ade8-3ba9f3ff9fb8`, filtered to the 34 OC cities plus Orange County, 8,623 rows (367 permitting-related 2025 rows classified) | 2026-11-07 |
| Program labels | Claude Haiku 5.5 reading the city's own text. Not hand-checked yet (accuracy unknown) | 2026-11-07 |
| City of Orange ADU permit → completion | BackyardADU.net reports 263 days; the APR data gives a different median. Both are shown in the app; we do not pick one | 2026-11-07 |
| Carrying cost $1,771/month | **ASSUMPTION**: $85,000 time cost ÷ 48 months from the SYNTHETIC deal in `lanes/3-fund-it/data/synthetic-example-deal.json`. Editable in the app. Replace with yours | 2026-11-07 |
| Minimum sample n = 30 | **ASSUMPTION**: below 30 records a cell shows "unknown" | 2026-11-07 |
| Stages drawn separately | **ASSUMPTION**: when fewer than 30 records hold both stages, the two stages are drawn independently, which ignores any link between them. The app labels every result that uses this | 2026-11-07 |
| OC best quartile | **ASSUMPTION**: 25th percentile of city medians (cities with n ≥ 30), excluding cities whose median is same-day (0 days), and "unknown" with fewer than 4 cities | 2026-11-07 |
| Same-day pattern (Anaheim, Fullerton) | **INFERRED**: most of their records show the entitlement date equal to the permit date. Probably a reporting pattern, not speed | 2026-11-07 |

Every number we made up is labelled ASSUMPTION here and in the tool.

## What is real and what is mocked

| Part | Status |
|---|---|
| OC permit timelines (Table A2, cached) | working, real data |
| P50/P80 dates, contingency, stage spread (Tab A) | working |
| Carrying cost per month | ASSUMPTION default from a synthetic deal; user-editable |
| City stage medians vs OC best quartile (Tab B) | working |
| Program type, status and target date (Tab B) | working; labels by Claude, not yet hand-checked |
| Overdue flag | working: target date before today and status not "completed"; "unknown" when there is no single target date |
| Peers that completed the same category | working (self-reported by cities) |
| Draft a request | working: static template with no key; Claude draft behind a button with a key. Never sent |
| Linking records across report years | counted only, not used: durations come from same-row date pairs |
| State Controller spending per permit; LA/San Diego benchmarks; Claude memo on Tab A | cut |

## Where it gets things wrong

- **Reporting, not reality.** Every figure is what cities reported to the state. Irvine reports
  very few entitlement dates, Costa Mesa few, and Huntington Beach reports no completion dates,
  so those cells show "unknown".
- **Same-day cities** (Anaheim, Fullerton) look fast from entitlement to permit because of how
  they report. When a picked city has 50% or more same-day entitlement → permit records
  (ASSUMPTION threshold) out of at least 30 (MIN_N; below that the share is "unknown"), the Tab A headline adds a caution; do not read those cities as fastest.
- **Thin cells.** Affordable-only projects are too few for benchmarks, so the app uses all
  projects of a unit type. Many city × unit-type cells are "unknown".
- **Separate draws.** Where few records hold both stages (Santa Ana: 6 for all types), the
  forecast assumes the stages are independent. The Tab A headline says so whenever a picked
  city has fewer than 30 (MIN_N) records with both stages. Treat those results as rough.
- **Program labels** come from Claude reading short status text. Accuracy is unknown until the
  hand-check is done. A keyword fallback exists but agreed with Claude on only 47% of
  categories, so it is weak.
- **Association, not cause.** A city finishing a program and having faster permits does not mean
  the program caused it. The app never says a city broke a law.

## Next steps

- Hand-check the 20 rows in `data/tableD_handcheck.csv` and publish the accuracy.
- Ask two or three OC nonprofits to test Tab A on a live project, and one city housing team to
  check Tab B against what they know.
- Scale: the same state tables cover every California jurisdiction, so the next 100 projects
  outside OC need a different filter, not a new data source.

## Data and privacy

This project uses only public data from data.ca.gov. Addresses, project names, notes and
coordinates are dropped when the data is fetched, and APNs are used only to link records, never
shown. It contains no personal information about real tenants, buyers or residents. It does not
file applications or contact any city or person.

## License

MIT, see [LICENSE](LICENSE).
