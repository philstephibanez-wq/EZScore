"""Application shell: header, profile sidebar and contextual navigation."""

from __future__ import annotations

import html
import json
import sqlite3
from difflib import SequenceMatcher
from pathlib import Path

import streamlit as st

from ezscore.auth import allowed, current_user, logout
from ezscore.auth.storage import avatar_value
import ezscore.persistence as _persistence
from ezscore.persistence import load_latest_persisted_analysis
from ezscore.midi import (
    MIDI_INSTRUMENTS as _MIDI_INSTRUMENTS,
    build_chord_midi_events as _build_chord_midi_events,
    build_midi_file as _build_midi_file,
)
import ezscore.transcription as _transcription
from ezscore.notation import formatter_mesure_signature as _formatter_mesure_signature
from ezscore.midi.analysis_player import render_analysis_midi_player as _render_analysis_midi_player
from ezscore.analysis.vocal import (
    analyze_vocal_pitch as _analyze_vocal_pitch,
    VOCAL_MIDI_INSTRUMENTS as _VOCAL_MIDI_INSTRUMENTS,
    build_vocal_midi_events as _build_vocal_midi_events,
    build_vocal_midi_file as _build_vocal_midi_file,
    demucs_available as _vocal_demucs_available,
    load_vocal_analysis as _load_vocal_analysis,
    refine_sections_with_vocal as _refine_sections_with_vocal,
)
from ezscore.analysis.stems import (
    cached_stem_paths as _cached_stem_paths,
    demucs_available as _stems_demucs_available,
    ensure_stems as _ensure_stems,
    load_stem_manifest as _load_stem_manifest,
    stems_cache_complete as _stems_cache_complete,
)
from ezscore.diagnostics.perf import (
    install_runtime_probes,
    perf_event,
    perf_span,
    render_perf_log_sidebar,
)

install_runtime_probes()


_SCROLL_TO_LYRICS_JS = r"""
export default function(component) {
    const { data } = component;
    const targetId = data && data.target_id;
    if (!targetId) return;

    const attempt = (remaining) => {
        const target = document.getElementById(targetId);
        if (target) {
            target.scrollIntoView({
                behavior: "smooth",
                block: "start",
                inline: "nearest"
            });
            return;
        }
        if (remaining > 0) {
            window.setTimeout(() => attempt(remaining - 1), 40);
        }
    };

    requestAnimationFrame(() => attempt(20));
}
"""

_SCROLL_TO_LYRICS = st.components.v2.component(
    "ezscore_scroll_to_lyrics_block",
    js=_SCROLL_TO_LYRICS_JS,
)




APP_DIR = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# R12.1 — STEM_LAB -> historical editor compatibility bridge.
# ---------------------------------------------------------------------------

_ORIGINAL_LOAD_LATEST_PERSISTED_ANALYSIS = load_latest_persisted_analysis


def _stem_lab_cache_dir(audio_hash: str) -> Path:
    return APP_DIR / "data" / "analysis" / "stem_lab" / str(audio_hash)


