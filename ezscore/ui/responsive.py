"""Responsive UI contract for desktop, tablet and phone."""

from __future__ import annotations

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


def render_responsive_css() -> None:
    """Inject application-level responsive rules."""
    st.markdown(_CSS, unsafe_allow_html=True)
