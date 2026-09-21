"""Responsive UI contract for desktop, tablet and phone."""

from __future__ import annotations

import re

import streamlit as st

_CSS = r"""
<style>
.stButton button,
.stDownloadButton button,
[role="radiogroup"] label,
.stTextInput input,
.stSelectbox [data-baseweb="select"] {
    min-height: 44px;
}

html,
body,
[data-testid="stAppViewContainer"] {
    overflow-x: hidden;
}

@media (max-width: 900px) {
    .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }

    [role="radiogroup"] {
        flex-wrap: wrap !important;
        row-gap: .35rem !important;
    }

    div[data-testid="stPopoverBody"] {
        max-width: min(92vw, 420px) !important;
    }
}

@media (max-width: 640px) {
    .block-container {
        padding-left: .65rem !important;
        padding-right: .65rem !important;
    }

    .app-title {
        font-size: 1.55rem !important;
    }

    .lyrics-chords {
        font-size: 1.45rem !important;
    }

    .lyrics-text {
        font-size: 1.55rem !important;
    }

    div[data-testid="stHorizontalBlock"] {
        flex-wrap: wrap;
    }

    div[data-testid="column"] {
        min-width: 100% !important;
        width: 100% !important;
    }

    .stButton button,
    .stDownloadButton button {
        width: 100%;
    }

    [data-testid="stFileUploader"] {
        width: 100%;
    }

    [role="radiogroup"] label {
        padding-top: .35rem !important;
        padding-bottom: .35rem !important;
    }
}
</style>
"""

_EZNAV_SPAN = re.compile(
    r'^\\s*<span\\s+class=["\\\']eznav-item(?:\\s+active)?["\\\']>'
    r'.*?</span>\\s*$',
    flags=re.IGNORECASE | re.DOTALL,
)


def _install_nav_markup_fix() -> None:
    """Render EZScore's own navigation span as HTML, never as literal text."""
    current_markdown = st.markdown
    if getattr(current_markdown, "_ezscore_nav_markup_fix", False):
        return

    def markdown_with_nav_markup(*args, **kwargs):
        if args:
            value = str(args[0] or "")
            if _EZNAV_SPAN.fullmatch(value):
                kwargs = dict(kwargs)
                kwargs["unsafe_allow_html"] = True
        return current_markdown(*args, **kwargs)

    markdown_with_nav_markup._ezscore_nav_markup_fix = True
    st.markdown = markdown_with_nav_markup


_install_nav_markup_fix()


def render_responsive_css() -> None:
    """Inject application-level responsive rules."""
    st.markdown(_CSS, unsafe_allow_html=True)