def _read_required_json(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(str(path))
    return __import__("json").loads(path.read_text(encoding="utf-8"))


def _stem_lab_editor_bridge(audio_hash: str) -> dict | None:
    """Expose STEM_LAB data to the mature Blocs/Paroles/Grille editors."""
    active_hash = str(audio_hash or "").strip()
    if not active_hash:
        return None

    work_mode = str(
        st.session_state.get(f"ez_work_mode_{active_hash[:12]}", "") or ""
    )
    if work_mode not in {"Édition", "Player"}:
        return None

    cache_dir = _stem_lab_cache_dir(active_hash)
    structure_path = cache_dir / "structure_analysis.json"
    speech_path = cache_dir / "whisper_original_small.json"

    if not structure_path.is_file() or not speech_path.is_file():
        return None

    structure = _read_required_json(structure_path)
    speech = _read_required_json(speech_path)

    beat_timeline = list(structure.get("beat_timeline", []) or [])
    source_measures = list(structure.get("measures", []) or [])
    source_words = list(speech.get("words", []) or [])

    if len(beat_timeline) < 2:
        raise RuntimeError(
            "Mode Édition impossible : beat_timeline STEM_LAB absente ou incomplète."
        )
    if not source_measures:
        raise RuntimeError(
            "Mode Édition impossible : aucune mesure STEM_LAB disponible."
        )
    if not source_words:
        raise RuntimeError(
            "Mode Édition impossible : aucun mot Whisper horodaté disponible."
        )

    tempo = float(structure.get("tempo", 0.0) or 0.0)
    if tempo <= 1.0:
        raise RuntimeError("Mode Édition impossible : tempo STEM_LAB invalide.")

    beats_per_measure = max(
        1,
        int(structure.get("beats_per_bar", 4) or 4),
    )
    signature = str(
        structure.get("signature", "") or (
            "6/8" if beats_per_measure == 6 else f"{beats_per_measure}/4"
        )
    )
    median_interval = 60.0 / tempo

    beats = []
    for index, item in enumerate(beat_timeline):
        start = float(item.get("time", 0.0) or 0.0)
        if index + 1 < len(beat_timeline):
            end = float(beat_timeline[index + 1].get("time", start))
        else:
            end = start + median_interval

        chord = str(item.get("chord", "N") or "N").strip()
        if chord in {"", "N"}:
            chord = "."

        beats.append({
            "index": int(index),
            "temps": start,
            "fin": max(start + 0.001, end),
            "intervalle": max(0.001, end - start),
            "accord": chord,
            "silence": chord == ".",
            "rms_ratio": 0.0 if chord == "." else 1.0,
            "chroma_ratio": 0.0 if chord == "." else 1.0,
        })

    measures = []
    for index, measure in enumerate(source_measures):
        chords = [
            "." if str(x or "N").strip() in {"", "N"} else str(x).strip()
            for x in list(measure.get("beat_chords", []) or [])
        ]
        while len(chords) < beats_per_measure:
            chords.append(".")
        chords = chords[:beats_per_measure]

        measures.append({
            "numero": int(measure.get("measure", index + 1) or index + 1),
            "debut": float(measure.get("time_start", 0.0) or 0.0),
            "fin": float(measure.get("time_end", 0.0) or 0.0),
            "accords": chords,
            "notation": _formatter_mesure_signature(
                chords,
                signature,
                fermata=False,
            ),
            "fermata": False,
        })

    whisper_words = []
    for word in source_words:
        text = str(word.get("text", "") or "").strip()
        start = float(word.get("start", 0.0) or 0.0)
        end = float(word.get("end", start) or start)
        if text and end > start:
            whisper_words.append({
                "word": text,
                "start": start,
                "end": end,
            })

    if not whisper_words:
        raise RuntimeError(
            "Mode Édition impossible : aucun mot Whisper valide après adaptation."
        )

    result = {
        "language": str(speech.get("language", "") or ""),
        "text": str(speech.get("text", "") or "").strip(),
        "segments": [{
            "start": float(whisper_words[0]["start"]),
            "end": float(whisper_words[-1]["end"]),
            "text": str(speech.get("text", "") or "").strip(),
            "words": whisper_words,
        }],
        "source": "stem_lab_whisper_small",
    }

    music = {
        "sr": 22050,
        "tempo": tempo,
        "tempo_brut": tempo,
        "beats": beats,
        "mesures": measures,
        "median_interval": float(median_interval),
        "tonalite": {},
        "tonalite_nom": "?",
        "accords_dominants": [],
        "vocabulaire": [],
        "alternance_active": False,
        "couverture_pair": 0.0,
        "taux_alternance_pair": 0.0,
        "signature": signature,
        "signature_mode": "STEM_LAB",
        "signature_auto": {},
        "beats_par_mesure": int(beats_per_measure),
        "analyse_sr": 22050,
        "hop_length": 512,
        "silence_rms_ratio": 0.22,
        "silence_chroma_ratio": 0.18,
        "poids_fondamentale": 0.10,
        "poids_accompagnement": 0.90,
        "harmonic_source_mix": {
            "other": 0.90,
            "bass_root_support": 0.10,
        },
        "performance": {
            "source": "stem_lab_bridge",
            "audio_reanalysis": False,
        },
    }

    parameters = {
        "signature_mode": signature,
        "analyse_sr": 22050,
        "hop_length": 512,
        "silence_rms_ratio": 0.22,
        "silence_chroma_ratio": 0.18,
        "poids_fondamentale": 0.10,
        "fermata_enabled": False,
        "fermata_gap_ratio": 1.85,
        "whisper_device": "stem_lab",
        "source": "stem_lab_bridge",
    }

    existing_blocks = _persistence.load_structure_blocks(active_hash)
    if not existing_blocks:
        visual_blocks = list(structure.get("visual_blocks", []) or [])
        detected_sections = []
        for index, block in enumerate(visual_blocks):
            m0 = int(block.get("measure_start", 1) or 1)
            m1 = int(block.get("measure_end", m0) or m0)
            detected_sections.append({
                "measure_start": m0,
                "measure_end": m1,
                "cluster": str(
                    block.get("cluster", chr(ord("A") + (index % 26)))
                ),
                "custom_label": str(block.get("custom_label", "") or "").strip(),
            })

        _persistence.ensure_structure_blocks(
            audio_hash=active_hash,
            detected_sections=detected_sections,
            total_measures=len(measures),
        )

    return {
        "analysis_key": "stem_lab_editor_bridge_v1",
        "parameters": parameters,
        "musique": music,
        "resultat": result,
        "updated_at": "",
        "source": "stem_lab_bridge",
    }


def load_latest_persisted_analysis(audio_hash):
    """Load historical analysis, or adapt STEM_LAB data for Edit/Player mode."""
    persisted = _ORIGINAL_LOAD_LATEST_PERSISTED_ANALYSIS(audio_hash)
    if persisted is not None:
        return persisted
    return _stem_lab_editor_bridge(str(audio_hash or ""))


_persistence.load_latest_persisted_analysis = load_latest_persisted_analysis



# ---------------------------------------------------------------------------
# R30/R33 runtime compatibility:
# - do NOT recompute R33 when visual blocks are already persisted;
# - restore the MP3 + MIDI synchronized player in Analyse;
# - keep all timings in the file-based performance log.
# ---------------------------------------------------------------------------

_ORIGINAL_DETECTER_SECTIONS = _transcription.detecter_sections_structurelles


def _measure_pattern(measure):
    return str(measure.get("notation", "") or "").strip()


def _ezscore_detecter_sections_structurelles(
    mesures,
    resultat,
    block_measures=4,
    similarity_threshold=0.66,
):
    """Reuse persisted visual blocks instead of rerunning R33 on every rerun.

    A reset of structure_blocks still works as intended: once the persisted
    rows are deleted, the original R33 engine runs once and ensure_structure_blocks
    persists the new proposal.
    """
    active_hash = str(st.session_state.get("active_song_hash", "") or "").strip()

    if active_hash:
        try:
            existing = _persistence.load_structure_blocks(active_hash)
        except Exception as exc:
            perf_event(
                "structure.persisted.lookup",
                status="error",
                error_type=type(exc).__name__,
                error=str(exc),
            )
            existing = []

        if existing:
            words = _transcription.extraire_mots(resultat)
            by_number = {
                int(m.get("numero", 0) or 0): m
                for m in (mesures or [])
            }

            sections = []
            ordered = sorted(
                [dict(block) for block in existing],
                key=lambda block: int(block.get("order_index", 0) or 0),
            )

            for index, block in enumerate(ordered):
                m0 = int(block.get("measure_start", 1) or 1)
                m1 = int(block.get("measure_end", m0) or m0)

                group = [
                    by_number[num]
                    for num in range(m0, m1 + 1)
                    if num in by_number
                ]
                if not group:
                    continue

                sections.append({
                    "index": index,
                    "measure_start": m0,
                    "measure_end": m1,
                    "time_start": float(group[0].get("debut", 0.0) or 0.0),
                    "time_end": float(
                        group[-1].get(
                            "fin",
                            group[-1].get("debut", 0.0),
                        )
                        or 0.0
                    ) + 0.001,
                    "cluster": str(
                        block.get("cluster", chr(ord("A") + (index % 26)))
                    ),
                    "custom_label": str(
                        block.get("custom_label", "") or ""
                    ).strip(),
                    "type": str(
                        block.get("custom_label", "") or ""
                    ).strip() or (
                        "Bloc "
                        + str(
                            block.get(
                                "cluster",
                                chr(ord("A") + (index % 26)),
                            )
                        )
                    ),
                    "confidence": 1.0,
                    "cluster_repeats": 1,
                    "lyric_repeat": 0.0,
                    "harmonic_repeat": 1.0,
                    "measure_patterns": [
                        _measure_pattern(measure)
                        for measure in group
                    ],
                    "visual_only": True,
                })

            # Preserve vocal pre-roll / post-roll without moving timestamps.
            if sections and words:
                sections[0]["time_start"] = min(
                    float(sections[0]["time_start"]),
                    min(float(word.get("start", 0.0)) for word in words),
                )
                sections[-1]["time_end"] = max(
                    float(sections[-1]["time_end"]),
                    max(
                        float(word.get("end", word.get("start", 0.0)))
                        for word in words
                    ),
                )

            perf_event(
                "structure.persisted.reuse",
                blocks=len(sections),
                measures=len(mesures or []),
                threshold=float(similarity_threshold),
            )
            return sections

    # No persisted structure: this is the only case where R33 is allowed to
    # perform the expensive intelligent analysis.
    with perf_span(
        "structure.r33.compute",
        measures=len(mesures or []),
        threshold=float(similarity_threshold),
    ):
        sections = _ORIGINAL_DETECTER_SECTIONS(
            mesures=mesures,
            resultat=resultat,
            block_measures=block_measures,
            similarity_threshold=similarity_threshold,
        )

    # Experimental branch only: vocal melody is a secondary cue. With no
    # persisted vocal analysis this is a strict no-op and R33 stays unchanged.
    vocal_analysis = _load_vocal_analysis(active_hash) if active_hash else None
    vocal_notes = list((vocal_analysis or {}).get("notes", []) or [])

    if vocal_notes:
        with perf_span(
            "structure.vocal.refine",
            notes=len(vocal_notes),
            sections=len(sections or []),
        ):
            sections, vocal_info = _refine_sections_with_vocal(
                sections=sections,
                mesures=mesures,
                vocal_notes=vocal_notes,
    )
        perf_event(
            "structure.vocal.refine.result",
            used=bool(vocal_info.get("used")),
            moved=int(vocal_info.get("moved", 0) or 0),
            moves=vocal_info.get("moves", []),
        )

    return sections


# EZScore.py imports this symbol only after app_shell has loaded.
_transcription.detecter_sections_structurelles = (
    _ezscore_detecter_sections_structurelles
)


@st.cache_data(show_spinner=False)
def _analysis_player_audio_bytes(path_str, mtime_ns, size):
    """Read archived audio once per physical file revision."""
    return Path(path_str).read_bytes()


def _analysis_player_song(active_hash):
    try:
        for item in _persistence.list_song_catalog(sort_by="title"):
            if str(item.get("audio_hash", "")) == active_hash:
                return item
    except Exception as exc:
        perf_event(
            "analysis.player.song_lookup",
            status="error",
            error_type=type(exc).__name__,
            error=str(exc),
        )
    return {}


def _analysis_player_audio(active_hash, song):
    filename = str(song.get("original_filename", "") or "").strip()
    audio_dir = getattr(_persistence, "AUDIO_DIR", None)

    if filename and audio_dir is not None:
        candidate = Path(audio_dir) / Path(filename).name
        if candidate.is_file():
            stat = candidate.stat()
            return (
                _analysis_player_audio_bytes(
                    str(candidate),
                    int(stat.st_mtime_ns),
                    int(stat.st_size),
                ),
                candidate.suffix.lower() or ".mp3",
            )

    # Compatibility fallback for archives with an old physical filename.
    try:
        candidate = _persistence.find_persisted_audio(active_hash)
    except Exception:
        candidate = None

    if candidate is None:
        return None, ".mp3"

    candidate = Path(candidate)
    stat = candidate.stat()
    return (
        _analysis_player_audio_bytes(
            str(candidate),
            int(stat.st_mtime_ns),
            int(stat.st_size),
        ),
        candidate.suffix.lower() or ".mp3",
    )


def _analysis_instrument_label(program):
    for label, value in _MIDI_INSTRUMENTS.items():
        if int(value) == int(program):
            return str(label)
    return f"Programme MIDI {int(program)}"



def _safe_midi_filename(value, suffix):
    stem = "".join(
        ch if ch.isalnum() or ch in "._-" else "_"
        for ch in str(value or "EZScore")
    ).strip("_") or "EZScore"
    return f"{stem}_{suffix}.mid"



def _render_stem_pipeline_analysis(
    *,
    active_hash,
    audio_bytes,
    extension,
):
    """Visible, non-destructive checkpoint for the new 4-stem workflow."""
    st.markdown("##### 🧩 Analyse STEM — nouveau pipeline")
    st.caption(
        "Audio original = horloge maître. Paroles = original + Whisper small. "
        "Demucs prépare vocals / drums / bass / other."
    )

    available = _stems_demucs_available()
    complete = _stems_cache_complete(active_hash)
    paths = _cached_stem_paths(active_hash)
    manifest = _load_stem_manifest(active_hash) if complete else None

    if not available:
        st.warning(
            "Demucs n'est pas disponible dans cet environnement. "
            "L'analyse EZScore historique reste active et inchangée."
        )
        return

    if complete:
        st.success(
            "4 stems en cache · htdemucs · timebase de l'audio original."
        )
    else:
        st.info(
            "Pipeline STEM disponible. Les quatre stems ne sont pas encore "
            "préparés pour ce morceau."
        )

    roles = [
        ("Original", "Paroles / Whisper small", "actif"),
        ("vocals.wav", "Mélodie / F0", "préparé" if "vocals" in paths else "à générer"),
        ("drums.wav", "Tempo / beats / mesures", "préparé" if "drums" in paths else "à générer"),
        ("bass.wav", "Fondamentale auxiliaire", "préparé" if "bass" in paths else "à générer"),
        ("other.wav", "Harmonie / accords", "préparé" if "other" in paths else "à générer"),
    ]
    st.dataframe(
        [{"Source": src, "Rôle": role, "État": state} for src, role, state in roles],
        hide_index=True,
        width="stretch",
    )

    if not complete:
        if st.button(
            "Préparer les 4 stems",
            key=f"stem_pipeline_prepare_{active_hash[:12]}",
            type="primary",
        ):
            with st.spinner("Demucs : séparation vocals / drums / bass / other…"):
                try:
                    with perf_span(
                        "stem_pipeline.ensure",
                        audio_bytes=len(audio_bytes or b""),
                        force=False,
                    ):
                        result = _ensure_stems(
                            audio_bytes=audio_bytes,
                            extension=extension,
                            audio_hash=active_hash,
                            force=False,
                        )
                    perf_event(
                        "stem_pipeline.ensure.result",
                        status=str(result.get("status", "")),
                        stems=len(result.get("paths", {}) or {}),
                    )
                except Exception as exc:
                    perf_event(
                        "stem_pipeline.ensure.result",
                        status="error",
                        error_type=type(exc).__name__,
                        error=str(exc),
                    )
                    st.error("Séparation STEM impossible : " + str(exc))
                    return
            st.rerun()
    else:
        with st.expander("Détails / maintenance STEM", expanded=False):
            st.code(
                "Original → Whisper small → paroles\n"
                "vocals  → mélodie / F0\n"
                "drums   → tempo / beats / mesures\n"
                "bass    → fondamentale auxiliaire\n"
                "other   → harmonie / accords",
                language="text",
            )
            if paths:
                st.caption(f"Cache : {next(iter(paths.values())).parent}")
            if st.button(
                "Recalculer les 4 stems",
                key=f"stem_pipeline_rebuild_{active_hash[:12]}",
                type="secondary",
            ):
                with st.spinner("Recalcul Demucs des quatre stems…"):
                    try:
                        _ensure_stems(
                            audio_bytes=audio_bytes,
                            extension=extension,
                            audio_hash=active_hash,
                            force=True,
                        )
                    except Exception as exc:
                        st.error("Recalcul STEM impossible : " + str(exc))
                        return
                st.rerun()

    if manifest:
        st.caption(
            "Checkpoint R2 : stems préparés et visibles. "
            "Le moteur musical historique reste le fallback tant que "
            "drums/other/bass ne sont pas encore branchés."
        )


def _render_vocal_melody_analysis(
    *,
    active_hash,
    song,
    audio_bytes,
    extension,
):
    """Independent vocal-pitch experiment for the feature branch."""
    st.markdown("##### 🎤 Mélodie chantée — expérimental")
    st.caption(
        "Analyse indépendante : hauteur de la voix → notes MIDI. "
        "Aucun timestamp d'accord, de parole ou de phonème n'est modifié."
    )

    cached = _load_vocal_analysis(active_hash)

    analyse_col, structure_col = st.columns([1.0, 1.35])

    with analyse_col:
        analyse_clicked = st.button(
            "Analyser / recalculer la voix",
            key=f"vocal_pitch_analyse_{active_hash[:12]}",
            type="secondary",
        )

    if analyse_clicked:
        with st.spinner(
            "Extraction de la voix et détection des notes chantées…"
        ):
            with perf_span(
                "vocal_pitch.analyse",
                demucs=_vocal_demucs_available(),
                audio_bytes=len(audio_bytes or b""),
            ):
                cached = _analyze_vocal_pitch(
                    audio_bytes=audio_bytes,
                    extension=extension,
                    audio_hash=active_hash,
                    prefer_demucs=True,
                )
        perf_event(
            "vocal_pitch.analyse.result",
            notes=int((cached or {}).get("note_count", 0) or 0),
            source=str((cached or {}).get("source", "")),
        )
        st.rerun()

    if not cached:
        if _vocal_demucs_available():
            st.caption(
                "Demucs est disponible : la piste voix isolée sera utilisée."
            )
        else:
            st.warning(
                "Demucs n'est pas installé : l'analyse reste possible sur le mix, "
                "mais elle sera moins fiable. Aucune régression : cette analyse "
                "reste totalement optionnelle."
            )
        return

    notes = list(cached.get("notes", []) or [])
    source = str(cached.get("source", "") or "")
    note_count = int(cached.get("note_count", len(notes)) or len(notes))

    if source.startswith("demucs"):
        source_label = "piste voix Demucs + pYIN"
    else:
        source_label = "mix original + pYIN (fallback)"

    st.success(
        f"Mélodie vocale disponible : {note_count} notes · {source_label}."
    )

    if cached.get("demucs_error") and not source.startswith("demucs"):
        st.caption(
            "Demucs n'a pas pu être utilisé : "
            + str(cached.get("demucs_error"))
        )

    if notes:
        vocal_midi = _build_vocal_midi_file(notes)
        title = (
            str(song.get("title", "") or "").strip()
            or Path(str(song.get("original_filename", "") or "EZScore")).stem
        )
        st.download_button(
            "⬇ Télécharger le MIDI du chant",
            data=vocal_midi,
            file_name=_safe_midi_filename(title, "chant"),
            mime="audio/midi",
            key=f"vocal_midi_download_{active_hash[:12]}",
        )

    with structure_col:
        refine_clicked = st.button(
            "Recalculer les blocs avec la mélodie",
            key=f"vocal_refine_blocks_{active_hash[:12]}",
            help=(
                "Supprime uniquement la proposition de blocs persistée. "
                "Au rerun, R33 est recalculé puis la mélodie vocale peut déplacer "
                "une frontière existante de ±2 mesures maximum."
            ),
        )

    if refine_clicked:
        _persistence.reset_structure_blocks_from_analysis(active_hash)
        perf_event(
            "structure.vocal.refine.requested",
            notes=len(notes),
        )
        st.rerun()



def _render_analysis_mp3_midi_player(
    *,
    beats,
    signature,
    beats_per_measure,
    program,
    gate_ratio,
    strum_ms,
):
    """Render the missing two-volume synchronized player in Analyse."""
    active_hash = str(st.session_state.get("active_song_hash", "") or "").strip()
    if not active_hash:
        return

    song = _analysis_player_song(active_hash)
    audio_bytes, extension = _analysis_player_audio(active_hash, song)

    if not audio_bytes:
        perf_event(
            "analysis.player.render",
            status="skipped",
            reason="audio_not_found",
        )
        return

    labels = list(_MIDI_INSTRUMENTS.keys())
    current_label = _analysis_instrument_label(program)
    selected_index = labels.index(current_label) if current_label in labels else 0

    instrument_label = st.selectbox(
        "Instrument de contrôle",
        labels,
        index=selected_index,
        key=f"analysis_midi_instrument_{active_hash[:12]}",
    )
    selected_program = int(_MIDI_INSTRUMENTS[instrument_label])
    selected_strum_ms = 12.0 if selected_program == 27 else 0.0

    with perf_span(
        "analysis.player.build_events",
        beats=len(beats or []),
        program=selected_program,
    ):
        chord_events = _build_chord_midi_events(
            beats=beats,
            signature=signature,
            beats_per_measure=beats_per_measure,
            program=selected_program,
            gate_ratio=gate_ratio,
            strum_ms=selected_strum_ms,
        )

    if not chord_events:
        return

    vocal_analysis = _load_vocal_analysis(active_hash)
    vocal_notes = list((vocal_analysis or {}).get("notes", []) or [])

    vocal_instrument_label = "Alto Sax"
    vocal_program = int(
        _VOCAL_MIDI_INSTRUMENTS[vocal_instrument_label]
    )
    vocal_events = []

    if vocal_notes:
        vocal_labels = list(_VOCAL_MIDI_INSTRUMENTS.keys())
        vocal_instrument_label = st.selectbox(
            "Instrument du chant MIDI",
            vocal_labels,
            index=0,
            key=f"analysis_vocal_instrument_{active_hash[:12]}",
        )
        vocal_program = int(
            _VOCAL_MIDI_INSTRUMENTS[vocal_instrument_label]
        )

        with perf_span(
            "analysis.player.build_vocal_events",
            notes=len(vocal_notes),
            program=vocal_program,
        ):
            vocal_events = _build_vocal_midi_events(
                vocal_notes,
                program=vocal_program,
            )

    title = (
        str(song.get("title", "") or "").strip()
        or Path(str(song.get("original_filename", "") or "EZScore")).stem
        or "EZScore"
    )
    artist = str(song.get("artist", "") or "").strip()

    if vocal_events:
        st.caption(
            "MP3 maître + accords MIDI + chant MIDI synchronisés. "
            "Les trois volumes sont indépendants."
        )
    else:
        st.caption(
            "MP3 maître + accords MIDI synchronisés. "
            "Analyse la mélodie chantée pour activer la troisième piste."
        )

    with perf_span(
        "analysis.player.render",
        chord_events=len(chord_events),
        vocal_events=len(vocal_events),
        audio_bytes=len(audio_bytes),
    ):
        _render_analysis_midi_player(
            audio_bytes=audio_bytes,
            extension=extension,
            chord_events=chord_events,
            chord_instrument_label=instrument_label,
            chord_program=selected_program,
            vocal_events=vocal_events,
            vocal_instrument_label=vocal_instrument_label,
            vocal_program=vocal_program,
            title=title,
            artist=artist,
            key=(
                f"analysis_mp3_midi_{active_hash[:12]}_"
                f"{selected_program}_{vocal_program}_"
                f"{1 if vocal_events else 0}"
            ),
        )

    _render_stem_pipeline_analysis(
        active_hash=active_hash,
        audio_bytes=audio_bytes,
        extension=extension,
    )

    _render_vocal_melody_analysis(
        active_hash=active_hash,
        song=song,
        audio_bytes=audio_bytes,
        extension=extension,
    )


def _ezscore_build_midi_file(*args, **kwargs):
    """Build the downloadable MIDI and restore the Analyse comparison player."""
    started = __import__("time").perf_counter()
    midi_bytes = _build_midi_file(*args, **kwargs)

    try:
        active_hash = str(
            st.session_state.get("active_song_hash", "") or ""
        )
        view = (
            str(
                st.session_state.get(
                    f"song_view_{active_hash[:12]}",
                    "",
                )
            )
            if active_hash
            else ""
        )

        if view == "Analyse":
            beats = kwargs.get("beats", args[0] if args else [])
            _render_analysis_mp3_midi_player(
                beats=beats,
                signature=str(kwargs.get("signature", "4/4")),
                beats_per_measure=int(
                    kwargs.get("beats_per_measure", 4)
                ),
                program=int(kwargs.get("program", 27)),
                gate_ratio=float(kwargs.get("gate_ratio", 0.48)),
                strum_ms=float(kwargs.get("strum_ms", 0.0)),
            )
    except Exception as exc:
        perf_event(
            "analysis.player.render",
            status="error",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        st.warning(
            "Le lecteur MP3 + MIDI n'a pas pu être initialisé : "
            + str(exc)
        )

    perf_event(
        "midi.build_midi_file.bridge",
        duration_ms=(
            __import__("time").perf_counter() - started
        ) * 1000.0,
        bytes=len(midi_bytes or b""),
    )
    return midi_bytes


# EZScore.py performs `from ezscore.persistence import *` after app_shell.
# Export the corrected wrapper through that existing import path.
_persistence.build_midi_file = _ezscore_build_midi_file
if "build_midi_file" not in _persistence.__all__:
    _persistence.__all__.append("build_midi_file")

perf_event("midi.symbol.exported", exported=True)


# ---------------------------------------------------------------------------
# R30 compatibility shim — structure detection is mandatory.
#
# EZScore.py R30 still instantiates two legacy widgets:
# - setting_sections_enabled
# - setting_section_block_measures
#
# We neutralize those exact widget keys before rendering:
# - structure detection is always enabled;
# - the internal observation window is fixed at 4 measures.
#
# This keeps the R30 SSO/auth/application shell intact while removing the two
# obsolete choices from the UI. Only the similarity sensitivity remains user-
# adjustable.
# ---------------------------------------------------------------------------

_ORIGINAL_ST_CHECKBOX = st.checkbox
_ORIGINAL_ST_SELECTBOX = st.selectbox
_ORIGINAL_ST_RADIO = st.radio
_ORIGINAL_ST_COLUMNS = st.columns
_ORIGINAL_ST_DATA_EDITOR = st.data_editor
_ORIGINAL_ST_TEXT_AREA = st.text_area
_ORIGINAL_ST_MARKDOWN = st.markdown
_ORIGINAL_ST_CAPTION = st.caption
_ORIGINAL_ST_INFO = st.info



def _song_hash_for_context() -> str:
    return str(st.session_state.get("active_song_hash", "") or "").strip()


def _work_mode_key(active_hash: str) -> str:
    return f"ez_work_mode_{active_hash[:12]}"


def _edit_tab_key(active_hash: str) -> str:
    return f"ez_edit_tab_{active_hash[:12]}"


def _player_tab_key(active_hash: str) -> str:
    return f"ez_player_tab_{active_hash[:12]}"


def _analysis_exists(active_hash: str) -> bool:
    if not active_hash:
        return False
    return load_latest_persisted_analysis(active_hash) is not None


def _initial_work_mode(active_hash: str, legacy_view: str) -> str:
    """Map the historical Vue/Édition state to the new three work modes."""
    legacy_mode = str(
        st.session_state.get(f"song_mode_{active_hash[:12]}", "") or ""
    )
    if legacy_view == "Analyse":
        return "Analyse"
    if legacy_mode == "Édition":
        return "Édition"
    if allowed("song.edit") and not _analysis_exists(active_hash):
        return "Analyse"
    return "Player"


def _render_context_tabs(active_hash: str, work_mode: str) -> str:
    """Render mode-specific navigation in the main page.

    Returns the historical `song_view` value expected by EZScore.py.
    The old rendering/editing code therefore remains authoritative.
    """
    global _SONG_CONTEXT_TABS_SLOT

    if work_mode == "Analyse":
        if _SONG_CONTEXT_TABS_SLOT is not None:
            with _SONG_CONTEXT_TABS_SLOT.container():
                st.caption("Mode Analyse · STEM · Paroles · Blocs / structure · MIDI")
        return "Analyse"

    if _SONG_CONTEXT_TABS_SLOT is None:
        raise RuntimeError("Le conteneur d'onglets contextuels n'est pas initialisé.")

    if work_mode == "Édition":
        options = ["Blocs", "Paroles + accords", "Grille"]
        state_key = _edit_tab_key(active_hash)
        current = str(st.session_state.get(state_key, "Blocs") or "Blocs")
        if current not in options:
            current = "Blocs"

        with _SONG_CONTEXT_TABS_SLOT.container():
            segmented_kwargs = {
                "key": state_key,
                "width": "stretch",
                "label_visibility": "collapsed",
            }
            if state_key not in st.session_state:
                segmented_kwargs["default"] = current

            selected = st.segmented_control(
                "Édition",
                options,
                **segmented_kwargs,
            )
        return str(selected or current)

    if work_mode == "Player":
        options = ["Karaoké", "Paroles + accords", "Grille"]
        state_key = _player_tab_key(active_hash)
        current = str(st.session_state.get(state_key, "Karaoké") or "Karaoké")
        if current not in options:
            current = "Karaoké"

        with _SONG_CONTEXT_TABS_SLOT.container():
            segmented_kwargs = {
                "key": state_key,
                "width": "stretch",
                "label_visibility": "collapsed",
            }
            if state_key not in st.session_state:
                segmented_kwargs["default"] = current

            selected = st.segmented_control(
                "Player",
                options,
                **segmented_kwargs,
            )

        # The existing Paroles + accords player is already the karaoke surface:
        # synchronized original audio + lyrics. Keep its tested rendering path.
        selected = str(selected or current)
        st.session_state[f"ez_player_surface_{active_hash[:12]}"] = selected
        if selected == "Karaoké":
            return "Paroles + accords"
        return selected

    raise RuntimeError(f"Mode de travail EZScore inconnu : {work_mode!r}")


def _ezscore_radio(*args, **kwargs):
    """Replace the historical View + View/Edit pair by a single work mode.

    Sidebar:
        Analyse / Édition / Player

    Main area:
        Édition -> Blocs / Paroles + accords / Grille
        Player  -> Karaoké / Paroles + accords / Grille
        Analyse -> the four existing STEM_LAB tabs
    """
    key = str(kwargs.get("key", "") or "")

    if key.startswith("song_view_"):
        active_hash = _song_hash_for_context()
        if not active_hash:
            return _ORIGINAL_ST_RADIO(*args, **kwargs)

        legacy_view = str(st.session_state.get(key, "Paroles + accords") or "")
        mode_key = _work_mode_key(active_hash)

        if mode_key in st.session_state:
            initial_mode = str(st.session_state.get(mode_key, "") or "")
        else:
            initial_mode = _initial_work_mode(
                active_hash,
                legacy_view,
            )

        if allowed("song.edit"):
            mode_options = ["Analyse", "Édition", "Player"]
        else:
            # Registered readers and public viewers do not receive edit/analyse controls.
            mode_options = ["Player"]

        current_mode = str(
            st.session_state.get(mode_key, initial_mode or mode_options[0])
            or (initial_mode or mode_options[0])
        )
        if current_mode not in mode_options:
            current_mode = mode_options[0]
            if mode_key in st.session_state:
                st.session_state[mode_key] = current_mode

        radio_kwargs = {
            "key": mode_key,
            "help": (
                "Analyse = produire/contrôler les données · "
                "Édition = modifier blocs, paroles et grille · "
                "Player = lecture/karaoké."
            ),
        }

        # Streamlit warning guard:
        # once the widget key is present in Session State, the widget must not
        # also receive an explicit default/index.
        if mode_key not in st.session_state:
            radio_kwargs["index"] = mode_options.index(current_mode)

        selected_mode = _ORIGINAL_ST_RADIO(
            "Mode",
            mode_options,
            **radio_kwargs,
        )
        mapped_view = _render_context_tabs(active_hash, str(selected_mode))
        st.session_state[key] = mapped_view
        return mapped_view

    if key.startswith("song_mode_") and key.endswith("_radio"):
        active_hash = _song_hash_for_context()
        work_mode = str(
            st.session_state.get(_work_mode_key(active_hash), "Player")
            if active_hash
            else "Player"
        )

        # EZScore.py still expects one of these two labels and performs the
        # historical mapping immediately afterwards.
        if work_mode == "Édition" and allowed("song.edit"):
            return "✏️ Éditer"
        return "👁 Vue"

    return _ORIGINAL_ST_RADIO(*args, **kwargs)



_BLOCK_EDITOR_SELECTED_PREFIX = "ez_block_detail_id_"


def _block_editor_active() -> bool:
    """True only inside Édition > Blocs for the active song."""
    active_hash = _song_hash_for_context()
    if not active_hash:
        return False

    work_mode = str(
        st.session_state.get(_work_mode_key(active_hash), "") or ""
    )
    song_view = str(
        st.session_state.get(f"song_view_{active_hash[:12]}", "") or ""
    )
    return work_mode == "Édition" and song_view == "Blocs"


def _block_editor_draft(active_hash: str) -> list[dict]:
    key = f"structure_draft_{active_hash[:16]}"
    draft = st.session_state.get(key, [])
    if not isinstance(draft, list):
        return []
    return [dict(item) for item in draft if isinstance(item, dict)]


def _block_editor_selected_key(active_hash: str) -> str:
    return f"{_BLOCK_EDITOR_SELECTED_PREFIX}{active_hash[:12]}"


def _selected_block_id(active_hash: str) -> int | None:
    value = st.session_state.get(_block_editor_selected_key(active_hash))
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _ezscore_columns(*args, **kwargs):
    """Stack the two historical block-editor panels vertically.

    Only the exact top-level `[2, 3], gap="large"` split used by the
    Blocs editor is replaced. All other columns in EZScore stay unchanged.
    """
    if _block_editor_active() and args:
        spec = args[0]
        gap = str(kwargs.get("gap", "") or "")
        if (
            isinstance(spec, (list, tuple))
            and list(spec) == [2, 3]
            and gap == "large"
        ):
            return [st.container(), st.container()]

    return _ORIGINAL_ST_COLUMNS(*args, **kwargs)


def _lyrics_anchor_id(active_hash: str, block_id: int) -> str:
    return f"ez-lyrics-{active_hash[:12]}-{int(block_id)}"


def _ezscore_data_editor(*args, **kwargs):
    """Full-width structure table + one real Edit button per block.

    The button is deliberately outside st.data_editor because Streamlit's
    dataframe widget has no native action-button column. Each action is placed
    in its own bordered box directly below the structure grid.
    """
    result = _ORIGINAL_ST_DATA_EDITOR(*args, **kwargs)

    key = str(kwargs.get("key", "") or "")
    if not (
        _block_editor_active()
        and key.startswith("structure_live_table_")
    ):
        return result

    active_hash = _song_hash_for_context()
    draft = _block_editor_draft(active_hash)
    if not draft:
        return result

    block_ids = [
        int(block.get("block_id", index + 1) or (index + 1))
        for index, block in enumerate(draft)
    ]
    selected_key = _block_editor_selected_key(active_hash)
    current = _selected_block_id(active_hash)

    if current not in block_ids:
        current = block_ids[0]
        st.session_state[selected_key] = current

    st.markdown("#### Paroles")

    for row_start in range(0, len(draft), 4):
        row_blocks = draft[row_start:row_start + 4]
        cols = _ORIGINAL_ST_COLUMNS(len(row_blocks))

        for local_index, block in enumerate(row_blocks):
            absolute_index = row_start + local_index
            block_id = block_ids[absolute_index]
            title = (
                str(block.get("custom_label", "") or "").strip()
                or f"Bloc {absolute_index + 1}"
            )
            m0 = int(block.get("measure_start", 0) or 0)
            m1 = int(block.get("measure_end", m0) or m0)

            with cols[local_index]:
                with st.container(border=True):
                    st.caption(f"{title} · mesures {m0}–{m1}")
                    if st.button(
                        "✏️ Éditer les paroles",
                        key=(
                            f"edit_block_lyrics_btn_"
                            f"{active_hash[:12]}_{block_id}"
                        ),
                        type="primary" if block_id == current else "secondary",
                        width="stretch",
                        help=(
                            f"Aller au bloc {title} et passer ses paroles "
                            "en mode édition."
                        ),
                    ):
                        st.session_state[selected_key] = block_id
                        st.session_state[
                            f"ez_scroll_lyrics_target_{active_hash[:12]}"
                        ] = block_id
                        st.rerun()

    return result


def _strong_interval_match(item_t0, item_t1, target_t0, target_t1):
    """Return a score for the same lyric block, or None if too different."""
    e0 = float(item_t0)
    e1 = float(item_t1)
    t0 = float(target_t0)
    t1 = float(target_t1)

    d0 = abs(e0 - t0)
    d1 = abs(e1 - t1)
    if d0 <= 0.02 and d1 <= 0.02:
        return (3.0, -(d0 + d1))

    current_duration = max(0.001, t1 - t0)
    edit_duration = max(0.001, e1 - e0)
    overlap = max(0.0, min(t1, e1) - max(t0, e0))
    if overlap <= 0.0:
        return None

    overlap_ratio = overlap / min(current_duration, edit_duration)
    if overlap_ratio < 0.70:
        return None

    center_distance = abs(((e0 + e1) / 2.0) - ((t0 + t1) / 2.0))
    center_limit = 0.35 * max(current_duration, edit_duration)
    if center_distance > center_limit:
        return None

    duration_ratio = min(current_duration, edit_duration) / max(
        current_duration,
        edit_duration,
    )
    return (2.0 + overlap_ratio, duration_ratio, -center_distance)


def _block_interval_from_analysis(active_hash: str, block_id: int):
    analysis = _persistence.load_latest_persisted_analysis(active_hash)
    if not analysis:
        return None

    music = dict(analysis.get("musique", {}) or {})
    measures = list(music.get("mesures", []) or [])
    if not measures:
        return None

    blocks = _persistence.load_structure_blocks(active_hash)
    block = next(
        (
            item for item in blocks
            if int(item.get("block_id", -1)) == int(block_id)
        ),
        None,
    )
    if block is None:
        return None

    m0 = int(block.get("measure_start", 1) or 1)
    m1 = int(block.get("measure_end", m0) or m0)
    if not (1 <= m0 <= len(measures) and 1 <= m1 <= len(measures)):
        return None

    t0 = float(measures[m0 - 1].get("debut", 0.0) or 0.0)
    t1 = float(measures[m1 - 1].get("fin", t0) or t0) + 0.001
    return block, t0, t1


def _recover_lyric_from_current_rows(active_hash: str, t0: float, t1: float):
    """Read current lyric_block_edits without changing anything."""
    try:
        with sqlite3.connect(_persistence.DB_PATH) as conn:
            rows = conn.execute(
                """
                SELECT corrected_text, time_start, time_end
                FROM lyric_block_edits
                WHERE audio_hash = ?
                """,
                (str(active_hash),),
            ).fetchall()
    except sqlite3.OperationalError:
        return None

    best = None
    best_score = None
    for corrected_text, e0, e1 in rows:
        score = _strong_interval_match(e0, e1, t0, t1)
        if score is None:
            continue
        if best_score is None or score > best_score:
            best = str(corrected_text or "")
            best_score = score

    return best if best_score is not None else None


def _recover_lyric_from_versions(
    active_hash: str,
    block_id: int,
    current_block: dict,
):
    """Recover the lyric of the SAME block from complete historical snapshots.

    Matching uses the persisted block_id first. This is intentionally stronger
    than matching today's time boundaries, because R12 changed presentation and
    the analysis source but must not detach previously validated lyrics.
    """
    try:
        with sqlite3.connect(_persistence.DB_PATH) as conn:
            rows = conn.execute(
                """
                SELECT version_no, music_json, structure_json, lyric_edits_json
                FROM analysis_versions
                WHERE audio_hash = ?
                  AND trim(lyric_edits_json) NOT IN ('', '{}')
                ORDER BY version_no DESC
                """,
                (str(active_hash),),
            ).fetchall()
    except sqlite3.OperationalError:
        return None

    current_order = int(current_block.get("order_index", 0) or 0)

    for version_no, music_json, structure_json, lyric_json in rows:
        try:
            music = json.loads(music_json or "{}")
            structure = json.loads(structure_json or "[]")
            lyric_edits = json.loads(lyric_json or "{}")
        except Exception:
            continue

        if not isinstance(structure, list) or not isinstance(lyric_edits, dict):
            continue

        historical_block = next(
            (
                item for item in structure
                if isinstance(item, dict)
                and int(item.get("block_id", -1)) == int(block_id)
            ),
            None,
        )

        if historical_block is None:
            historical_block = next(
                (
                    item for item in structure
                    if isinstance(item, dict)
                    and int(item.get("order_index", -1)) == current_order
                ),
                None,
            )

        if historical_block is None:
            continue

        measures = list(dict(music or {}).get("mesures", []) or [])
        if not measures:
            continue

        hm0 = int(historical_block.get("measure_start", 1) or 1)
        hm1 = int(historical_block.get("measure_end", hm0) or hm0)
        if not (1 <= hm0 <= len(measures) and 1 <= hm1 <= len(measures)):
            continue

        ht0 = float(measures[hm0 - 1].get("debut", 0.0) or 0.0)
        ht1 = float(measures[hm1 - 1].get("fin", ht0) or ht0) + 0.001

        best = None
        best_score = None
        for item in lyric_edits.values():
            if not isinstance(item, dict):
                continue
            e0 = float(item.get("time_start", 0.0) or 0.0)
            e1 = float(item.get("time_end", e0) or e0)
            score = _strong_interval_match(e0, e1, ht0, ht1)
            if score is None:
                continue
            if best_score is None or score > best_score:
                best = str(item.get("corrected_text", "") or "")
                best_score = score

        if best_score is not None:
            return {
                "text": best,
                "version_no": int(version_no),
            }

    return None


def _validated_lyric_for_block(active_hash: str, block_id: int):
    """Resolve validated lyric text without modifying DB state."""
    interval = _block_interval_from_analysis(active_hash, block_id)
    if interval is None:
        return None

    block, t0, t1 = interval

    # Current table is always authoritative, including an explicitly empty edit.
    current = _recover_lyric_from_current_rows(active_hash, t0, t1)
    if current is not None:
        return {
            "text": current,
            "source": "current",
        }

    historical = _recover_lyric_from_versions(
        active_hash,
        block_id,
        block,
    )
    if historical is not None:
        return {
            "text": str(historical.get("text", "") or ""),
            "source": f"version:{historical.get('version_no')}",
        }

    return None



def _token_spans(value: str):
    return [
        (match.group(0), match.start(), match.end())
        for match in __import__("re").finditer(r"\S+", str(value or ""))
    ]


def _norm_token(value: str) -> str:
    return __import__("re").sub(
        r"^[^\wÀ-ÿ]+|[^\wÀ-ÿ]+$",
        "",
        str(value or "").casefold(),
    )


def _project_source_boundary(opcodes, source_index: int, target_len: int) -> int:
    """Project a token boundary from source text to edited text."""
    source_index = max(0, int(source_index))

    for tag, i1, i2, j1, j2 in opcodes:
        if source_index < i1:
            return max(0, min(target_len, j1))

        if i1 <= source_index <= i2:
            if i2 == i1:
                return max(0, min(target_len, j1))

            fraction = (source_index - i1) / max(i2 - i1, 1)
            projected = round(j1 + fraction * (j2 - j1))
            return max(0, min(target_len, int(projected)))

    return max(0, min(target_len, target_len))


def _slice_tokens_preserve_layout(value: str, token_start: int, token_end: int) -> str:
    spans = _token_spans(value)
    token_start = max(0, min(len(spans), int(token_start)))
    token_end = max(token_start, min(len(spans), int(token_end)))

    if token_start >= token_end:
        return ""

    char_start = spans[token_start][1]
    char_end = spans[token_end - 1][2]
    return str(value or "")[char_start:char_end].strip()


def _rebase_lyrics_after_boundary_change(
    previous_original: str,
    current_text: str,
    new_original: str,
) -> str:
    """Reassign lyric text when a block is extended or shortened.

    Canonical word timestamps do not move. This function only changes which
    source words belong to the visual block.

    Existing corrections in the overlapping core are preserved. Newly included
    boundary words are taken from Whisper. Removed boundary words disappear.
    """
    old_tokens = [token for token, _, _ in _token_spans(previous_original)]
    new_tokens = [token for token, _, _ in _token_spans(new_original)]
    edited_tokens = [token for token, _, _ in _token_spans(current_text)]

    if not old_tokens:
        return str(new_original or "")
    if not new_tokens:
        return ""

    old_norm = [_norm_token(token) for token in old_tokens]
    new_norm = [_norm_token(token) for token in new_tokens]
    edited_norm = [_norm_token(token) for token in edited_tokens]

    if old_norm == new_norm:
        return str(current_text or "")

    boundary_matcher = SequenceMatcher(
        a=old_norm,
        b=new_norm,
        autojunk=False,
    )
    common = boundary_matcher.find_longest_match(
        0,
        len(old_norm),
        0,
        len(new_norm),
    )

    # A block that became entirely different must use its canonical words.
    minimum_common = min(3, len(old_norm), len(new_norm))
    if common.size < minimum_common:
        return str(new_original or "")

    edit_matcher = SequenceMatcher(
        a=old_norm,
        b=edited_norm,
        autojunk=False,
    )
    opcodes = edit_matcher.get_opcodes()

    edited_start = _project_source_boundary(
        opcodes,
        common.a,
        len(edited_tokens),
    )
    edited_end = _project_source_boundary(
        opcodes,
        common.a + common.size,
        len(edited_tokens),
    )

    corrected_core = _slice_tokens_preserve_layout(
        current_text,
        edited_start,
        edited_end,
    )

    new_prefix = " ".join(new_tokens[:common.b]).strip()
    new_suffix = " ".join(
        new_tokens[common.b + common.size:]
    ).strip()

    pieces = [
        piece
        for piece in (new_prefix, corrected_core, new_suffix)
        if str(piece or "").strip()
    ]
    return " ".join(pieces).strip()


def _draft_block_original_text(active_hash: str, block_id: int):
    """Canonical Whisper words currently assigned to the draft block."""
    analysis = _persistence.load_latest_persisted_analysis(active_hash)
    if not analysis:
        return None

    result = dict(analysis.get("resultat", {}) or {})
    music = dict(analysis.get("musique", {}) or {})
    measures = list(music.get("mesures", []) or [])
    if not measures:
        return None

    draft = _block_editor_draft(active_hash)
    block = next(
        (
            item
            for index, item in enumerate(draft)
            if int(item.get("block_id", index + 1) or (index + 1))
            == int(block_id)
        ),
        None,
    )
    if block is None:
        return None

    m0 = int(block.get("measure_start", 1) or 1)
    m1 = int(block.get("measure_end", m0) or m0)
    if not (1 <= m0 <= len(measures) and 1 <= m1 <= len(measures)):
        return None

    t0 = float(measures[m0 - 1].get("debut", 0.0) or 0.0)
    t1 = float(measures[m1 - 1].get("fin", t0) or t0) + 0.001

    words = _persistence._source_words_for_interval(
        result,
        t0,
        t1,
    )
    original = " ".join(
        str(word.get("text", "") or "").strip()
        for word in words
        if str(word.get("text", "") or "").strip()
    ).strip()

    return {
        "measure_start": m0,
        "measure_end": m1,
        "original_text": original,
    }


def _block_lyrics_widget_id(key: str) -> int | None:
    match = __import__("re").search(r"_id(\d+)$", str(key or ""))
    if not match:
        return None
    return int(match.group(1))


def _ezscore_text_area(*args, **kwargs):
    """Show every lyric block; edit exactly one selected block."""
    key = str(kwargs.get("key", "") or "")

    if not (_block_editor_active() and key.startswith("block_lyrics_")):
        return _ORIGINAL_ST_TEXT_AREA(*args, **kwargs)

    active_hash = _song_hash_for_context()
    widget_block_id = _block_lyrics_widget_id(key)
    selected_id = _selected_block_id(active_hash)

    if widget_block_id is None:
        return _ORIGINAL_ST_TEXT_AREA(*args, **kwargs)

    # R12.4: recover validated text before presenting the block.
    recovery_marker = (
        f"ez_r124_lyrics_recovered_{active_hash[:12]}_{widget_block_id}"
    )
    if not st.session_state.get(recovery_marker, False):
        current_value = str(st.session_state.get(key, "") or "")
        if not current_value.strip():
            recovered = _validated_lyric_for_block(
                active_hash,
                int(widget_block_id),
            )
            if recovered is not None:
                recovered_text = str(recovered.get("text", "") or "")
                if recovered_text.strip():
                    st.session_state[key] = recovered_text
        st.session_state[recovery_marker] = True

    # Automatic repartition when a block boundary changes.
    current_assignment = _draft_block_original_text(
        active_hash,
        int(widget_block_id),
    )
    assignment_key = (
        f"ez_lyrics_assignment_{active_hash[:12]}_{widget_block_id}"
    )
    previous_assignment = st.session_state.get(assignment_key)

    if current_assignment is not None:
        if isinstance(previous_assignment, dict):
            previous_bounds = (
                int(previous_assignment.get("measure_start", 0) or 0),
                int(previous_assignment.get("measure_end", 0) or 0),
            )
            current_bounds = (
                int(current_assignment.get("measure_start", 0) or 0),
                int(current_assignment.get("measure_end", 0) or 0),
            )

            if previous_bounds != current_bounds:
                previous_original = str(
                    previous_assignment.get("original_text", "") or ""
                )
                current_text = str(st.session_state.get(key, "") or "")
                new_original = str(
                    current_assignment.get("original_text", "") or ""
                )

                st.session_state[key] = _rebase_lyrics_after_boundary_change(
                    previous_original,
                    current_text,
                    new_original,
                )

        st.session_state[assignment_key] = dict(current_assignment)

    current_text = str(st.session_state.get(key, "") or "")

    if widget_block_id == selected_id:
        pending_scroll_key = (
            f"ez_scroll_lyrics_target_{active_hash[:12]}"
        )
        pending_target = st.session_state.get(pending_scroll_key)

        if pending_target is not None and int(pending_target) == int(widget_block_id):
            _SCROLL_TO_LYRICS(
                data={
                    "target_id": _lyrics_anchor_id(
                        active_hash,
                        int(widget_block_id),
                    )
                },
                key=(
                    f"scroll_to_lyrics_"
                    f"{active_hash[:12]}_{widget_block_id}_"
                    f"{int(st.session_state.get(
                        'ez_scroll_seq_' + active_hash[:12],
                        0
                    ))}"
                ),
            )
            st.session_state.pop(pending_scroll_key, None)
            seq_key = f"ez_scroll_seq_{active_hash[:12]}"
            st.session_state[seq_key] = int(
                st.session_state.get(seq_key, 0)
            ) + 1

        st.caption("✏️ Mode édition")
        kwargs = dict(kwargs)
        kwargs["height"] = max(150, int(kwargs.get("height", 120) or 120))
        return _ORIGINAL_ST_TEXT_AREA(*args, **kwargs)

    # Read-only compact view for every non-selected block.
    display = html.escape(current_text or "[instrumental]")
    _ORIGINAL_ST_MARKDOWN(
        (
            '<div class="ez-lyrics-preview-readonly">'
            + display.replace("\n", "<br>")
            + "</div>"
        ),
        unsafe_allow_html=True,
    )
    return current_text


