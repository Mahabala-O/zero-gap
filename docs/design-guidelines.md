# Permit Clock design guidelines

The look and voice of the product. Every screen, chart and sentence follows these. The model is
Stripe's dashboard and documentation: calm, precise, generous whitespace, one accent color, type
that does the work, nothing decorative. `ui.py` implements the tokens below; use its helpers
instead of writing styles inline.

## 1. Principles

1. **Answer, then evidence, then detail.** Each page opens with what the user came for, in one
   sentence they can repeat. Charts and tables support the sentence. Methods and caveats are one
   click away, never in the headline.
2. **One accent.** Purple marks the thing the user chose or should look at. Everything else is
   navy text on white, with grey for context. Status colors (green, amber, red) are reserved for
   status and never used for decoration.
3. **Plain words.** No statistics jargon on screen (no P50/P80, percentile, median in body
   text). Say "likely", "plan for", "typical". Explain a term once, in a tooltip, at first use.
4. **Honest by design.** Every number carries its unit and its sample size. Missing data says
   "Not enough reported data" in the same place a number would be, never a blank. Assumptions are
   labelled where they apply. Uncertain labels look uncertain (grey, "unverified").
5. **Skimmable.** A reader should get the page from headings, eyebrow labels and bold leads
   alone. Group repeated things; show counts on groups; order by what matters most.
6. **Consistent spacing.** Everything sits on an 8-px grid. Same card padding everywhere, same
   gap between sections, same caption style under every chart.

## 2. Tokens

| Token | Value | Use |
|---|---|---|
| `text` | `#0A2540` | Headings, body, numbers |
| `text-2` | `#425466` | Secondary text, descriptions |
| `muted` | `#697386` | Captions, eyebrow labels, axis text |
| `border` | `#E3E8EE` | Card borders, dividers, chart gridlines |
| `surface` | `#F6F9FC` | Sidebar, subtle backgrounds |
| `accent` | `#635BFF` | The chosen item, primary controls, links |
| `accent-soft` | `#E0DEFF` | Accent backgrounds (selected rows, plan-for bar) |
| `grey-bar` | `#CFD7DF` | Non-highlighted chart bars |
| `success` | `#228403` on `#D7F7C2` | Done, at or ahead |
| `warning` | `#BB5504` on `#FCEDB9` | Due later, caution |
| `danger` | `#CD3D64` on `#FFE7F2` | Overdue, behind |
| `neutral` | `#545969` on `#EBEEF1` | Unknown, recurring, unverified |
| `series` | `#635BFF`, `#0A2540`, `#00A3BF` | Up to three compared items, in order, same everywhere |

Spacing scale: 4, 8, 12, 16, 24, 32, 48, 64 px. Radius: 8 px cards, 6 px controls. Cards have a
1-px `border` and no shadow. No gradients, no icons except the status dot, no emoji.

## 3. Type

System stack (`-apple-system, "Segoe UI", Inter, Roboto, "Helvetica Neue", Arial`), so no
font download on load.

| Role | Size / weight | Notes |
|---|---|---|
| Page title (h1) | 28 / 600 | One per page. Letter-spacing −0.01em |
| Section (h2) | 20 / 600 | 32 px above, 8 px below |
| Card title (h3) | 16 / 600 | |
| Eyebrow | 12 / 600, uppercase, +0.04em, `muted` | Labels above numbers and lists |
| Big number | 28 / 600, tabular figures | Stat tiles |
| Body | 15 / 400, line-height 1.5 | |
| Caption | 13 / 400, `muted` | Under charts, sources, notes |

## 4. Components

- **Page header**: h1 question, then one lead sentence in `text-2` saying what the page shows
  and from what data. Nothing else above the first result.
- **Stat tile**: eyebrow label, big number, one-line delta or note below in a status color or
  `muted`. Tiles sit in a row of equal columns; three per row on desktop. Missing data shows
  "Not enough reported data" as the value, in `muted`.
- **Card**: bordered container, 16-px padding, title row (name + muted count), content rows.
  One card per entity, full width, never stacked in two columns on desktop.
- **Row**: status dot, the item in body text, then metadata in a muted 13-px run separated by
  "·". Done or inactive rows are `muted` throughout.
- **Status dot and pill**: dot for rows; pill (colored text on soft background) for a single
  headline status. Colors only from the status set.
- **Filter**: a horizontal radio with counts ("Overdue (14)"). At most one filter row per list.
- **Chart**: Plotly, transparent background, `border`-colored horizontal gridlines only, no
  zero line, axis titles in `muted` 12 px, legend top-left horizontal or none. Highlighted
  items in `series` colors, everything else `grey-bar`. Every chart has a one-line caption that
  states what solid and faded mean and the data range. No chart titles inside the plot; use the
  section heading.
- **Expander**: "How we got this" and "Sources and method" only. Never hide a primary result.
- **Disclaimer**: one caption at the bottom of each page: "Prototype. Not legal, financial or
  lending advice."

## 5. Voice

- Sentence case everywhere, including buttons and headings.
- Talk to one person: "your shortlist", "pick a city".
- Verbs over nouns: "Ask the city about it", not "Request drafting".
- Numbers: months to the nearest half ("8.5 months"), dollars to the nearest hundred
  ("$24,700"), dates as "Aug 2027", counts as "14 of 29".
- State the source and date inline when a number comes from outside the dataset
  ("prime rate 7.00%, FRED, 2026-10-27").
- When unsure, say so in the user's words: "not enough reported data", "no single target
  date", "unverified label".

## 6. Page templates

**Landing: a city's promises.** Header → three stat tiles → promise cards (filter row above) →
"Look closer" picker with the city's own words → draft request → sources expander.

**Evidence: timing after approval.** Header (what it measures and what it does not) → controls
(unit type, affordability, date) → ranked chart including unknown rows → shortlist verdict →
timeline → per-city tiles with "How we got this" → sources expander.

## 7. Checklist before merging a UI change

- [ ] First screen states the answer or the question and shows a real result with defaults.
- [ ] No P50/P80/percentile/median in body text; terms explained once.
- [ ] Every number has a unit; every benchmark shows n; missing data says so in place.
- [ ] Colors only from the tokens; accent used for one thing per view.
- [ ] Cards full width, same padding; sections 32 px apart; captions under every chart.
- [ ] Phone (390 px): no horizontal scroll, headline visible in the first screen.
- [ ] Sources and method expander present; disclaimer present once.
