"""Finite-state machine for EZScore song view/mode navigation.

This module owns the legal transitions between the song views and the
read/edit modes.  Widget keys are the single source of truth: there is no
secondary radio state to keep in sync.
"""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

VIEW_GRID = "Grille"
VIEW_LYRICS = "Paroles + accords"
VIEW_BLOCKS = "Blocs"
VIEW_ANALYSIS = "Analyse"

MODE_VIEW = "Vue"
MODE_EDIT = "Édition"

EVENT_SELECT_VIEW = "select_view"
EVENT_SELECT_MODE = "select_mode"
EVENT_OPEN_VIEW = "open_view"
EVENT_OPEN_EDIT = "open_edit"


@dataclass(frozen=True)
class SongUiState:
    view: str
    mode: str


def state_keys(audio_hash: str) -> tuple[str, str]:
    prefix = str(audio_hash or "")[:12]
    return f"song_view_{prefix}", f"song_mode_{prefix}"


def allowed_views(can_edit: bool) -> list[str]:
    result = [VIEW_GRID, VIEW_LYRICS]
    if can_edit:
        result.extend([VIEW_BLOCKS, VIEW_ANALYSIS])
    return result


def allowed_modes(view: str, can_edit: bool) -> list[str]:
    if can_edit and view in (VIEW_GRID, VIEW_LYRICS, VIEW_BLOCKS):
        return [MODE_VIEW, MODE_EDIT]
    return [MODE_VIEW]


def normalize(state: SongUiState, can_edit: bool) -> SongUiState:
    views = allowed_views(can_edit)
    view = state.view if state.view in views else VIEW_LYRICS
    modes = allowed_modes(view, can_edit)
    mode = state.mode if state.mode in modes else MODE_VIEW
    return SongUiState(view=view, mode=mode)


def transition(
    state: SongUiState,
    event: str,
    *,
    value: str | None = None,
    can_edit: bool,
) -> SongUiState:
    current = normalize(state, can_edit)

    if event == EVENT_SELECT_VIEW:
        candidate = SongUiState(
            view=str(value or VIEW_LYRICS),
            # Deliberate UX rule: changing view exits edit mode.
            mode=MODE_VIEW,
        )
        return normalize(candidate, can_edit)

    if event == EVENT_SELECT_MODE:
        candidate = SongUiState(
            view=current.view,
            mode=str(value or MODE_VIEW),
        )
        return normalize(candidate, can_edit)

    if event == EVENT_OPEN_EDIT:
        candidate = SongUiState(
            view=str(value or VIEW_GRID),
            mode=MODE_EDIT,
        )
        return normalize(candidate, can_edit)

    if event == EVENT_OPEN_VIEW:
        candidate = SongUiState(
            view=str(value or VIEW_LYRICS),
            mode=MODE_VIEW,
        )
        return normalize(candidate, can_edit)

    return current


def initialize_session(audio_hash: str, can_edit: bool) -> SongUiState:
    view_key, mode_key = state_keys(audio_hash)
    current = SongUiState(
        view=str(st.session_state.get(view_key, VIEW_LYRICS)),
        mode=str(st.session_state.get(mode_key, MODE_VIEW)),
    )
    normalized = normalize(current, can_edit)
    st.session_state[view_key] = normalized.view
    st.session_state[mode_key] = normalized.mode
    return normalized


def apply_session_transition(
    audio_hash: str,
    event: str,
    *,
    value: str | None = None,
    can_edit: bool,
) -> SongUiState:
    view_key, mode_key = state_keys(audio_hash)
    current = SongUiState(
        view=str(st.session_state.get(view_key, VIEW_LYRICS)),
        mode=str(st.session_state.get(mode_key, MODE_VIEW)),
    )
    next_state = transition(
        current,
        event,
        value=value,
        can_edit=can_edit,
    )
    st.session_state[view_key] = next_state.view
    st.session_state[mode_key] = next_state.mode
    return next_state


def on_view_widget_change(audio_hash: str, can_edit: bool) -> None:
    """Streamlit callback executed before widgets are instantiated again."""
    view_key, _mode_key = state_keys(audio_hash)
    apply_session_transition(
        audio_hash,
        EVENT_SELECT_VIEW,
        value=str(st.session_state.get(view_key, VIEW_LYRICS)),
        can_edit=can_edit,
    )


def mode_label(value: str) -> str:
    return "✏️ Éditer" if value == MODE_EDIT else "👁 Vue"