def _ezscore_markdown(*args, **kwargs):
    """Show every lyric block and attach a stable browser anchor."""
    if not args:
        return _ORIGINAL_ST_MARKDOWN(*args, **kwargs)

    value = str(args[0] or "")

    if _block_editor_active():
        value = value.replace(
            "À gauche, modifiez le découpage. À droite, "
            "contrôlez immédiatement les paroles et accords "
            "correspondant aux bornes du brouillon.",
            "Modifiez le découpage sur toute la largeur. "
            "Tous les blocs de paroles restent visibles en dessous.",
        )

        match = __import__("re").fullmatch(
            r"\*\*(.+?)\*\* · mesures (\d+)–(\d+)",
            value.strip(),
        )
        if match:
            active_hash = _song_hash_for_context()
            draft = _block_editor_draft(active_hash)
            m0 = int(match.group(2))
            m1 = int(match.group(3))

            block_id = None
            for index, block in enumerate(draft):
                if (
                    int(block.get("measure_start", 0) or 0) == m0
                    and int(block.get("measure_end", 0) or 0) == m1
                ):
                    block_id = int(
                        block.get("block_id", index + 1)
                        or (index + 1)
                    )
                    break

            if block_id is not None:
                title = html.escape(str(match.group(1)))
                anchor = _lyrics_anchor_id(active_hash, block_id)
                return _ORIGINAL_ST_MARKDOWN(
                    (
                        f'<div id="{anchor}" '
                        'class="ez-lyrics-block-anchor"></div>'
                        '<div class="ez-lyrics-block-heading">'
                        f'<strong>{title}</strong>'
                        f' · mesures {m0}–{m1}'
                        "</div>"
                    ),
                    unsafe_allow_html=True,
                )

    return _ORIGINAL_ST_MARKDOWN(*args, **kwargs)


