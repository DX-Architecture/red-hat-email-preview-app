"""SQLite persistence for email preview test history and screenshot metadata."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS email_tests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mailpit_id TEXT UNIQUE,
    subject TEXT NOT NULL,
    sender TEXT,
    recipients TEXT,
    received_at TEXT,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    html_path TEXT,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS screenshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_id INTEGER NOT NULL,
    client TEXT NOT NULL,
    variant TEXT NOT NULL,
    file_path TEXT NOT NULL,
    created_at TEXT NOT NULL,
    worker TEXT,
    FOREIGN KEY (test_id) REFERENCES email_tests(id),
    UNIQUE (test_id, client, variant)
);

CREATE INDEX IF NOT EXISTS idx_email_tests_created_at ON email_tests(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_email_tests_status ON email_tests(status);
"""


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    config.ensure_data_dirs()
    conn = sqlite3.connect(config.DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)


def create_test(
    *,
    mailpit_id: str,
    subject: str,
    sender: str = "",
    recipients: list[str] | None = None,
    received_at: str | None = None,
    html_path: str | None = None,
) -> int:
    recipients_json = json.dumps(recipients or [])
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO email_tests (
                mailpit_id, subject, sender, recipients, received_at,
                created_at, status, html_path
            ) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
            ON CONFLICT(mailpit_id) DO UPDATE SET
                subject=excluded.subject,
                sender=excluded.sender,
                recipients=excluded.recipients,
                received_at=excluded.received_at,
                html_path=COALESCE(excluded.html_path, email_tests.html_path)
            RETURNING id
            """,
            (
                mailpit_id,
                subject or "(no subject)",
                sender,
                recipients_json,
                received_at,
                _utcnow(),
                html_path,
            ),
        )
        row = cur.fetchone()
        return int(row["id"])


def get_test(test_id: int) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM email_tests WHERE id = ?", (test_id,)).fetchone()
        return _row_to_dict(row)


def get_test_by_mailpit_id(mailpit_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM email_tests WHERE mailpit_id = ?", (mailpit_id,)
        ).fetchone()
        return _row_to_dict(row)


def list_tests(limit: int = 50, status: str | None = None) -> list[dict[str, Any]]:
    with connect() as conn:
        if status:
            rows = conn.execute(
                """
                SELECT * FROM email_tests
                WHERE status = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM email_tests
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]


def update_test_status(
    test_id: int,
    status: str,
    error_message: str | None = None,
) -> None:
    with connect() as conn:
        conn.execute(
            """
            UPDATE email_tests
            SET status = ?, error_message = ?
            WHERE id = ?
            """,
            (status, error_message, test_id),
        )


def claim_pending_for_outlook(limit: int = 5) -> list[dict[str, Any]]:
    """Return pending/linux-complete tests that still need an Outlook screenshot."""
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT t.*
            FROM email_tests t
            WHERE t.status IN ('pending', 'linux_complete', 'processing')
              AND NOT EXISTS (
                SELECT 1 FROM screenshots s
                WHERE s.test_id = t.id AND s.client = 'outlook' AND s.variant = 'desktop'
              )
            ORDER BY t.created_at ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def save_screenshot(
    *,
    test_id: int,
    client: str,
    variant: str,
    file_path: str | Path,
    worker: str | None = None,
) -> int:
    path = str(file_path)
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO screenshots (test_id, client, variant, file_path, created_at, worker)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(test_id, client, variant) DO UPDATE SET
                file_path=excluded.file_path,
                created_at=excluded.created_at,
                worker=excluded.worker
            RETURNING id
            """,
            (test_id, client, variant, path, _utcnow(), worker),
        )
        return int(cur.fetchone()["id"])


def list_screenshots(test_id: int) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM screenshots
            WHERE test_id = ?
            ORDER BY client, variant
            """,
            (test_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def mark_linux_complete(test_id: int) -> None:
    update_test_status(test_id, "linux_complete")


def mark_complete(test_id: int) -> None:
    update_test_status(test_id, "complete")


def refresh_completion(test_id: int) -> str:
    """Set status to complete when Linux + Outlook shots exist; otherwise linux_complete."""
    shots = list_screenshots(test_id)
    clients = {s["client"] for s in shots}
    has_linux = "playwright" in clients or "browser" in clients
    has_outlook = "outlook" in clients
    if has_linux and has_outlook:
        mark_complete(test_id)
        return "complete"
    if has_linux:
        mark_linux_complete(test_id)
        return "linux_complete"
    return get_test(test_id)["status"] if get_test(test_id) else "pending"
