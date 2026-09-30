"""Shared configuration for the Red Hat Email Preview App."""

from __future__ import annotations

import os
from pathlib import Path


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default).strip()


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    return int(raw)


# Persistent volume mount (shared PVC in OpenShift)
DATA_DIR = Path(_env("DATA_DIR", "/data"))
SCREENSHOTS_DIR = DATA_DIR / "screenshots"
HTML_DIR = DATA_DIR / "html"
DB_PATH = Path(_env("DB_PATH", str(DATA_DIR / "email_preview.db")))

# Mailpit (SMTP catcher + HTTP API)
MAILPIT_API_URL = _env("MAILPIT_API_URL", "http://mailpit:8025")
MAILPIT_POLL_SECONDS = _env_int("MAILPIT_POLL_SECONDS", 10)

# Worker identity / behavior
WORKER_NAME = _env("WORKER_NAME", "linux-playwright")
WINDOWS_WORKER_POLL_SECONDS = _env_int("WINDOWS_WORKER_POLL_SECONDS", 15)
WINDOWS_WORKER_API_TOKEN = _env("WINDOWS_WORKER_API_TOKEN", "")

# Screenshot viewports
DESKTOP_VIEWPORT = {"width": 1280, "height": 800}
MOBILE_VIEWPORT = {"width": 390, "height": 844}
MOBILE_DEVICE = "iPhone 13"

# Dashboard
APP_TITLE = _env("APP_TITLE", "Red Hat Email Preview")
STREAMLIT_SERVER_PORT = _env_int("STREAMLIT_SERVER_PORT", 8501)


def ensure_data_dirs() -> None:
    """Create persistent storage directories if they do not exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    HTML_DIR.mkdir(parents=True, exist_ok=True)
