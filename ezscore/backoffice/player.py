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
from ezscore.player.timeline import build_measure_timeline
from ezscore.guitar import (
    choices as guitar_choices,
    get_voicing,
    load_show_diagrams,
    load_voicings,
    save_show_diagrams,
    save_voicing,
    svg as guitar_svg,
)
from ezscore.notation import accord_forme_capo, formatter_mesure_signature
from ezscore.persistence import (
    _lyric_block_key,
    _persist_structure_draft,
    _source_words_for_interval,
    load_lyric_block_edits,
    load_structure_blocks,
    resolve_lyric_block_edit,
    save_lyric_block_edits_snapshot,
    save_measure_edit,
)


def _editor_measure_windows(beats, beats_per_measure: int):
    """Return strict, deterministic measure windows from the effective beat list."""
    bpm = int(beats_per_measure)
    if bpm <= 0:
        raise ValueError("beats_per_measure doit être strictement positif.")

    rows = list(beats or [])
    windows = []
    for start in range(0, len(rows), bpm):
        group = rows[start:start + bpm]
        if not group:
            continue

        first = group[0]
        last = group[-1]
        t0 = float(first.get("temps", first.get("start", 0.0)) or 0.0)
        t1 = float(last.get("fin", last.get("end", t0)) or t0)

        if t1 < t0:
            raise ValueError(
                f"Timeline invalide pour la mesure {len(windows) + 1}: fin < début."
            )

        windows.append(
            {
                "measure_no": len(windows) + 1,
                "time_start": t0,
                "time_end": t1,
                "beats": group,
            }
        )
    return windows


def _editor_validate_anchor_rows(blocks, edited_rows, total_measures: int):
    """
    Convert section-start anchors to the legacy contiguous block representation.

    No guessed value, no clamping and no hidden fallback:
    every invalid anchor rejects the whole save.
    """
    if not blocks:
        return False, [], "Aucun bloc structurel persistant à éditer."

    if len(edited_rows) != len(blocks):
        return False, [], "Le nombre d’ancres ne correspond plus aux blocs."

    total = int(total_measures)
    if total <= 0:
        return False, [], "Aucune mesure exploitable."

    starts = []
    labels = []

    for i, row in enumerate(edited_rows):
        label = str(row.get("Section", "") or "").strip()
        if not label:
            return False, [], f"Ancre {i + 1}: le nom de section est obligatoire."

        raw_start = row.get("Ancre mesure")
        try:
            start = int(raw_start)
        except (TypeError, ValueError):
            return False, [], f"Ancre {i + 1}: numéro de mesure invalide."

        if start < 1 or start > total:
            return (
                False,
                [],
                f"Ancre {i + 1}: mesure {start} hors plage 1–{total}.",
            )

        starts.append(start)
        labels.append(label)

    if starts[0] != 1:
        return False, [], "La première ancre doit rester sur la mesure 1."

    if any(b <= a for a, b in zip(starts, starts[1:])):
        return False, [], "Les ancres doivent être strictement croissantes."

    draft = []
    for i, block in enumerate(blocks):
        copied = dict(block)
        copied["order_index"] = i
        copied["custom_label"] = labels[i]
        copied["measure_start"] = starts[i]
        copied["measure_end"] = (
            starts[i + 1] - 1
            if i + 1 < len(starts)
            else total
        )
        if int(copied["measure_end"]) < int(copied["measure_start"]):
            return False, [], f"Section {labels[i]}: intervalle vide."
        draft.append(copied)

    return True, draft, ""


def _editor_interval_from_draft(block, measure_windows):
    m0 = int(block["measure_start"])
    m1 = int(block["measure_end"])

    if m0 < 1 or m1 < m0 or m1 > len(measure_windows):
        raise ValueError(
            f"Bornes de section invalides: mesures {m0}–{m1}."
        )

    first = measure_windows[m0 - 1]
    last = measure_windows[m1 - 1]
    return (
        float(first["time_start"]),
        float(last["time_end"]) + 0.001,
    )