def _ezscore_checkbox(*args, **kwargs):
    key = kwargs.get("key")
    if key == "setting_sections_enabled":
        st.session_state[key] = True
        return True
    return _ORIGINAL_ST_CHECKBOX(*args, **kwargs)


def _ezscore_selectbox(*args, **kwargs):
    key = kwargs.get("key")
    if key == "setting_section_block_measures":
        st.session_state[key] = 4
        return 4
    return _ORIGINAL_ST_SELECTBOX(*args, **kwargs)





def _ezscore_info(*args, **kwargs):
    """Swap the legacy fresh-song message for the validated STEM_LAB surface."""
    if args:
        value = str(args[0] or "").strip()
        if value.startswith("Aucune analyse n'a encore été lancée."):
            active_hash = str(
                st.session_state.get("active_song_hash", "") or ""
            ).strip()
            if active_hash:
                from ezscore.ui.stem_lab_analysis import (
                    render_stem_lab_fresh_analysis,
                )
                render_stem_lab_fresh_analysis(active_hash)
                return None
    return _ORIGINAL_ST_INFO(*args, **kwargs)


def _ezscore_caption(*args, **kwargs):
    if args:
        value = str(args[0] or "").strip()

        if (
            _block_editor_active()
            and value.startswith(
                "Paroles seules, sans accords. Chaque bloc suit les bornes"
            )
        ):
            return _ORIGINAL_ST_CAPTION(
                "Tous les blocs de paroles sont affichés ci-dessous. "
                "Le bouton « Éditer les paroles » de la grille fait défiler "
                "la page jusqu’au bloc demandé et active son éditeur."
            )
        if value == (
            "La lecture MIDI synchronisée est disponible dans "
            "Grille > Jouer."
        ):
            return None
    return _ORIGINAL_ST_CAPTION(*args, **kwargs)


