#!/usr/bin/env bash
# Unattended build-and-improve loop for Permit Clock (hackathon tooling, not part of the app).
#
# Each round runs `claude -p` with a fresh context and a dollar cap, using .claude/loop.md as
# the prompt. Then it runs scripts/check.sh. If the checks pass, it pushes to main. If they
# fail, it resets to the last good commit, so main always holds a working version.
#
# Usage (from the repo root, on main, with a clean working tree):
#   bash scripts/run_loop.sh
#   STOP_AT=1330 MAX_TOTAL_USD=40 bash scripts/run_loop.sh       # override defaults
# Stop early:  touch STOP   (checked between rounds; delete it before the next run)
# Watch:       tail -f logs/loop.log   or the commits on GitHub
set -u
cd "$(dirname "$0")/.."

STOP_AT="${STOP_AT:-1330}"                 # local time HHMM: no new round starts after this
HARD_STOP="${HARD_STOP:-1420}"             # never push after 14:20 (submissions are due 14:30)
MAX_TOTAL_USD="${MAX_TOTAL_USD:-40}"       # cap on this script's Claude Code spend (our choice)
BUILD_ROUND_USD="${BUILD_ROUND_USD:-8}"    # per-round cap while the build is unfinished
IMPROVE_ROUND_USD="${IMPROVE_ROUND_USD:-3}" # per-round cap afterwards
MODEL="${MODEL:-sonnet}"
PERMISSION_MODE="${PERMISSION_MODE:-auto}" # if auto is unavailable for you: PERMISSION_MODE=acceptEdits
PAUSE_SECONDS="${PAUSE_SECONDS:-30}"
MAX_FAILS=3
PY="${PYTHON:-python3}"

mkdir -p logs
LOG=logs/loop.log
log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG"; }
now() { echo $((10#$(date +%H%M))); }
add() { "$PY" -c "import sys; print(round(float(sys.argv[1]) + float(sys.argv[2]), 4))" "$1" "$2"; }
lt()  { "$PY" -c "import sys; sys.exit(0 if float(sys.argv[1]) < float(sys.argv[2]) else 1)" "$1" "$2"; }
cost_of() { "$PY" -c "
import json, sys
try:
    print(float(json.load(open(sys.argv[1])).get('total_cost_usd', sys.argv[2])))
except Exception:
    print(sys.argv[2])" "$1" "$2"; }   # unknown cost counts as the full round budget

push_main() {
  for wait in 2 4 8 16; do
    git push origin main >>"$LOG" 2>&1 && return 0
    log "push failed, retrying in ${wait}s"; sleep "$wait"
  done
  return 1
}

# ---- preflight -------------------------------------------------------------------------
command -v claude >/dev/null || { echo "claude CLI not found. Install Claude Code first."; exit 1; }
[ "$(git rev-parse --abbrev-ref HEAD)" = "main" ] || { echo "Switch to main first: git checkout main"; exit 1; }
[ -z "$(git status --porcelain)" ] || { echo "Working tree not clean. Commit or stash first."; git status --short; exit 1; }
[ -f STOP ] && { echo "Remove the STOP file first: rm STOP"; exit 1; }
git pull --ff-only origin main >>"$LOG" 2>&1 || { echo "git pull failed; see $LOG"; exit 1; }

log "preflight: checking Claude Code auth and permission mode '$PERMISSION_MODE'"
claude -p "Reply with the single word OK." --model "$MODEL" --permission-mode "$PERMISSION_MODE" \
  --max-budget-usd 0.25 --output-format json > logs/preflight.json 2>logs/preflight.err
if ! grep -q '"result"' logs/preflight.json; then
  echo "Preflight failed. See logs/preflight.err. Common fixes:"
  echo "  - sign Claude Code in: run 'claude', then /login (Console / API billing option)"
  echo "  - auto mode unavailable: PERMISSION_MODE=acceptEdits bash scripts/run_loop.sh"
  exit 1
fi
spent=$(cost_of logs/preflight.json 0.25)
log "preflight ok (cost ~\$$spent). Stop at $STOP_AT, total cap \$$MAX_TOTAL_USD, model $MODEL"

# ---- rounds ----------------------------------------------------------------------------
round=0; fails=0
while :; do
  [ -f STOP ] && { log "STOP file found: stopping."; break; }
  [ "$(now)" -ge "$((10#$STOP_AT))" ] && { log "Reached STOP_AT $STOP_AT: stopping."; break; }
  budget=$IMPROVE_ROUND_USD; [ -f .claude/BUILD_COMPLETE ] || budget=$BUILD_ROUND_USD
  remaining=$("$PY" -c "import sys; print(round(float(sys.argv[1]) - float(sys.argv[2]), 2))" "$MAX_TOTAL_USD" "$spent")
  lt "$remaining" 0.5 && { log "Budget used (~\$$spent of \$$MAX_TOTAL_USD): stopping."; break; }
  lt "$remaining" "$budget" && budget=$remaining

  round=$((round + 1))
  last_good=$(git rev-parse HEAD)
  log "round $round: starting (cap \$$budget, spent so far ~\$$spent)"
  claude -p "$(cat .claude/loop.md)

This is script round $round (number log entries from ITERATION_LOG.md). Local time is $(date '+%H:%M'). No new rounds start after $STOP_AT." \
    --model "$MODEL" --permission-mode "$PERMISSION_MODE" --max-budget-usd "$budget" \
    --output-format json --disallowedTools "Bash(git push*)" "Bash(git reset*)" "Bash(git rebase*)" \
    > "logs/round-$round.json" 2> "logs/round-$round.err"
  rc=$?
  cost=$(cost_of "logs/round-$round.json" "$budget")
  spent=$(add "$spent" "$cost")
  log "round $round: claude exit $rc, cost ~\$$cost, total ~\$$spent"

  # Commit anything Claude left uncommitted, so the check sees exactly what would ship.
  if [ -n "$(git status --porcelain)" ]; then
    git add -A && git commit -q -m "Loop round $round: uncommitted changes" >>"$LOG" 2>&1
  fi

  if bash scripts/check.sh > "logs/check-$round.log" 2>&1; then
    fails=0
    if [ "$(git rev-parse HEAD)" = "$last_good" ]; then
      log "round $round: checks pass, nothing new to push"
    elif [ "$(now)" -ge "$HARD_STOP" ]; then
      log "round $round: past $HARD_STOP, not pushing. Push by hand if you want it."; break
    elif push_main; then
      log "round $round: checks pass, pushed $(git rev-parse --short HEAD)"
    else
      log "round $round: checks pass but push failed (see $LOG)"
    fi
  else
    fails=$((fails + 1))
    log "round $round: CHECKS FAILED, reverting to $last_good ($fails in a row)"
    { echo "Round $round was reverted because scripts/check.sh failed:"; tail -40 "logs/check-$round.log"; } > logs/last_failure.tmp
    git reset -q --hard "$last_good"
    mv logs/last_failure.tmp .claude/last_failure.txt
    [ "$fails" -ge "$MAX_FAILS" ] && { log "$MAX_FAILS failed rounds in a row: stopping."; break; }
  fi
  sleep "$PAUSE_SECONDS"
done
log "loop finished after $round rounds, ~\$$spent spent. Read ITERATION_LOG.md."
