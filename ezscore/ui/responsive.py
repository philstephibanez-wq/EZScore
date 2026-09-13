"""Responsive UI contract for desktop, tablet and phone."""

from __future__ import annotations

import streamlit as st

_CSS = r"""
<style>
.stButton button,
.stDownloadButton button,
[role="radiogroup"] label {
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
}
</style>
"""


def render_responsive_css() -> None:
    """Inject application-level responsive rules."""
    st.markdown(_CSS, unsafe_allow_html=True)
