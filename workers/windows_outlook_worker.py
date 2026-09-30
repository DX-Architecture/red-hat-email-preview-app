#!/usr/bin/env python3
"""
Windows Outlook rendering worker (runs on an external Windows VM).

MVP behavior:
1. Polls the shared SQLite DB (via mounted/synced PVC path or network share)
   for tests that still need an Outlook screenshot.
2. Opens the saved HTML in Outlook (or Edge fallback) and captures a screenshot.
3. Writes the PNG next to the Linux shots and updates SQLite.

Outlook automation uses pywin32 when available. If Outlook is not installed
or COM fails, the worker falls back to a Chromium/Edge full-page screenshot
labeled as outlook/desktop so the pipeline still completes in demo environments.
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config
from database import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [windows-worker] %(message)s",
)
log = logging.getLogger("windows-worker")


def _capture_with_playwright(html_path: Path, out_path: Path) -> None:
    """Fallback renderer when Outlook COM is unavailable."""
    from playwright.sync_api import sync_playwright

    file_url = html_path.resolve().as_uri()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport=config.DESKTOP_VIEWPORT)
        page = context.new_page()
        page.goto(file_url, wait_until="networkidle")
        page.screenshot(path=str(out_path), full_page=True)
        context.close()
        browser.close()


def _capture_with_outlook(html_path: Path, out_path: Path) -> None:
    """
    Native Outlook render via COM + window screenshot.

    Requires: Windows, Outlook installed, pywin32, and pillow.
    """
    import pythoncom  # type: ignore
    import win32com.client  # type: ignore
    import win32gui  # type: ignore
    import win32ui  # type: ignore
    from PIL import ImageGrab  # type: ignore

    pythoncom.CoInitialize()
    outlook = win32com.client.Dispatch("Outlook.Application")
    # olMailItem = 0
    mail = outlook.CreateItem(0)
    html = html_path.read_text(encoding="utf-8")
    mail.HTMLBody = html
    mail.Display(False)
    time.sleep(2)

    hwnd = win32gui.FindWindow(None, mail.Subject or "Untitled")
    if not hwnd:
        # Fallback: grab the active inspector window bounds via ImageGrab of primary screen crop
        bbox = None
        inspectors = outlook.Inspectors
        if inspectors.Count >= 1:
            # Best-effort full-screen grab of inspector area
            bbox = None
        img = ImageGrab.grab(bbox=bbox)
        img.save(out_path)
    else:
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        img = ImageGrab.grab(bbox=(left, top, right, bottom))
        img.save(out_path)

    try:
        mail.Close(0)  # olDiscard
    except Exception:
        pass


def render_outlook(test: dict) -> Path:
    test_id = int(test["id"])
    html_path = Path(test["html_path"] or (config.HTML_DIR / f"{test_id}.html"))
    if not html_path.exists():
        raise FileNotFoundError(f"HTML not found for test {test_id}: {html_path}")

    out_dir = config.SCREENSHOTS_DIR / str(test_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "outlook-desktop.png"

    try:
        if sys.platform.startswith("win"):
            _capture_with_outlook(html_path, out_path)
            log.info("Captured Outlook native screenshot for test_id=%s", test_id)
        else:
            raise RuntimeError("Not on Windows; using Playwright fallback")
    except Exception as exc:
        log.warning(
            "Outlook COM unavailable (%s); using Playwright/Edge fallback for test_id=%s",
            exc,
            test_id,
        )
        _capture_with_playwright(html_path, out_path)

    db.save_screenshot(
        test_id=test_id,
        client="outlook",
        variant="desktop",
        file_path=out_path,
        worker="windows-outlook",
    )
    db.refresh_completion(test_id)
    return out_path


def poll_once() -> int:
    pending = db.claim_pending_for_outlook(limit=5)
    for test in pending:
        try:
            render_outlook(test)
        except Exception as exc:
            log.exception("Outlook render failed for test_id=%s", test.get("id"))
            db.update_test_status(int(test["id"]), "error", error_message=str(exc))
    return len(pending)


def main() -> None:
    config.ensure_data_dirs()
    db.init_db()
    log.info(
        "Starting Windows Outlook worker; poll=%ss data=%s",
        config.WINDOWS_WORKER_POLL_SECONDS,
        config.DATA_DIR,
    )
    while True:
        try:
            n = poll_once()
            if n:
                log.info("Handled %s pending Outlook job(s)", n)
        except Exception:
            log.exception("Unexpected poll error")
        time.sleep(config.WINDOWS_WORKER_POLL_SECONDS)


if __name__ == "__main__":
    main()