st.checkbox = _ezscore_checkbox
st.selectbox = _ezscore_selectbox
st.radio = _ezscore_radio
st.columns = _ezscore_columns
st.data_editor = _ezscore_data_editor
st.text_area = _ezscore_text_area
st.markdown = _ezscore_markdown
st.caption = _ezscore_caption
st.info = _ezscore_info


# ---------------------------------------------------------------------------
# R33 compatibility bridge — vocal pre-roll / post-roll.
#
# Primary timelines remain authoritative. Structural blocks are visual only.
# The legacy R30 orchestration still rebuilds block time_start/time_end from
# measure boundaries, which cuts lyrics sung before measure 1 (and potentially
# after the last detected measure).
#
# R33's structure engine already carries the correct visual envelope in
# detected_sections. We preserve it here without moving a single timestamp:
# - materialized first/last block inherit the wider detected envelope;
# - the block editor preview, which still queries raw measure boundaries,
#   transparently receives the same envelope through _source_words_for_interval.
#
# This bridge can disappear when EZScore.py is fully migrated to the canonical
# timeline API.
# ---------------------------------------------------------------------------

_ORIGINAL_MATERIALISER_STRUCTURE_BLOCKS = (
    _persistence.materialiser_structure_blocks
)
_ORIGINAL_SOURCE_WORDS_FOR_INTERVAL = (
    _persistence._source_words_for_interval
)

