"""PatternFly / RHDS-inspired Streamlit theme helpers.

Streamlit cannot host RHDS web components, so we apply Red Hat design tokens
and PatternFly layout patterns (masthead, card, label, alert, empty state)
via scoped CSS + lightweight HTML fragments.
Token source: https://ux.redhat.com/tokens/color/
"""

from __future__ import annotations

import html
from typing import Mapping

import streamlit as st

# RHDS / PatternFly-aligned tokens
RH = {
    "brand": "#EE0000",
    "brand_dark": "#A60000",
    "text": "#151515",
    "text_secondary": "#4D4D4D",
    "border": "#C7C7C7",
    "surface": "#FFFFFF",
    "surface_alt": "#F2F2F2",
    "link": "#0066CC",
    "success_bg": "#E9F7E9",
    "success_text": "#1E4F18",
    "success_border": "#3E8635",
    "warning_bg": "#FFF4CC",
    "warning_text": "#73480B",
    "warning_border": "#DCA614",
    "danger_bg": "#FCE3E3",
    "danger_text": "#A60000",
    "danger_border": "#EE0000",
    "info_bg": "#E0F0FF",
    "info_text": "#003366",
    "info_border": "#0066CC",
    "purple_bg": "#ECE6FF",
    "purple_text": "#3D2785",
    "blue_bg": "#E0F0FF",
    "blue_text": "#002952",
}

STATUS_LABEL: Mapping[str, tuple[str, str, str]] = {
    # status -> (bg, text, border)
    "pending": (RH["info_bg"], RH["info_text"], RH["info_border"]),
    "processing": (RH["purple_bg"], RH["purple_text"], "#876FD4"),
    "linux_complete": (RH["warning_bg"], RH["warning_text"], RH["warning_border"]),
    "complete": (RH["success_bg"], RH["success_text"], RH["success_border"]),
    "error": (RH["danger_bg"], RH["danger_text"], RH["danger_border"]),
}


