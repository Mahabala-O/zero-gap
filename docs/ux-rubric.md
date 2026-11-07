# UX rubric: minimalist, function first

Used by every improvement round (see `.claude/loop.md`). Score each item pass or fail from the
screenshots in `.ux/`, desktop 1280×800 and phone 390×844. Log the score, for example "9/13",
in `ITERATION_LOG.md` so the change over the day is measurable.

The test behind every item: **does this help the user decide, faster?** If not, remove it.

| # | Check | Pass when |
|---|---|---|
| 1 | Answer first | Each tab shows a real result with sensible defaults on first load, with no empty "pick something" state. The headline sentence is visible without scrolling at 1280×800 |
| 2 | Few inputs | At most 4 inputs are visible before the first result. Advanced inputs (carrying cost, MIN_N, year range) sit in an expander |
| 3 | One message per tab | One plain sentence answers the user's question, e.g. "City B is about N months faster at P80. Budget $X contingency." |
| 4 | Numbers readable | Every number carries its unit (months, $). Months are rounded to 0.5 and dollars to the nearest $100. Every benchmark shows its n beside it |
| 5 | Plain language | No unexplained jargon. "Entitlement", "certificate of occupancy (CO)", "P50/P80" and "same-day" each get a short help tooltip or caption on first use |
| 6 | Honesty visible | ASSUMPTION tags sit right next to the numbers they affect. "Unknown" looks the same everywhere. Sources and caveats are one click away on every tab |
| 7 | Charts earn their place | At most one chart per question, with labelled axes and units. City A and City B keep the same colors throughout. No decorative charts |
| 8 | Phone works | At 390 px wide there is no horizontal scroll, and the headline sentence is visible within the first screen |
| 9 | No dead ends | Empty or "unknown" states say why and what to try instead, e.g. "Irvine reports too few entitlement dates. Try permit → CO" |
| 10 | Fast | After the first load, a change of input re-renders in under about 3 seconds. Data and the Monte Carlo are cached |
| 11 | Ends in an action | Tab A ends with the contingency figure and the city recommendation. Tab B ends with the overdue list and a drafted, unsent request the user can copy |
| 12 | No clutter | No logos, emojis, long intros (2 lines at most), duplicate tables, or debug output |
| 13 | Disclaimer present, small | "Prototype. Not legal, financial or lending advice." appears once per page, unobtrusive |

When two fixes compete, choose the one that shortens the path from opening the page to the
answer.