_LYRICS_ENVELOPE_STATE_KEY = "_ezscore_lyrics_visual_envelope"


def _ezscore_materialiser_structure_blocks(
    blocks,
    mesures,
    detected_sections,
):
    result = _ORIGINAL_MATERIALISER_STRUCTURE_BLOCKS(
        blocks=blocks,
        mesures=mesures,
        detected_sections=detected_sections,
    )

    if not result:
        st.session_state.pop(_LYRICS_ENVELOPE_STATE_KEY, None)
        return result

    raw_start = float(result[0].get("time_start", 0.0) or 0.0)
    raw_end = float(result[-1].get("time_end", raw_start) or raw_start)

    visual_start = raw_start
    visual_end = raw_end

    detected = [
        section
        for section in (detected_sections or [])
        if isinstance(section, dict)
    ]

    if detected:
        first_detected = min(
            detected,
            key=lambda section: int(
                section.get("measure_start", 10**9) or 10**9
            ),
        )
        last_detected = max(
            detected,
            key=lambda section: int(
                section.get("measure_end", 0) or 0
            ),
        )

        try:
            visual_start = min(
                raw_start,
                float(first_detected.get("time_start", raw_start)),
            )
        except (TypeError, ValueError):
            visual_start = raw_start

        try:
            visual_end = max(
                raw_end,
                float(last_detected.get("time_end", raw_end)),
            )
        except (TypeError, ValueError):
            visual_end = raw_end

    result[0]["time_start"] = visual_start
    result[-1]["time_end"] = visual_end

    st.session_state[_LYRICS_ENVELOPE_STATE_KEY] = {
        "measure_time_start": raw_start,
        "measure_time_end": raw_end,
        "visual_time_start": visual_start,
        "visual_time_end": visual_end,
    }

    if visual_start < raw_start or visual_end > raw_end:
        perf_event(
            "lyrics.visual_envelope",
            measure_start=raw_start,
            measure_end=raw_end,
            visual_start=visual_start,
            visual_end=visual_end,
        )

    return result


