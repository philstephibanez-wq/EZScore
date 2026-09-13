"""Back-office harmonic comparison player for EZScore."""

from __future__ import annotations

import re
import streamlit as st

from ezscore.midi import (
    build_chord_midi_events,
    build_midi_file,
    render_editor_midi_player,
)
from ezscore.player import cover_payload
from ezscore.guitar import (
    choices as guitar_choices,
    get_voicing,
    load_show_diagrams,
    load_voicings,
    save_show_diagrams,
    save_voicing,
    svg as guitar_svg,
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
    artist: str,
    cover_path,
    audio_hash: str,
    instruments: dict[str, int],
    resultat,
):
    """Render the MP3+MIDI verification tool inside edition views only."""
    with st.container(border=True):
        st.markdown("#### 🎧 Contrôle grille ↔ MP3")
        identity_cover = cover_payload(cover_path)
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

        from ezscore.transcription import extraire_mots
        lyrics_words = extraire_mots(resultat)

        chord_symbols = []
        for event in events:
            if event.get("kind") != "note_on":
                continue
            symbol = str(event.get("chord", "") or "").strip()
            if symbol and symbol not in chord_symbols:
                chord_symbols.append(symbol)

        saved_voicings = load_voicings(audio_hash)
        show_diagrams_saved = load_show_diagrams(audio_hash)
        diagram_map = {}

        with st.expander("🎸 Diagrammes guitare (optionnel)", expanded=False):
            show_diagrams = st.toggle(
                "Afficher le diagramme de l’accord courant dans le bandeau",
                value=show_diagrams_saved,
                key=f"show_guitar_diagrams_{audio_hash[:12]}",
            )
            if show_diagrams != show_diagrams_saved:
                save_show_diagrams(audio_hash, show_diagrams)

            supported = [
                symbol for symbol in chord_symbols
                if guitar_choices(symbol)
            ]

            if not supported:
                st.caption(
                    "Aucun voicing prédéfini pour les accords de ce morceau. "
                    "Le catalogue sera enrichi progressivement."
                )
            else:
                st.caption(
                    "Le symbole harmonique ne change pas : choisissez uniquement "
                    "la position guitare (ouverte, barrée, simplifiée…)."
                )
                columns = st.columns(3)
                for index, symbol in enumerate(supported):
                    available = guitar_choices(symbol)
                    names = [item.name for item in available]
                    saved_name = saved_voicings.get(symbol)
                    selected_index = names.index(saved_name) if saved_name in names else 0

                    with columns[index % 3]:
                        selected_name = st.selectbox(
                            f"{symbol} — position",
                            names,
                            index=selected_index,
                            key=f"voicing_{audio_hash[:10]}_{symbol}_{index}",
                        )
                        if selected_name != saved_name:
                            save_voicing(audio_hash, symbol, selected_name)

                        selected = get_voicing(symbol, selected_name)
                        if selected is not None:
                            preview_svg = guitar_svg(
                                symbol,
                                selected,
                                width=132,
                                height=168,
                            )
                            st.markdown(
                                '<div style="text-align:center">' + preview_svg + '</div>',
                                unsafe_allow_html=True,
                            )
                            diagram_map[symbol] = guitar_svg(
                                symbol,
                                selected,
                                width=110,
                                height=140,
                            )

        show_diagrams = st.session_state.get(
            f"show_guitar_diagrams_{audio_hash[:12]}",
            show_diagrams_saved,
        )

        render_editor_midi_player(
            audio_bytes=audio_bytes,
            extension=extension,
            midi_events=events,
            instrument_label=instrument_label,
            program=program,
            lyrics_words=lyrics_words,
            chord_diagrams=diagram_map,
            show_diagrams=bool(show_diagrams),
            cover=identity_cover,
            title=title,
            artist=artist,
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
