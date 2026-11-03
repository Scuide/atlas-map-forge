"""Exercise the shipped Linux binary, including browser launch and the rendered UI.

Run on Linux with Playwright/Chromium installed. No atlasforge import: all app
requests go to the frozen executable extracted from the download archive.
"""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import sync_playwright


def main():
    executable = Path(sys.argv[1]).resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="atlas-linux-test-") as tmp:
        tmp = Path(tmp)
        cfg = tmp / "config" / "atlas-map-forge"
        cfg.mkdir(parents=True)
        (cfg / "config.json").write_text(json.dumps({"author": "CI", "outdir": str(tmp / "maps")}), encoding="utf8")
        # Capture the URL through Python's real browser launcher, rather than
        # scraping logs or assuming a port. A desktop browser is replaced by
        # headless Chromium only in this CI test.
        capture = tmp / "capture-browser"
        capture.write_text('#!/bin/sh\nprintf "%s" "$1" > "$ATLAS_TEST_URL"\n', encoding="utf8")
        capture.chmod(0o755)
        url_file = tmp / "browser-url"
        env = dict(os.environ, XDG_CONFIG_HOME=str(tmp / "config"),
                   XDG_CACHE_HOME=str(tmp / "cache"), BROWSER=f"{capture} %s",
                   ATLAS_TEST_URL=str(url_file))
        with (tmp / "app.log").open("w+") as log:
            proc = subprocess.Popen([str(executable)], cwd=tmp, env=env,
                                    stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                deadline = time.monotonic() + 90
                while not url_file.exists() or not url_file.read_text():
                    if proc.poll() is not None:
                        raise RuntimeError(f"App exited before opening browser ({proc.returncode})")
                    if time.monotonic() >= deadline:
                        raise TimeoutError("App did not open its browser URL")
                    time.sleep(0.2)
                url = url_file.read_text()
                parsed = urlparse(url)
                assert parsed.scheme == "http" and parsed.hostname == "127.0.0.1", url
                assert parse_qs(parsed.query).get("t"), "Browser URL is missing the session token"
                with sync_playwright() as p:
                    browser = p.chromium.launch()
                    page = browser.new_page(viewport={"width": 1560, "height": 980})
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.goto(url)
                    page.locator("#report li").first.wait_for(timeout=120_000)
                    page.wait_for_function("!document.querySelector('#veil').classList.contains('on')")
                    assert page.locator("#btn-build").is_enabled(), "Preview did not enable map building"
                    assert page.locator("#tpl-count").inner_text().strip(), "Missing template catalogue"
                    assert page.locator("#map").evaluate("c => c.width > 0 && c.height > 0 && c.getContext('2d').getImageData(0, 0, c.width, c.height).data.some((v, i) => i % 4 !== 3 && v > 0)"), "Map canvas is blank"
                    page.screenshot(path="linux-browser-preview.png")
                    # Unauthenticated websites must not be able to use the API.
                    response = page.request.get(f"{parsed.scheme}://{parsed.netloc}/api/state")
                    assert response.status == 403
                    assert not errors, errors
                    browser.close()
                assert proc.poll() is None, "App stopped while the UI was being used"
                print("Linux bundle OK: browser opened, map preview rendered, build enabled, API protected")
            finally:
                if proc.poll() is None:
                    os.killpg(proc.pid, signal.SIGINT)
                    try:
                        proc.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid, signal.SIGKILL)
                        proc.wait(timeout=5)
                log.seek(0)
                print(log.read())


if __name__ == "__main__":
    main()
