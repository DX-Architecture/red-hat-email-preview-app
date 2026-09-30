#!/usr/bin/env python3
"""Streamlit dashboard for Red Hat Email Preview (PatternFly / RHDS styled)."""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config
from app import theme
from database import db

st.set_page_config(
    page_title=config.APP_TITLE,
    page_icon="https://static.redhat.com/libs/redhat/brand-standards/latest/img/logo.svg",
    layout="wide",
    initial_sidebar_state="collapsed",
)

STATUS_HELP = {
    "pending": "Queued — waiting for Linux render",
    "processing": "Linux worker is rendering browser screenshots",
    "linux_complete": "Browser shots ready — waiting for Outlook worker",
    "complete": "All screenshots available",
    "error": "Render failed — see error details below",
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
        theme.alert("info", "No screenshots yet", "The worker has not finished rendering this test.")
        return

    by_client: dict[str, list[dict]] = {}
    for shot in shots:
        by_client.setdefault(shot["client"], []).append(shot)

    for client, client_shots in by_client.items():
        theme.section_heading(client.replace("-", " ").title())
        cols = st.columns(max(len(client_shots), 1))
        for col, shot in zip(cols, client_shots):
            path = Path(shot["file_path"])
            with col:
                st.markdown(
                    f'<div class="pf-shot-card">'
                    f'<div class="pf-shot-card__label">{html.escape(shot["variant"])}</div>'
                    f"</div>",
                    unsafe_allow_html=True,
                )
                if path.exists():
                    st.image(str(path), use_container_width=True)
                else:
                    theme.alert("warning", "Missing file", str(path))


def _status_alert(status: str, error_message: str | None) -> None:
    help_text = STATUS_HELP.get(status, "")
    if status == "error":
        theme.alert("danger", "Render error", error_message or help_text)
    elif status == "complete":
        theme.alert("success", "Preview complete", help_text)
    elif status in {"pending", "processing"}:
        theme.alert("info", "In progress", help_text)
    elif status == "linux_complete":
        theme.alert("warning", "Partial complete", help_text)


def main() -> None:
    _init()
    theme.inject_styles()
    theme.masthead(config.APP_TITLE)
    theme.page_header(
        "Email preview tests",
        "Internal Email on Acid replacement — Mailpit ingestion, "
        "Playwright browser renders, Outlook captures, SQLite history.",
    )

    tests = db.list_tests(limit=100)
    if not tests:
        theme.empty_state(
            title="No email tests yet",
            body=(
                "Send a message to the OpenShift testing alias and wait for "
                "Mailpit and the Linux worker to pick it up."
            ),
            code="Marketer → testing alias → Mailpit → Playwright worker → SQLite/PVC → this dashboard",
        )
        return

    labels = {
        t["id"]: f"#{t['id']} · {t['subject']} · {t['status']} · {(t['created_at'] or '')[:19]}"
        for t in tests
    }

    with st.container():
        st.markdown('<div class="pf-card">', unsafe_allow_html=True)
        selected_id = st.selectbox(
            "Select a test",
            options=list(labels.keys()),
            format_func=lambda i: labels[i],
        )
        st.markdown("</div>", unsafe_allow_html=True)

    test = next(t for t in tests if t["id"] == selected_id)
    status = test["status"] or "pending"
    mailpit_id = test.get("mailpit_id") or "—"
    if mailpit_id != "—" and len(mailpit_id) > 12:
        mailpit_short = html.escape(mailpit_id[:12]) + "…"
    else:
        mailpit_short = html.escape(str(mailpit_id))

    theme.description_list(
        {
            "Status": theme.status_label(status),
            "Sender": html.escape(test["sender"] or "—"),
            "Received": html.escape((test["received_at"] or test["created_at"] or "—")[:19]),
            "Mailpit ID": mailpit_short,
            "Recipients": html.escape(_parse_recipients(test.get("recipients"))),
            "Subject": html.escape(test.get("subject") or "—"),
        }
    )

    _status_alert(status, test.get("error_message"))

    theme.section_heading("Screenshots")
    st.markdown('<div class="pf-card">', unsafe_allow_html=True)
    _show_gallery(int(test["id"]))
    st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("Raw metadata"):
        st.json(test)

    theme.section_heading("Recent tests")
    table = [
        {
            "ID": t["id"],
            "Subject": t["subject"],
            "Status": t["status"],
            "Sender": t["sender"],
            "Created": (t["created_at"] or "")[:19],
        }
        for t in tests
    ]
    st.dataframe(table, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