def _ezscore_source_words_for_interval(resultat, t0, t1):
    query_start = float(t0)
    query_end = float(t1)

    envelope = st.session_state.get(_LYRICS_ENVELOPE_STATE_KEY)
    if isinstance(envelope, dict):
        measure_start = float(
            envelope.get("measure_time_start", query_start)
        )
        measure_end = float(
            envelope.get("measure_time_end", query_end)
        )
        visual_start = float(
            envelope.get("visual_time_start", measure_start)
        )
        visual_end = float(
            envelope.get("visual_time_end", measure_end)
        )

        # Only the true first/last measure boundaries are expanded.
        # Middle block boundaries are never touched.
        if abs(query_start - measure_start) <= 0.010:
            query_start = min(query_start, visual_start)

        if abs(query_end - measure_end) <= 0.010:
            query_end = max(query_end, visual_end)

    return _ORIGINAL_SOURCE_WORDS_FOR_INTERVAL(
        resultat,
        query_start,
        query_end,
    )


# Patch the already imported persistence module BEFORE EZScore.py later performs
# `from ezscore.persistence import *`. The orchestration therefore receives the
# corrected functions without any change to auth/SSO, timelines or R33.
_persistence.materialiser_structure_blocks = (
    _ezscore_materialiser_structure_blocks
)
_persistence._source_words_for_interval = (
    _ezscore_source_words_for_interval
)


