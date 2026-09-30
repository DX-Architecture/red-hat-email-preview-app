#!/usr/bin/env python3
"""Poll Mailpit, render email HTML with Playwright, store screenshots + metadata."""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

# Allow running as `python workers/linux_playwright_worker.py` from repo root
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config
from database import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [linux-worker] %(message)s",
)
log = logging.getLogger("linux-worker")


def mailpit_get(path: str) -> dict | list:
    url = f"{config.MAILPIT_API_URL.rstrip('/')}{path}"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_message_html(message_id: str) -> str:
    """Prefer HTML part; fall back to text wrapped in <pre>."""
    msg = mailpit_get(f"/api/v1/message/{message_id}")
    html = (msg.get("HTML") or "").strip()
    if html:
        return html
    text = (msg.get("Text") or "").strip()
    if text:
        return f"<pre style='font-family:sans-serif;white-space:pre-wrap'>{text}</pre>"
    return "<p>(empty message body)</p>"


def list_new_messages() -> list[dict]:
    data = mailpit_get("/api/v1/messages?limit=50")
    return list(data.get("messages") or [])


def render_screenshots(test_id: int, html: str) -> dict[str, Path]:
    config.ensure_data_dirs()
    test_dir = config.SCREENSHOTS_DIR / str(test_id)
    test_dir.mkdir(parents=True, exist_ok=True)

    html_path = config.HTML_DIR / f"{test_id}.html"
    html_path.write_text(html, encoding="utf-8")
    file_url = html_path.resolve().as_uri()

    shots = {
        ("playwright", "desktop"): {
            "filename": "desktop.png",
            "device": None,
            "viewport": config.DESKTOP_VIEWPORT,
            "color_scheme": None,
        },
        ("playwright", "mobile-light"): {
            "filename": "mobile-light.png",
            "device": config.MOBILE_DEVICE,
            "viewport": config.MOBILE_VIEWPORT,
            "color_scheme": "light",
        },
        ("playwright", "mobile-dark"): {
            "filename": "mobile-dark.png",
            "device": config.MOBILE_DEVICE,
            "viewport": config.MOBILE_VIEWPORT,
            "color_scheme": "dark",
        },
    }

    results: dict[str, Path] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for (client, variant), opts in shots.items():
            out = test_dir / opts["filename"]
            if opts["device"]:
                device = p.devices[opts["device"]]
                context = browser.new_context(
                    **device,
                    color_scheme=opts["color_scheme"],
                )
            else:
                context = browser.new_context(viewport=opts["viewport"])

            page = context.new_page()
            page.goto(file_url, wait_until="networkidle")
            page.screenshot(path=str(out), full_page=True)
            context.close()

            db.save_screenshot(
                test_id=test_id,
                client=client,
                variant=variant,
                file_path=out,
                worker=config.WORKER_NAME,
            )
            results[f"{client}:{variant}"] = out
            log.info("Saved %s", out)

        browser.close()

    return results


def process_message(message: dict) -> None:
    mailpit_id = message.get("ID") or message.get("id")
    if not mailpit_id:
        log.warning("Skipping message without ID: %s", message)
        return

    existing = db.get_test_by_mailpit_id(mailpit_id)
    if existing and existing.get("status") in {"complete", "linux_complete", "processing"}:
        return

    subject = message.get("Subject") or "(no subject)"
    sender = ""
    from_list = message.get("From")
    if isinstance(from_list, dict):
        sender = from_list.get("Address") or from_list.get("Name") or ""
    elif isinstance(from_list, list) and from_list:
        first = from_list[0]
        sender = first.get("Address") if isinstance(first, dict) else str(first)

    recipients: list[str] = []
    for field in ("To", "Cc", "Bcc"):
        for item in message.get(field) or []:
            if isinstance(item, dict):
                recipients.append(item.get("Address") or item.get("Name") or "")
            else:
                recipients.append(str(item))

    received_at = message.get("Created") or message.get("Date")

    log.info("Processing mailpit_id=%s subject=%r", mailpit_id, subject)
    test_id = db.create_test(
        mailpit_id=mailpit_id,
        subject=subject,
        sender=sender,
        recipients=recipients,
        received_at=received_at,
    )
    db.update_test_status(test_id, "processing")

    try:
        html = fetch_message_html(mailpit_id)
        html_path = config.HTML_DIR / f"{test_id}.html"
        html_path.write_text(html, encoding="utf-8")
        with db.connect() as conn:
            conn.execute(
                "UPDATE email_tests SET html_path = ? WHERE id = ?",
                (str(html_path), test_id),
            )

        render_screenshots(test_id, html)
        db.refresh_completion(test_id)
        log.info("Linux render complete for test_id=%s", test_id)
    except Exception as exc:
        log.exception("Failed processing test_id=%s", test_id)
        db.update_test_status(test_id, "error", error_message=str(exc))


def poll_once() -> int:
    messages = list_new_messages()
    processed = 0
    for message in messages:
        before = db.get_test_by_mailpit_id(message.get("ID", ""))
        process_message(message)
        after = db.get_test_by_mailpit_id(message.get("ID", ""))
        if after and (not before or before.get("status") != after.get("status")):
            processed += 1
    return processed


def main() -> None:
    config.ensure_data_dirs()
    db.init_db()
    log.info(
        "Starting Linux Playwright worker; Mailpit=%s poll=%ss data=%s",
        config.MAILPIT_API_URL,
        config.MAILPIT_POLL_SECONDS,
        config.DATA_DIR,
    )
    while True:
        try:
            n = poll_once()
            if n:
                log.info("Processed %s message(s)", n)
        except requests.RequestException as exc:
            log.warning("Mailpit unreachable: %s", exc)
        except Exception:
            log.exception("Unexpected poll error")
        time.sleep(config.MAILPIT_POLL_SECONDS)


if __name__ == "__main__":
    main()