def _editor_validate_chord_value(value, row_no: int):
    chord = str(value or "").strip()
    if not chord:
        return False, "", f"Ligne accord {row_no}: valeur vide interdite."

    if any(ch.isspace() for ch in chord):
        return (
            False,
            "",
            f"Ligne accord {row_no}: aucun espace n’est autorisé dans un symbole.",
        )

    if len(chord) > 24:
        return (
            False,
            "",
            f"Ligne accord {row_no}: symbole trop long ({len(chord)} caractères).",
        )

    return True, chord, ""


def _render_partition_editor(
    *,
    audio_hash: str,
    beats,
    beats_per_measure: int,
    signature: str,
    resultat,
):
    """
    Editorial-only editor.

    Invariants:
    - audio/STEM data is never touched;
    - beat timestamps are never edited;
    - detected analysis is never recomputed;
    - section anchors only change presentation structure;
    - lyrics only replace text inside an existing time interval;
    - chord edits are persisted through the existing measure overlay layer.
    """
    measure_windows = _editor_measure_windows(beats, beats_per_measure)
    if not measure_windows:
        st.error("Éditeur indisponible: aucune mesure effective.")
        return

    structure_blocks = load_structure_blocks(audio_hash)
    if not structure_blocks:
        st.error(
            "Éditeur indisponible: aucune structure persistante. "
            "Aucune structure n’est créée automatiquement."
        )
        return

    st.markdown("#### ✏️ Édition paroles · accords · ancres")
    st.caption(
        "Couche éditoriale uniquement : timestamps, audio, STEMs et analyse "
        "technique restent inchangés."
    )

    tabs = st.tabs(["⚑ Ancres + paroles", "♬ Accords beat par beat"])

    with tabs[0]:
        anchor_rows = []
        for block in structure_blocks:
            anchor_rows.append(
                {
                    "Section": (
                        str(block.get("custom_label", "") or "").strip()
                        or str(block.get("cluster", "") or "").strip()
                    ),
                    "Ancre mesure": int(block["measure_start"]),
                }
            )

        revision_key = f"editor_anchor_revision_{audio_hash[:12]}"
        revision = int(st.session_state.get(revision_key, 0))

        edited_anchor_df = st.data_editor(
            anchor_rows,
            width="stretch",
            hide_index=True,
            num_rows="fixed",
            column_config={
                "Section": st.column_config.TextColumn(
                    "Section",
                    required=True,
                    width="large",
                ),
                "Ancre mesure": st.column_config.NumberColumn(
                    "Ancre mesure",
                    min_value=1,
                    max_value=len(measure_windows),
                    step=1,
                    required=True,
                    width="small",
                ),
            },
            key=f"editor_anchor_table_{audio_hash[:12]}_{revision}",
        )

        edited_anchor_rows = (
            edited_anchor_df.to_dict("records")
            if hasattr(edited_anchor_df, "to_dict")
            else list(edited_anchor_df)
        )

        ok_anchors, draft_blocks, anchor_error = _editor_validate_anchor_rows(
            structure_blocks,
            edited_anchor_rows,
            len(measure_windows),
        )

        if not ok_anchors:
            st.error(anchor_error)
            return

        lyric_edits = load_lyric_block_edits(audio_hash)
        lyric_items = []

        st.caption(
            "Les paroles utilisent les bornes des ancres visibles ci-dessus. "
            "Les retours à la ligne saisis sont conservés."
        )

        for index, block in enumerate(draft_blocks):
            t0, t1 = _editor_interval_from_draft(
                block,
                measure_windows,
            )
            source_words = _source_words_for_interval(resultat, t0, t1)
            original = " ".join(
                str(word.get("text", "") or "").strip()
                for word in source_words
                if str(word.get("text", "") or "").strip()
            ).strip()

            existing = resolve_lyric_block_edit(
                lyric_edits,
                t0,
                t1,
            )
            current = (
                str(existing.get("corrected_text", "") or "")
                if existing
                else original
            )

            block_id = int(block.get("block_id", index + 1) or (index + 1))
            label = str(block.get("custom_label", "") or "").strip()
            widget_key = (
                f"editor_lyrics_{audio_hash[:10]}_block_{block_id}"
            )

            # Stable widget identity by persistent block_id.
            # We never rewrite an instantiated widget during the same rerun.
            if widget_key not in st.session_state:
                st.session_state[widget_key] = current

            st.markdown(
                f"**{label}** · mesures "
                f"{int(block['measure_start'])}–{int(block['measure_end'])}"
            )
            edited_text = st.text_area(
                f"Paroles {label}",
                height=105,
                key=widget_key,
                label_visibility="collapsed",
                placeholder="[instrumental]",
            )

            lyric_items.append(
                {
                    "block_id": block_id,
                    "widget_key": widget_key,
                    "block_key": _lyric_block_key(t0, t1),
                    "original_text": original,
                    "edited_text": edited_text,
                    "time_start": t0,
                    "time_end": t1,
                }
            )

        if st.button(
            "✅ Valider ancres + paroles",
            type="primary",
            key=f"editor_save_anchors_lyrics_{audio_hash[:12]}",
            width="stretch",
        ):
            # Revalidate immediately before any write.
            ok_anchors, draft_blocks, anchor_error = _editor_validate_anchor_rows(
                structure_blocks,
                edited_anchor_rows,
                len(measure_windows),
            )
            if not ok_anchors:
                st.error(anchor_error)
                return

            # Rebuild lyric intervals from the exact draft being persisted.
            validated_lyrics = []
            by_block_id = {
                int(item["block_id"]): item
                for item in lyric_items
            }

            for index, block in enumerate(draft_blocks):
                block_id = int(
                    block.get("block_id", index + 1) or (index + 1)
                )
                if block_id not in by_block_id:
                    st.error(
                        f"Bloc {block_id}: éditeur de paroles absent. "
                        "Aucune donnée n’a été enregistrée."
                    )
                    return

                source_item = by_block_id[block_id]
                t0, t1 = _editor_interval_from_draft(
                    block,
                    measure_windows,
                )
                validated_lyrics.append(
                    {
                        **source_item,
                        "block_key": _lyric_block_key(t0, t1),
                        "time_start": t0,
                        "time_end": t1,
                    }
                )

            saved, message = _persist_structure_draft(
                audio_hash,
                draft_blocks,
                len(measure_windows),
            )
            if not saved:
                st.error(message)
                return

            save_lyric_block_edits_snapshot(
                audio_hash,
                validated_lyrics,
            )

            st.session_state[revision_key] = revision + 1
            for item in validated_lyrics:
                st.session_state.pop(item["widget_key"], None)

            st.success("Ancres et paroles enregistrées.")
            st.rerun()

    with tabs[1]:
        chord_rows = []
        for measure in measure_windows:
            measure_no = int(measure["measure_no"])
            for local_index, beat in enumerate(measure["beats"]):
                time_value = float(
                    beat.get("temps", beat.get("start", 0.0)) or 0.0
                )
                chord_rows.append(
                    {
                        "Mesure": measure_no,
                        "Beat": local_index + 1,
                        "Temps": round(time_value, 3),
                        "Accord": str(
                            beat.get("accord", "") or ""
                        ).strip(),
                    }
                )

        chord_df = st.data_editor(
            chord_rows,
            width="stretch",
            hide_index=True,
            num_rows="fixed",
            disabled=["Mesure", "Beat", "Temps"],
            column_config={
                "Mesure": st.column_config.NumberColumn(
                    "Mesure",
                    width="small",
                ),
                "Beat": st.column_config.NumberColumn(
                    "Beat",
                    width="small",
                ),
                "Temps": st.column_config.NumberColumn(
                    "Temps (s)",
                    format="%.3f",
                    width="small",
                ),
                "Accord": st.column_config.TextColumn(
                    "Accord réel",
                    required=True,
                    width="medium",
                    help=(
                        "Symbole réel (ex. Gm, A7, D/F#), '-' pour tenue, "
                        "'.' pour beat non joué. Aucun timestamp n’est modifiable."
                    ),
                ),
            },
            key=f"editor_chords_{audio_hash[:12]}",
        )

        edited_chord_rows = (
            chord_df.to_dict("records")
            if hasattr(chord_df, "to_dict")
            else list(chord_df)
        )

        if st.button(
            "✅ Valider les accords",
            type="primary",
            key=f"editor_save_chords_{audio_hash[:12]}",
            width="stretch",
        ):
            if len(edited_chord_rows) != len(chord_rows):
                st.error(
                    "Le nombre de beats a changé. "
                    "Aucun accord n’a été enregistré."
                )
                return

            validated = []
            errors = []

            for row_no, row in enumerate(edited_chord_rows, start=1):
                ok, chord, error = _editor_validate_chord_value(
                    row.get("Accord"),
                    row_no,
                )
                if not ok:
                    errors.append(error)
                    continue

                validated.append(
                    {
                        "measure_no": int(row["Mesure"]),
                        "beat_no": int(row["Beat"]),
                        "chord": chord,
                    }
                )

            if errors:
                for error in errors:
                    st.error(error)
                return

            grouped = {}
            for row in validated:
                grouped.setdefault(row["measure_no"], {})[
                    row["beat_no"]
                ] = row["chord"]

            for measure_no, beat_map in grouped.items():
                if len(beat_map) != int(beats_per_measure):
                    # Only the final incomplete technical measure may be shorter.
                    source_measure = measure_windows[measure_no - 1]
                    expected = len(source_measure["beats"])
                    if len(beat_map) != expected:
                        st.error(
                            f"Mesure {measure_no}: {len(beat_map)} beats reçus, "
                            f"{expected} attendus. Aucun accord n’a été enregistré."
                        )
                        return

            # All validation is complete before the first write.
            for measure_no, beat_map in grouped.items():
                source_measure = measure_windows[measure_no - 1]
                expected = len(source_measure["beats"])
                symbols = [
                    beat_map[index]
                    for index in range(1, expected + 1)
                ]

                while len(symbols) < int(beats_per_measure):
                    symbols.append(".")

                notation_real = formatter_mesure_signature(
                    symbols,
                    signature,
                    fermata=False,
                )
                save_measure_edit(
                    audio_hash,
                    measure_no,
                    notation_real,
                )

            st.success(
                "Accords enregistrés dans la couche éditoriale. "
                "La timeline technique est inchangée."
            )
            st.rerun()


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
    lyrics_words=None,
    capo: int = 0,
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

        lyrics_words = list(lyrics_words or [])

        display_beats = []
        chord_symbols = []
        current_real = ""

        for beat in beats or []:
            copied = dict(beat)
            raw = str(beat.get("accord", "") or "").strip()

            if raw == ".":
                current_real = ""
                copied["accord"] = "."
            elif raw == "-":
                copied["accord"] = "-"
            elif raw:
                current_real = raw
                copied["accord"] = accord_forme_capo(raw, capo)
            else:
                copied["accord"] = raw

            display_beats.append(copied)

            if current_real:
                display_symbol = accord_forme_capo(current_real, capo)
                if display_symbol and display_symbol not in chord_symbols:
                    chord_symbols.append(display_symbol)

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

        player_measures = build_measure_timeline(
            beats=display_beats,
            lyrics_words=lyrics_words,
            beats_per_measure=beats_per_measure,
            chord_diagrams=diagram_map,
        )

        render_editor_midi_player(
            audio_bytes=audio_bytes,
            extension=extension,
            midi_events=events,
            instrument_label=instrument_label,
            program=program,
            lyrics_words=lyrics_words,
            player_measures=player_measures,
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

        st.markdown("---")
        _render_partition_editor(
            audio_hash=audio_hash,
            beats=beats,
            beats_per_measure=beats_per_measure,
            signature=signature,
            resultat=resultat,
        )