_SHELL_CSS = r"""
<style>
.ez-lyrics-block-anchor {
    scroll-margin-top: 5.5rem;
}
.ez-lyrics-block-heading {
    font-size: 1.05rem;
    font-weight: 800;
    margin: 1rem 0 .35rem 0;
    padding: .35rem .55rem;
    border-left: 4px solid var(--primary-color, #4da3ff);
}
.ez-lyrics-preview-readonly {
    white-space: pre-wrap;
    line-height: 1.35;
    padding: .7rem .8rem;
    margin: 0 0 .45rem 0;
    border: 1px solid rgba(120,130,145,.25);
    border-radius: .5rem;
    background: rgba(120,130,145,.035);
}
.ez-topbar {
    display:flex;
    align-items:center;
    gap:1rem;
    padding:.65rem .9rem;
    margin:0 0 .85rem 0;
    border:1px solid rgba(120,130,145,.24);
    border-radius:14px;
    background:linear-gradient(90deg, rgba(20,92,86,.24), rgba(18,25,34,.12));
}
.ez-topbar-logo {
    font-size:1.65rem;
    font-weight:900;
    white-space:nowrap;
}
.ez-topbar-search {
    flex:1;
    min-width:8rem;
    opacity:.8;
    border:1px solid rgba(120,130,145,.26);
    border-radius:999px;
    padding:.55rem .9rem;
}
.ez-topbar-user {
    font-weight:750;
    white-space:nowrap;
}
.ez-side-profile {
    text-align:center;
    padding:.7rem .25rem 1rem;
}
.ez-side-avatar {
    width:76px;
    height:76px;
    border-radius:50%;
    margin:0 auto .55rem;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:1.65rem;
    font-weight:900;
    background:rgba(45,180,160,.18);
    border:2px solid rgba(45,180,160,.55);
}
.ez-side-name {
    font-weight:850;
    line-height:1.2;
}
.ez-side-role {
    opacity:.68;
    font-size:.82rem;
    margin-top:.2rem;
}
.ez-side-profile-compact {
    display:flex;
    align-items:center;
    gap:.65rem;
    padding:.35rem .2rem .55rem;
}
.ez-side-avatar-compact {
    width:38px;
    height:38px;
    flex:0 0 38px;
    border-radius:50%;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:1rem;
    font-weight:900;
    background:rgba(45,180,160,.18);
    border:1px solid rgba(45,180,160,.65);
}
.ez-side-profile-compact .ez-side-name {
    font-size:.94rem;
}
.ez-side-profile-compact .ez-side-role {
    margin-top:.05rem;
    font-size:.72rem;
}
@media(max-width:900px) {
    .ez-topbar {flex-wrap:wrap}
    .ez-topbar-search {order:3; width:100%}
}
</style>
"""


def current_section() -> str:
    pending = st.session_state.get("_pending_main_menu")
    if pending:
        return str(pending)
    return str(st.session_state.get("main_menu", "Répertoire"))


def analysis_sidebar_active() -> bool:
    """Show analysis controls for imports, fresh songs, or explicit edit mode."""
    # Structural analysis is a permanent EZScore invariant.
    st.session_state["setting_sections_enabled"] = True
    st.session_state["setting_section_block_measures"] = 4
    section = current_section()

    if section == "Import":
        return allowed("song.edit")

    if section != "Chanson" or not allowed("song.edit"):
        return False

    active_hash = str(
        st.session_state.get("active_song_hash", "") or ""
    )
    if not active_hash:
        return False

    # R30 baseline fix:
    # a freshly imported song has no persisted analysis yet. It must expose
    # the analysis settings even though the song is opened in Vue mode.
    try:
        with perf_span(
            "ui.analysis_sidebar.load_latest",
            audio_hash=active_hash[:12],
        ):
            latest = load_latest_persisted_analysis(active_hash)
    except Exception as exc:
        perf_event(
            "ui.analysis_sidebar.load_latest",
            status="error",
            audio_hash=active_hash[:12],
            error_type=type(exc).__name__,
            error=str(exc),
        )
        latest = None

    if latest is None:
        perf_event(
            "ui.analysis_sidebar.state",
            audio_hash=active_hash[:12],
            fresh_song=True,
            show_settings=False,
            stem_lab_ui=True,
        )
        # feature/stem-analysis-pipeline:
        # the fresh-song entry point is the STEM_LAB surface, not the legacy
        # technical settings form.
        return False

    mode_key = "song_mode_" + active_hash[:12]
    editing = st.session_state.get(mode_key) == "Édition"

    perf_event(
        "ui.analysis_sidebar.state",
        audio_hash=active_hash[:12],
        fresh_song=False,
        edit_mode=bool(editing),
        stem_lab_ui=True,
    )
    # The STEM pipeline branch no longer exposes the historical technical
    # analyzer as its primary visual surface.
    return False


_SONG_CONTEXT_TABS_SLOT = None


def render_app_header() -> None:
    global _SONG_CONTEXT_TABS_SLOT

    st.markdown(_SHELL_CSS, unsafe_allow_html=True)
    user = current_user()
    if user:
        name = html.escape(str(user.get("display_name") or user.get("email") or "Compte"))
        role = html.escape(str(user.get("role") or "reader"))
        user_label = f"{name} · {role}"
    else:
        user_label = "Visiteur"

    st.markdown(
        f"""
        <div class="ez-topbar">
          <div class="ez-topbar-logo">🎸 EZScore</div>
          <div class="ez-topbar-search">🔎 Rechercher dans le répertoire</div>
          <div class="ez-topbar-user">👤 {user_label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Filled later, when EZScore.py knows the active song.
    # This keeps contextual tabs in the main area, not in the sidebar.
    _SONG_CONTEXT_TABS_SLOT = st.empty()


def _goto(section: str) -> None:
    st.session_state["_pending_main_menu"] = section
    st.rerun()


def render_profile_sidebar() -> None:
    """Render global navigation without stealing space from song controls.

    Répertoire / Compte keep the richer profile presentation. Chanson / Import
    use a compact identity plus a collapsed secondary menu so the contextual
    song controls remain immediately reachable.
    """
    render_perf_log_sidebar()

    section = current_section()
    compact = section in ("Chanson", "Import")
    user = current_user()

    if user:
        name = str(user.get("display_name") or user.get("email") or "Compte")
        role = str(user.get("role") or "reader")
        initial = html.escape(name[:1].upper() if name else "?")
        avatar = avatar_value(user)

        if compact:
            if avatar:
                av_col, name_col = st.sidebar.columns([0.28, 0.72])
                with av_col:
                    st.image(avatar, width=42)
                with name_col:
                    st.markdown(
                        f"**{html.escape(name)}**  \n"
                        f"<small>{html.escape(role)}</small>",
                        unsafe_allow_html=True,
                    )
            else:
                st.sidebar.markdown(
                    f"""
                    <div class="ez-side-profile-compact">
                      <div class="ez-side-avatar-compact">{initial}</div>
                      <div>
                        <div class="ez-side-name">{html.escape(name)}</div>
                        <div class="ez-side-role">{html.escape(role)}</div>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            if avatar:
                st.sidebar.image(avatar, width=76)
                st.sidebar.markdown(
                    f"<div style='text-align:center'>"
                    f"<div class='ez-side-name'>{html.escape(name)}</div>"
                    f"<div class='ez-side-role'>{html.escape(role)}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.sidebar.markdown(
                    f"""
                    <div class="ez-side-profile">
                      <div class="ez-side-avatar">{initial}</div>
                      <div class="ez-side-name">{html.escape(name)}</div>
                      <div class="ez-side-role">{html.escape(role)}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    else:
        if compact:
            st.sidebar.markdown(
                """
                <div class="ez-side-profile-compact">
                  <div class="ez-side-avatar-compact">?</div>
                  <div>
                    <div class="ez-side-name">Visiteur</div>
                    <div class="ez-side-role">accès public</div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.sidebar.markdown(
                """
                <div class="ez-side-profile">
                  <div class="ez-side-avatar">?</div>
                  <div>
                    <div class="ez-side-name">Visiteur</div>
                    <div class="ez-side-role">accès public</div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    if compact:
        quick_col1, quick_col2 = st.sidebar.columns(2)
        with quick_col1:
            if st.button("🎵 Répertoire", key="shell_repertoire", width="stretch"):
                _goto("Répertoire")
        with quick_col2:
            if user:
                if st.button("👤 Profil", key="shell_profile", width="stretch"):
                    _goto("Compte")
            else:
                if st.button("🔐 Connexion", key="shell_login", width="stretch"):
                    _goto("Compte")

        if user:
            with st.sidebar.expander("☰ Navigation", expanded=False):
                if allowed("song.edit"):
                    if st.button(
                        "✏️ Mes éditions",
                        key="shell_edits",
                        width="stretch",
                    ):
                        _goto("Répertoire")
                    if st.button(
                        "⬆️ Importer",
                        key="shell_import",
                        width="stretch",
                    ):
                        _goto("Import")

                if allowed("admin.users"):
                    if st.button(
                        "👥 Utilisateurs & droits",
                        key="shell_admin_users",
                        width="stretch",
                    ):
                        st.session_state["_open_admin_users"] = True
                        _goto("Compte")

                if st.button(
                    "🚪 Déconnexion",
                    key="shell_logout",
                    width="stretch",
                ):
                    logout()
                    _goto("Répertoire")
        return

    if st.sidebar.button("🎵 Répertoire", key="shell_repertoire", width="stretch"):
        _goto("Répertoire")

    if user:
        if st.sidebar.button("👤 Mon profil", key="shell_profile", width="stretch"):
            _goto("Compte")

        if allowed("song.edit"):
            if st.sidebar.button("✏️ Mes éditions", key="shell_edits", width="stretch"):
                _goto("Répertoire")
            if st.sidebar.button("⬆️ Importer", key="shell_import", width="stretch"):
                _goto("Import")

        if allowed("admin.users"):
            st.sidebar.markdown("---")
            st.sidebar.caption("Administration")
            if st.sidebar.button(
                "👥 Utilisateurs & droits",
                key="shell_admin_users",
                width="stretch",
            ):
                st.session_state["_open_admin_users"] = True
                _goto("Compte")

        st.sidebar.markdown("---")
        if st.sidebar.button("🚪 Déconnexion", key="shell_logout", width="stretch"):
            logout()
            _goto("Répertoire")
    else:
        if st.sidebar.button(
            "🔐 Connexion / inscription",
            key="shell_login",
            width="stretch",
        ):
            _goto("Compte")
