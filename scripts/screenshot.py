"""Take screenshots of the running app for the UX review (see docs/ux-rubric.md).

Starts `streamlit run app.py` on a spare port with no API key, captures every page at desktop
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


def content_height(page, minimum, cap=12000):
    """Height of the content inside Streamlit's scrolling container, capped."""
    js = """() => {
        const sels = ['[data-testid="stMain"]', '[data-testid="stAppViewContainer"]', 'section.main'];
        let h = document.documentElement.scrollHeight;
        for (const s of sels) {
            const el = document.querySelector(s);
            if (el) h = Math.max(h, el.scrollHeight);
        }
        return h;
    }"""
    try:
        return max(minimum, min(int(page.evaluate(js)) + 40, cap))
    except Exception:
        return minimum


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
                # Pages are picked with the sidebar radio; its labels are the page names.
                pages = ["What did my city promise?", "After approval, how long to move-in?"]
                for i, name in enumerate(pages):
                    option = page.get_by_text(name, exact=True).first
                    box = page.locator('[data-testid="stSidebar"]').bounding_box()
                    if not box or box["width"] == 0 or box["x"] < 0:
                        # Phone width: the sidebar starts collapsed. Open it to pick a page.
                        page.locator('[data-testid="stSidebarCollapsedControl"] button, '
                                     '[data-testid="collapsedControl"] button').first.click()
                        page.wait_for_timeout(700)
                    option.click()
                    settle(page)
                    if w < 700:
                        # Close the sidebar again so the screenshot shows the result.
                        page.locator('[data-testid="stSidebarCollapseButton"] button, '
                                     '[data-testid="stSidebar"] button[kind="headerNoPadding"]'
                                     ).first.click()
                        page.wait_for_timeout(700)
                    path = OUT / f"page{i + 1}-{label}-fold.png"
                    page.screenshot(path=str(path))
                    saved.append(path)
                    # Streamlit scrolls inside its own container, so full_page=True stops at
                    # the viewport. Grow the viewport to the content height instead.
                    page.set_viewport_size({"width": w, "height": content_height(page, h)})
                    page.wait_for_timeout(1000)
                    path = OUT / f"page{i + 1}-{label}-full.png"
                    page.screenshot(path=str(path))
                    saved.append(path)
                    page.set_viewport_size({"width": w, "height": h})
                    page.wait_for_timeout(500)
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
