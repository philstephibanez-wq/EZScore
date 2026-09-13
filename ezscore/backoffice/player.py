"""Back-office harmonic comparison player for EZScore."""

from __future__ import annotations

import re
import streamlit as st

from ezscore.midi import (
    build_chord_midi_events,
    build_midi_file,
    render_editor_midi_player,
)


def render_editor_comparison_player(
    *,
    audio_bytes: bytes,
    extension: str,
    beats,
    signature: str,
    beats_per_measure: int,
    tempo: float,
    title: str,
    audio_hash: str,
    instruments: dict[str, int],
):
    """Render the MP3+MIDI verification tool inside edition views only."""
    with st.container(border=True):
        st.markdown("#### 🎧 Contrôle grille ↔ MP3")
        st.caption(
            "Back-office : le MP3 est l’horloge maître. Le MIDI rejoue la grille "
            "effective, y compris les corrections manuelles, afin de comparer à l’oreille."
        )

        instrument_label = st.selectbox(
            "Instrument de contrôle",
            list(instruments.keys()),
            index=0,
            key=f"editor_midi_instrument_{audio_hash[:12]}",
        )
        program = int(instruments[instrument_label])
        strum_ms = 12.0 if program == 27 else 0.0

        events = build_chord_midi_events(
            beats=beats,
            signature=signature,
            beats_per_measure=beats_per_measure,
            program=program,
            gate_ratio=0.48,
            strum_ms=strum_ms,
        )

        render_editor_midi_player(
            audio_bytes=audio_bytes,
            extension=extension,
            midi_events=events,
            instrument_label=instrument_label,
            program=program,
            key=f"editor_midi_player_{audio_hash[:12]}_{program}",
        )

        midi_bytes = build_midi_file(
            beats=beats,
            tempo=tempo,
            signature=signature,
            beats_per_measure=beats_per_measure,
            program=program,
            gate_ratio=0.48,
            strum_ms=strum_ms,
        )

        safe = (
            re.sub(r"[^A-Za-z0-9._-]+", "_", str(title or "EZScore")).strip("_")
            or "EZScore"
        )
        st.download_button(
            "⬇ Télécharger le MIDI des accords",
            data=midi_bytes,
            file_name=f"{safe}_accords.mid",
            mime="audio/midi",
            key=f"editor_midi_download_{audio_hash[:12]}",
        )
