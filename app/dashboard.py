#!/usr/bin/env python3
"""Streamlit dashboard for Red Hat Email Preview (OpenShift Route)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config
from database import db

st.set_page_config(
    page_title=config.APP_TITLE,
    page_icon="https://ux.redhat.com/assets/logo-red-hat.svg",
    layout="wide",
)

STATUS_HELP = {
    "pending": "Queued — waiting for Linux render",
    "processing": "Linux worker is rendering",
    "linux_complete": "Browser shots ready — waiting for Outlook",
    "complete": "All screenshots available",
    "error": "Render failed — see error message",
}


def _init() -> None:
    config.ensure_data_dirs()
    db.init_db()


def _parse_recipients(raw: str | None) -> str:
    if not raw:
        return "—"
    try:
        items = json.loads(raw)
        return ", ".join(i for i in items if i) or "—"
    except json.JSONDecodeError:
        return raw


def _show_gallery(test_id: int) -> None:
    shots = db.list_screenshots(test_id)
    if not shots:
        st.info("No screenshots yet.")
        return

    by_client: dict[str, list[dict]] = {}
    for shot in shots:
        by_client.setdefault(shot["client"], []).append(shot)

    for client, client_shots in by_client.items():
        st.subheader(client.replace("-", " ").title())
        cols = st.columns(max(len(client_shots), 1))
        for col, shot in zip(cols, client_shots):
            path = Path(shot["file_path"])
            with col:
                st.caption(shot["variant"])
                if path.exists():
                    st.image(str(path), use_container_width=True)
                else:
                    st.warning(f"Missing file: {path}")


def main() -> None:
    _init()

    st.title(config.APP_TITLE)
    st.caption(
        "Internal Email on Acid replacement — Mailpit ingestion, "
        "Playwright browser renders, Outlook captures, SQLite history."
    )

    tests = db.list_tests(limit=100)
    if not tests:
        st.warning(
            "No email tests yet. Send a message to the OpenShift testing alias "
            "and wait for Mailpit + the Linux worker to pick it up."
        )
        st.code(
            "Marketer → testing alias → Mailpit → Playwright worker → SQLite/PVC → this dashboard",
            language="text",
        )
        return

    labels = {
        t["id"]: f"#{t['id']} · {t['subject']} · {t['status']} · {t['created_at'][:19]}"
        for t in tests
    }
    selected_id = st.selectbox(
        "Select a test",
        options=list(labels.keys()),
        format_func=lambda i: labels[i],
    )
    test = next(t for t in tests if t["id"] == selected_id)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Status", test["status"])
    c2.metric("Sender", test["sender"] or "—")
    c3.metric("Received", (test["received_at"] or test["created_at"] or "—")[:19])
    c4.metric("Mailpit ID", (test["mailpit_id"] or "—")[:12] + "…")

    st.write("**Recipients:**", _parse_recipients(test.get("recipients")))
    st.caption(STATUS_HELP.get(test["status"], ""))
    if test.get("error_message"):
        st.error(test["error_message"])

    st.divider()
    _show_gallery(int(test["id"]))

    with st.expander("Raw metadata"):
        st.json(test)

    st.divider()
    st.subheader("Recent tests")
    table = [
        {
            "id": t["id"],
            "subject": t["subject"],
            "status": t["status"],
            "sender": t["sender"],
            "created_at": (t["created_at"] or "")[:19],
        }
        for t in tests
    ]
    st.dataframe(table, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
