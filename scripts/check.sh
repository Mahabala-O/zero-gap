#!/usr/bin/env bash
# Gate run before every push by scripts/run_loop.sh. Exit 0 means the app still works.
# Run it yourself any time:  bash scripts/check.sh
set -u
cd "$(dirname "$0")/.."
PY="${PYTHON:-python3}"
fail() { echo "CHECK FAILED: $1"; exit 1; }

# 1. No secrets in tracked files, and .env never tracked.
if git ls-files --error-unmatch .env >/dev/null 2>&1; then fail ".env is tracked by git"; fi
if git grep -nI -E "sk-ant-[A-Za-z0-9_-]{10,}" >/dev/null 2>&1; then fail "possible API key in a tracked file"; fi

# 2. Every Python file compiles.
"$PY" -m compileall -q -x '(\.venv|venv|node_modules|\.ux)' . >/dev/null || fail "a Python file does not compile"

# 3. Tests pass, if there are any.
if [ -n "$(find . -path ./.venv -prune -o -path ./venv -prune -o -name 'test_*.py' -print -quit)" ]; then
  "$PY" -m pytest -q -x || fail "tests failed"
fi

# 4. The Streamlit app runs top to bottom without an exception, with NO API key set
#    (so the app must work without Claude, and the check never spends credits).
if [ -f app.py ]; then
  env -u ANTHROPIC_API_KEY "$PY" - <<'EOF' || fail "app.py raised an exception (see above)"
from streamlit.testing.v1 import AppTest
at = AppTest.from_file("app.py", default_timeout=120).run()
if at.exception:
    for e in at.exception:
        print("APP EXCEPTION:", e.message)
    raise SystemExit(1)
print("app ok")
EOF
fi

echo "CHECKS PASSED"
