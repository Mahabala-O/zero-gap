"""Take screenshots of the running app for the UX review (see docs/ux-rubric.md).

Starts `streamlit run app.py` on a spare port with no API key, captures every tab at desktop
(1280x800) and phone (390x844) width, saves PNGs in .ux/, prints their paths, then stops the
server.

One-time setup:  pip install -r requirements-dev.txt && python -m playwright install chromium
Run:             python scripts/screenshot.py
If Chromium lives elsewhere, set PW_CHROMIUM_PATH to its executable.
"""
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / ".ux"
PORT = int(os.environ.get("UX_PORT", "8599"))
URL = f"http://localhost:{PORT}"
SIZES = {"desktop": (1280, 800), "phone": (390, 844)}


def wait_for_server(timeout=90):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{URL}/_stcore/health", timeout=2) as r:
                if r.read().decode().strip() == "ok":
                    return True
        except Exception:
            time.sleep(1)
    return False


def settle(page):
    """Wait until Streamlit has finished running the script."""
    page.wait_for_selector('[data-testid="stApp"]', timeout=60000)
    page.wait_for_timeout(1500)
    for _ in range(60):
        if page.locator('[data-testid="stStatusWidget"]').count() == 0:
            break
        page.wait_for_timeout(500)
    page.wait_for_timeout(1000)


def main():
    if not (ROOT / "app.py").exists():
        print("No app.py yet: nothing to screenshot.")
        return 0
    from playwright.sync_api import sync_playwright

    OUT.mkdir(exist_ok=True)
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    server = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py", "--server.headless", "true",
         "--server.port", str(PORT), "--browser.gatherUsageStats", "false"],
        cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    saved = []
    try:
        if not wait_for_server():
            print("Server did not start; run `streamlit run app.py` to see the error.")
            return 1
        with sync_playwright() as p:
            launch = {"executable_path": os.environ["PW_CHROMIUM_PATH"]} if os.environ.get("PW_CHROMIUM_PATH") else {}
            browser = p.chromium.launch(**launch)
            for label, (w, h) in SIZES.items():
                page = browser.new_page(viewport={"width": w, "height": h})
                page.goto(URL)
                settle(page)
                tabs = page.get_by_role("tab")
                count = max(tabs.count(), 1)
                for i in range(count):
                    if tabs.count():
                        tabs.nth(i).click()
                        settle(page)
                    for kind, full in (("fold", False), ("full", True)):
                        path = OUT / f"tab{i + 1}-{label}-{kind}.png"
                        page.screenshot(path=str(path), full_page=full)
                        saved.append(path)
                page.close()
            browser.close()
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
    for path in saved:
        print(path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