def inject_styles() -> None:
    """Inject Red Hat fonts + PatternFly-inspired Streamlit overrides."""
    st.markdown(
        f"""
<style>
@import url("https://fonts.googleapis.com/css2?family=Red+Hat+Display:wght@400;500;700&family=Red+Hat+Text:wght@400;500;700&display=swap");

:root {{
  --rh-brand: {RH["brand"]};
  --rh-brand-dark: {RH["brand_dark"]};
  --rh-text: {RH["text"]};
  --rh-text-secondary: {RH["text_secondary"]};
  --rh-border: {RH["border"]};
  --rh-surface: {RH["surface"]};
  --rh-surface-alt: {RH["surface_alt"]};
  --rh-link: {RH["link"]};
  --pf-font-display: "Red Hat Display", "RedHatDisplay", Helvetica, Arial, sans-serif;
  --pf-font-text: "Red Hat Text", "RedHatText", Helvetica, Arial, sans-serif;
}}

html, body, [class*="css"] {{
  font-family: var(--pf-font-text) !important;
  color: var(--rh-text);
}}

/* Hide Streamlit chrome that fights PatternFly masthead */
#MainMenu {{ visibility: hidden; }}
footer {{ visibility: hidden; }}
header[data-testid="stHeader"] {{
  background: transparent;
  height: 0;
}}
div[data-testid="stToolbar"] {{ display: none; }}

.stApp {{
  background: var(--rh-surface-alt);
}}

.block-container {{
  padding-top: 1rem !important;
  padding-bottom: 3rem !important;
  max-width: 1200px;
}}

/* ---- Masthead (PatternFly pf-c-masthead) ---- */
.pf-masthead {{
  background: #151515;
  color: #fff;
  margin: -1rem -1rem 1.5rem -1rem;
  padding: 0.75rem 1.5rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  border-bottom: 3px solid var(--rh-brand);
}}
.pf-masthead__brand {{
  display: flex;
  align-items: center;
  gap: 0.75rem;
  text-decoration: none;
  color: #fff !important;
}}
.pf-masthead__logo {{
  height: 28px;
  width: auto;
}}
.pf-masthead__title {{
  font-family: var(--pf-font-display);
  font-weight: 500;
  font-size: 1.05rem;
  letter-spacing: 0.01em;
  border-left: 1px solid #4d4d4d;
  padding-left: 0.75rem;
  margin: 0;
}}
.pf-masthead__meta {{
  margin-left: auto;
  font-size: 0.8rem;
  color: #c7c7c7;
}}

/* ---- Page header ---- */
.pf-page-header {{
  margin-bottom: 1.25rem;
}}
.pf-page-header__title {{
  font-family: var(--pf-font-display);
  font-size: 1.75rem;
  font-weight: 500;
  color: var(--rh-text);
  margin: 0 0 0.25rem 0;
  line-height: 1.3;
}}
.pf-page-header__subtitle {{
  color: var(--rh-text-secondary);
  font-size: 0.95rem;
  margin: 0;
}}

/* ---- Cards (pf-c-card) ---- */
.pf-card {{
  background: var(--rh-surface);
  border: 1px solid var(--rh-border);
  border-radius: 0;
  box-shadow: 0 0.0625rem 0.125rem 0 rgba(3, 3, 3, 0.12),
              0 0 0.125rem 0 rgba(3, 3, 3, 0.06);
  padding: 1.25rem 1.5rem;
  margin-bottom: 1rem;
}}
.pf-card__title {{
  font-family: var(--pf-font-display);
  font-size: 1.125rem;
  font-weight: 500;
  margin: 0 0 0.75rem 0;
  color: var(--rh-text);
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--rh-border);
}}
.pf-card__body {{
  color: var(--rh-text);
  font-size: 0.925rem;
}}

/* ---- Labels / status badges (pf-c-label) ---- */
.pf-label {{
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.15rem 0.5rem;
  font-size: 0.75rem;
  font-weight: 500;
  line-height: 1.4;
  border: 1px solid;
  border-radius: 30px;
  text-transform: none;
  white-space: nowrap;
}}
.pf-label::before {{
  content: "";
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 50%;
  background: currentColor;
  flex-shrink: 0;
}}

/* ---- Description list (pf-c-description-list) ---- */
.pf-dl {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 0.75rem 1.25rem;
  margin: 0;
}}
.pf-dl__group {{
  min-width: 0;
}}
.pf-dl__term {{
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--rh-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin: 0 0 0.15rem 0;
}}
.pf-dl__desc {{
  font-size: 0.95rem;
  color: var(--rh-text);
  margin: 0;
  word-break: break-word;
}}

/* ---- Alert (pf-c-alert) ---- */
.pf-alert {{
  display: flex;
  gap: 0.75rem;
  padding: 0.85rem 1rem;
  border: 1px solid;
  border-left-width: 4px;
  margin: 0.75rem 0 1rem 0;
  background: var(--rh-surface);
}}
.pf-alert--info {{
  border-color: {RH["info_border"]};
  background: {RH["info_bg"]};
  color: {RH["info_text"]};
}}
.pf-alert--warning {{
  border-color: {RH["warning_border"]};
  background: {RH["warning_bg"]};
  color: {RH["warning_text"]};
}}
.pf-alert--danger {{
  border-color: {RH["danger_border"]};
  background: {RH["danger_bg"]};
  color: {RH["danger_text"]};
}}
.pf-alert--success {{
  border-color: {RH["success_border"]};
  background: {RH["success_bg"]};
  color: {RH["success_text"]};
}}
.pf-alert__title {{
  font-weight: 700;
  font-family: var(--pf-font-display);
  margin: 0 0 0.2rem 0;
  font-size: 0.95rem;
}}
.pf-alert__desc {{
  margin: 0;
  font-size: 0.875rem;
}}

/* ---- Empty state (pf-c-empty-state) ---- */
.pf-empty {{
  text-align: center;
  padding: 2.5rem 1.5rem;
}}
.pf-empty__icon {{
  font-size: 2.5rem;
  color: var(--rh-brand);
  margin-bottom: 0.75rem;
}}
.pf-empty__title {{
  font-family: var(--pf-font-display);
  font-size: 1.35rem;
  font-weight: 500;
  margin: 0 0 0.5rem 0;
}}
.pf-empty__body {{
  color: var(--rh-text-secondary);
  max-width: 36rem;
  margin: 0 auto 1rem auto;
  font-size: 0.95rem;
}}
.pf-empty__code {{
  display: inline-block;
  text-align: left;
  background: #151515;
  color: #f2f2f2;
  padding: 0.75rem 1rem;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.8rem;
  border-left: 3px solid var(--rh-brand);
  max-width: 100%;
  overflow-x: auto;
}}

/* ---- Screenshot gallery cards ---- */
.pf-shot-card {{
  background: var(--rh-surface);
  border: 1px solid var(--rh-border);
  padding: 0.75rem;
  height: 100%;
}}
.pf-shot-card__label {{
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--rh-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 0.5rem;
}}

/* Streamlit widget polish */
div[data-testid="stSelectbox"] label,
div[data-testid="stMetric"] label {{
  font-family: var(--pf-font-text) !important;
  color: var(--rh-text-secondary) !important;
  font-size: 0.8rem !important;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}}
div[data-testid="stMetricValue"] {{
  font-family: var(--pf-font-display) !important;
  color: var(--rh-text) !important;
}}
div[data-testid="stExpander"] {{
  border: 1px solid var(--rh-border);
  background: var(--rh-surface);
}}
div[data-testid="stDataFrame"] {{
  border: 1px solid var(--rh-border);
}}
.stDivider {{
  margin: 1.25rem 0;
}}

/* Primary button → brand red */
button[kind="primary"],
div[data-testid="stButton"] button[kind="primary"] {{
  background-color: var(--rh-brand) !important;
  border-color: var(--rh-brand) !important;
  color: #fff !important;
}}
button[kind="primary"]:hover {{
  background-color: var(--rh-brand-dark) !important;
  border-color: var(--rh-brand-dark) !important;
}}

a {{ color: var(--rh-link); }}
</style>
""",
        unsafe_allow_html=True,
    )


