# Permit Clock: one build-or-improve round

You are running one round of an unattended loop while the owner is away. The script
`scripts/run_loop.sh` runs you, then runs `scripts/check.sh`, and pushes to `main` only if the
checks pass. If they fail, the script reverts your round. Nobody can answer questions, so make a
sensible choice inside the rules and write down what you chose. If a person is typing in this
session (an interactive `/loop`), their instructions come first.

## Start every round

1. Read `CLAUDE.md` (the event rules: they do not bend) and `NOTES.md` (the decision, scope and
   cut list).
2. Read `ITERATION_LOG.md`, or create it with a one-line header if it is missing. It holds what
   earlier rounds did and what they queued next.
3. If `.claude/last_failure.txt` exists, the previous round was reverted because the checks
   failed. Read it, do not repeat that change, then delete the file.
4. Run `git log --oneline -15` and `git status`.

## Pick ONE thing for this round, from the highest category that applies

- **A. Broken.** `bash scripts/check.sh` fails right now: fix only that.
- **B. Build not finished** (`.claude/BUILD_COMPLETE` does not exist): do the next unfinished
  step of `prompts/01-build.md`. One step per round; split a big step into parts. When steps 1
  to 6 all work, create `.claude/BUILD_COMPLETE` with one line listing what is in and what was
  cut.
- **C. Honesty and correctness.** Look for:
  - a number on screen without a source or an ASSUMPTION label
  - a cell with n below MIN_N that is not shown as "unknown"
  - wording that claims a program caused something, or that a city violated a law
  - an address, APN or project name in the UI
  - a statistic computed wrongly (prove it with a test, then fix it)
- **D. UX.** Run `python scripts/screenshot.py`, then Read the PNGs it lists in `.ux/`. Score
  them against `docs/ux-rubric.md` and fix the single worst failing item. Log the score before
  and after.
- **E. Function.** Look for:
  - an input that does nothing
  - a cached step slower than 3 seconds
  - an unhandled edge case: a city with no data, a unit type with n = 0, a start date in the
    past, every option set to "unknown"
- **F. Docs.** Make the README, the "real vs mocked" table and the sources table match what the
  app does now.
- **G. Nothing above.** Simplify: remove or shorten something that does not help the user
  decide.

## Rules for every round

- Make one small, focused change. Do not add features beyond the scope in `NOTES.md`. When in
  doubt, choose less.
- Keep the app runnable. Run `bash scripts/check.sh` before you finish. If it fails, fix your
  change or undo it.
- Commit with a clear message. **Do not push**: the script pushes after the checks pass. Never
  rewrite history.
- Never weaken, skip or delete a test or a check to make it pass. Do not edit
  `scripts/run_loop.sh`, `scripts/check.sh` or `.claude/settings.json`.
- Do not fetch from data.ca.gov again if the CSVs in `data/` already exist. Never request
  anything from a city website.
- Do not run `scripts/classify_tableD.py` again if `data/tableD_classified.csv` exists: it
  spends API credits. Live Claude calls in the app must sit behind a button and
  `st.cache_data`, never run on page load, and must not run when no API key is set.
- Never invent a number, fee, deadline, statute, address or parcel fact. Say "unknown". Label
  every assumption as ASSUMPTION. No personal information. Nothing that sends an email, a form or
  a message.
- Do not touch `.env`, `LICENSE`, `docs/` event files (other than `docs/ux-rubric.md`) or
  anything under `lanes/` (those are read-only sources).
- Add a dependency only if it is essential, and pin it in `requirements.txt`.

## End every round

Append to `ITERATION_LOG.md`:

```
### Round <n> · <HH:MM> · <one-line title>      (n = last round in ITERATION_LOG.md + 1)
- Category: <A-G>
- Found: <what was wrong, with evidence: screenshot file, test name, number>
- Changed: <files and what changed>
- Result: check.sh <pass/fail>; before -> after <measurable if possible: UX score, inputs before
  the first result, seconds to render, rows tested>
- Next: <top 1-3 candidates for the next round>
```

Then commit, with `ITERATION_LOG.md` included in the commit.
