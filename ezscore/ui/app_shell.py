"""Application shell: header, profile sidebar and contextual navigation."""

from __future__ import annotations

import html
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
            selected = st.segmented_control(
                "Édition",
                options,
                default=current,
                key=state_key,
                width="stretch",
                label_visibility="collapsed",
            )
        return str(selected or current)

    if work_mode == "Player":
        options = ["Karaoké", "Paroles + accords", "Grille"]
        state_key = _player_tab_key(active_hash)
        current = str(st.session_state.get(state_key, "Karaoké") or "Karaoké")
        if current not in options:
            current = "Karaoké"

        with _SONG_CONTEXT_TABS_SLOT.container():
            selected = st.segmented_control(
                "Player",
                options,
                default=current,
                key=state_key,
                width="stretch",
                label_visibility="collapsed",
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

        if mode_key not in st.session_state:
            st.session_state[mode_key] = _initial_work_mode(
                active_hash,
                legacy_view,
            )

        if allowed("song.edit"):
            mode_options = ["Analyse", "Édition", "Player"]
        else:
            # Registered readers and public viewers do not receive edit/analyse controls.
            mode_options = ["Player"]

        current_mode = str(st.session_state.get(mode_key, mode_options[0]) or mode_options[0])
        if current_mode not in mode_options:
            current_mode = mode_options[0]
            st.session_state[mode_key] = current_mode

        selected_mode = _ORIGINAL_ST_RADIO(
            "Mode",
            mode_options,
            key=mode_key,
            index=mode_options.index(current_mode),
            help=(
                "Analyse = produire/contrôler les données · "
                "Édition = modifier blocs, paroles et grille · "
                "Player = lecture/karaoké."
            ),
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
        if value == (
            "La lecture MIDI synchronisée est disponible dans "
            "Grille > Jouer."
        ):
            return None
    return _ORIGINAL_ST_CAPTION(*args, **kwargs)


st.checkbox = _ezscore_checkbox
st.selectbox = _ezscore_selectbox
st.radio = _ezscore_radio
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