def masthead(app_title: str, meta: str = "DX Architecture · Internal") -> None:
    logo = "https://static.redhat.com/libs/redhat/brand-standards/latest/img/logo.svg"
    st.markdown(
        f"""
<div class="pf-masthead">
  <div class="pf-masthead__brand">
    <img class="pf-masthead__logo" src="{logo}" alt="Red Hat" />
    <p class="pf-masthead__title">{html.escape(app_title)}</p>
  </div>
  <div class="pf-masthead__meta">{html.escape(meta)}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
<div class="pf-page-header">
  <h1 class="pf-page-header__title">{html.escape(title)}</h1>
  <p class="pf-page-header__subtitle">{html.escape(subtitle)}</p>
</div>
""",
        unsafe_allow_html=True,
    )


def status_label(status: str) -> str:
    bg, text, border = STATUS_LABEL.get(
        status, (RH["surface_alt"], RH["text"], RH["border"])
    )
    label = html.escape(status.replace("_", " "))
    return (
        f'<span class="pf-label" style="background:{bg};color:{text};border-color:{border}">'
        f"{label}</span>"
    )


def alert(kind: str, title: str, body: str = "") -> None:
    safe_kind = kind if kind in {"info", "warning", "danger", "success"} else "info"
    body_html = f'<p class="pf-alert__desc">{html.escape(body)}</p>' if body else ""
    st.markdown(
        f"""
<div class="pf-alert pf-alert--{safe_kind}" role="alert">
  <div>
    <p class="pf-alert__title">{html.escape(title)}</p>
    {body_html}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def empty_state(title: str, body: str, code: str = "") -> None:
    code_html = (
        f'<pre class="pf-empty__code">{html.escape(code)}</pre>' if code else ""
    )
    st.markdown(
        f"""
<div class="pf-card">
  <div class="pf-empty">
    <div class="pf-empty__icon" aria-hidden="true">✉</div>
    <h2 class="pf-empty__title">{html.escape(title)}</h2>
    <p class="pf-empty__body">{html.escape(body)}</p>
    {code_html}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def description_list(items: Mapping[str, str]) -> None:
    groups = []
    for term, desc in items.items():
        groups.append(
            f"""
<div class="pf-dl__group">
  <dt class="pf-dl__term">{html.escape(term)}</dt>
  <dd class="pf-dl__desc">{desc}</dd>
</div>"""
        )
    st.markdown(
        f'<div class="pf-card"><dl class="pf-dl">{"".join(groups)}</dl></div>',
        unsafe_allow_html=True,
    )


def card_title(title: str) -> None:
    st.markdown(
        f'<div class="pf-card" style="padding-bottom:0.5rem;margin-bottom:0.5rem">'
        f'<h2 class="pf-card__title" style="border:none;padding:0;margin:0">'
        f"{html.escape(title)}</h2></div>",
        unsafe_allow_html=True,
    )


def section_heading(title: str) -> None:
    st.markdown(
        f'<h2 class="pf-card__title" style="border:none;margin:1rem 0 0.75rem 0">'
        f"{html.escape(title)}</h2>",
        unsafe_allow_html=True,
    )
