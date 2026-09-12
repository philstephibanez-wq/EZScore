import streamlit as st
import html
import numpy as np
import librosa
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import tempfile
import os
import sys
import subprocess
import shutil
import sqlite3
import json
import hashlib
import re
import warnings
import time
import base64
import struct
from datetime import datetime, timezone
from pathlib import Path
import torch
import whisper
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
from collections import Counter
from EZScoreTemplate import ScoreTemplateRenderer
from ezscore.midi import (
    MIDI_INSTRUMENTS,
    build_chord_midi_events,
    build_midi_file,
    render_editor_midi_player,
)
from ezscore.timeline import (
    chord_regions as creer_regions_harmoniques,
    create_harmonic_timeline as creer_figure_deroule_riffstation,
    waveform_preview_cache,
)
from ezscore.printing import (
    make_print_document as _make_print_document,
    print_css_text as _print_css_text,
    print_grid_block_height_mm as _print_grid_block_height_mm,
    print_icon as _print_icon,
    print_lyrics_block_height_mm as _print_lyrics_block_height_mm,
    print_paginate_blocks as _print_paginate_blocks,
    print_song_header_html as _print_song_header_html,
)
from ezscore.transcription import (
    construire_bloc_paroles,
    construire_groupes_phonetiques,
    construire_timeline_phonetique,
    detecter_sections_structurelles,
    extraire_mots,
    position_caractere_pour_temps,
)
from ezscore.notation import (
    accord_forme_capo,
    formatter_mesure,
    formatter_mesure_signature,
    normaliser_symboles_mesure,
    preparer_mesures_affichage,
)
from ezscore.persistence import *

# Whisper/CUDA : Triton est optionnel sous Windows.
# Ces warnings indiquent uniquement un fallback plus lent.
warnings.filterwarnings(
    "ignore",
    message=r"Failed to launch Triton kernels.*",
    category=UserWarning,
    module=r"whisper\.timing",
)

SCORE = ScoreTemplateRenderer(Path(__file__).resolve().parent)

# ============================================================
# CHORDSTATION
# ============================================================

st.set_page_config(
    page_title="EZScore",
    page_icon="🎸",
    layout="wide"
)

st.markdown(
    '<div class="app-title">🎸 EZScore — V1.1</div>',
    unsafe_allow_html=True,
)
st.markdown(
    "Analyse d'un morceau : tempo, beats, mesures, accords et paroles synchronisées."
)


st.markdown(
    """
    <style>
    /* =====================================================
       CHORDSTATION V23 — AFFICHAGE COMPACT / IMPRESSION
       ===================================================== */

    /* Réduction des espacements verticaux généraux */
    .block-container {
        padding-top: 2.2rem;
        padding-bottom: 1.2rem;
    }

    .app-title {
        display: block;
        font-size: 1.95rem;
        font-weight: 800;
        line-height: 1.60;
        padding: 1.10rem 0 0.50rem 0;
        margin: 0;
        overflow: visible !important;
        white-space: normal;
        min-height: 3.6rem;
    }

    /* -----------------------------
       GRILLE D'ACCORDS TYPE EXCEL
       ----------------------------- */
    .chord-grid-wrap {
        margin: 0 !important;
        padding: 0 !important;
    }

    .song-structure-block {
        margin: 0 0 1rem 0 !important;
        padding: 0 !important;
        page-break-inside: avoid;
    }

    .song-structure-block:last-child {
        margin-bottom: 0 !important;
    }

    .song-block-title {
        font-size: 0.80rem;
        font-weight: 800;
        color: #4da3ff;
        margin: 0 0 0.22rem 0 !important;
        padding: 0 !important;
        opacity: 1;
    }

    .lyrics-structure-block {
        margin: 0 0 1rem 0 !important;
        padding: 0 !important;
        page-break-inside: avoid;
    }

    .lyrics-structure-block:last-child {
        margin-bottom: 0 !important;
    }


    .catalog-directory {
        margin-top: 0.35rem;
    }

    .catalog-letter-title {
        font-size: 1rem;
        font-weight: 800;
        color: #4da3ff;
        margin: 0.65rem 0 0.30rem 0;
    }

    .catalog-song-row {
        display: grid;
        grid-template-columns: minmax(0, 1fr) minmax(0, 0.9fr);
        gap: 1rem;
        align-items: center;
        padding: 0.42rem 0.55rem;
        border-bottom: 1px solid rgba(120, 130, 145, 0.20);
        line-height: 1.15;
    }

    .catalog-song-row.current {
        background: rgba(77, 163, 255, 0.10);
        border-left: 3px solid #4da3ff;
    }

    .catalog-primary {
        font-weight: 700;
    }

    .catalog-secondary {
        opacity: 0.78;
    }

    .catalog-status-line {
        display: flex;
        flex-wrap: wrap;
        gap: 0.32rem;
        margin-top: 0.24rem;
        line-height: 1.1;
    }

    .catalog-status-badge {
        display: inline-flex;
        align-items: center;
        padding: 0.16rem 0.42rem;
        border-radius: 999px;
        border: 1px solid rgba(140, 150, 165, 0.32);
        font-size: 0.76rem;
        font-weight: 700;
        white-space: nowrap;
    }

    .catalog-status-analyzed {
        background: rgba(46, 157, 87, 0.11);
        border-color: rgba(46, 157, 87, 0.46);
    }

    .catalog-status-working {
        background: rgba(230, 167, 0, 0.11);
        border-color: rgba(230, 167, 0, 0.48);
    }

    .catalog-status-validated {
        background: rgba(77, 163, 255, 0.11);
        border-color: rgba(77, 163, 255, 0.46);
    }

    .catalog-status-published {
        background: rgba(132, 91, 194, 0.12);
        border-color: rgba(132, 91, 194, 0.50);
    }

    .catalog-status-pending {
        opacity: 0.76;
    }

    .block-live-preview {
        max-height: 72vh;
        overflow-y: auto;
        padding: 0.55rem 0.70rem;
        border: 1px solid rgba(120, 130, 145, 0.28);
        border-radius: 8px;
        background: rgba(120, 130, 145, 0.035);
    }

    .block-live-preview-caption {
        font-size: 0.82rem;
        opacity: 0.72;
        margin: 0 0 0.60rem 0;
    }

    .block-live-card {
        border-left: 3px solid rgba(77, 163, 255, 0.72);
        padding: 0.28rem 0 0.46rem 0.70rem;
        margin: 0 0 0.85rem 0;
        background: rgba(77, 163, 255, 0.035);
    }

    .block-live-title {
        font-size: 1.02rem;
        font-weight: 800;
        color: #4da3ff;
        margin: 0 0 0.36rem 0;
    }

    .block-live-range {
        font-size: 0.74rem;
        font-weight: 600;
        opacity: 0.62;
        margin-left: 0.35rem;
    }

    .block-live-line {
        margin: 0 0 0.38rem 0;
        padding: 0;
        overflow-x: auto;
    }

    .block-live-chords,
    .block-live-text {
        white-space: pre;
        font-family: Consolas, "Courier New", ui-monospace, monospace;
        letter-spacing: 0;
        font-variant-ligatures: none;
        margin: 0;
        padding: 0;
    }

    .block-live-chords {
        font-size: 1.00rem;
        font-weight: 800;
        line-height: 1.05;
    }

    .block-live-text {
        font-size: 1.08rem;
        font-weight: 520;
        line-height: 1.12;
    }

    .block-live-instrumental {
        opacity: 0.58;
        font-size: 0.90rem;
    }

    .lyrics-block-title {
        font-size: 1.85rem;
        font-weight: 820;
        color: #4da3ff;
        margin: 0.50rem 0 0.42rem 0 !important;
        padding: 0 !important;
        line-height: 1.05;
    }

    .chord-grid-table {
        width: 100%;
        border-collapse: collapse !important;
        border-spacing: 0 !important;
        table-layout: fixed;
        margin: 0 !important;
    }

    .chord-grid-table th,
    .chord-grid-table td {
        border: 1px solid #5b6068;
        padding: 0.42rem 0.35rem;
        text-align: center;
        vertical-align: middle;
        line-height: 1.15;
        margin: 0 !important;
    }

    .chord-grid-table th {
        font-size: 0.78rem;
        font-weight: 600;
        background: rgba(120, 130, 145, 0.12);
    }

    .chord-grid-table td {
        font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
        font-size: 1rem;
        font-weight: 700;
        min-height: 2.3rem;
    }

    /* -----------------------------
       PAROLES + ACCORDS CONTINUS
       ----------------------------- */
    .lyrics-sheet {
        margin: 0 !important;
        padding: 0 !important;
    }

    .lyrics-line {
        margin: 0 !important;
        padding: 0.42rem 0.44rem 0.48rem 0.44rem !important;
        border-bottom: 1px solid rgba(120, 130, 145, 0.22);
        line-height: 1.02;
        page-break-inside: avoid;
        overflow-x: auto;
    }

    .lyrics-chords,
    .lyrics-text {
        white-space: pre;
        font-family: Consolas, "Courier New", ui-monospace, monospace;
        letter-spacing: 0;
        font-variant-ligatures: none;
        margin: 0 !important;
        padding: 0 !important;
        tab-size: 4;
    }

    .lyrics-chords {
        font-size: 2.15rem;
        font-weight: 820;
        line-height: 0.98;
        margin-bottom: 0.22rem !important;
    }

    .lyrics-text {
        font-size: 2.35rem;
        font-weight: 520;
        line-height: 1.02;
        overflow-x: auto;
    }

    /* Neutraliser les marges des conteneurs HTML générés */
    div[data-testid="stVerticalBlock"] > div:has(.chord-grid-wrap),
    div[data-testid="stVerticalBlock"] > div:has(.lyrics-sheet) {
        gap: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    /* -----------------------------
       PRÉPARATION IMPRESSION
       ----------------------------- */
    @media print {
        header,
        footer,
        [data-testid="stSidebar"],
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        button {
            display: none !important;
        }

        .block-container {
            max-width: none !important;
            padding: 0 !important;
            margin: 0 !important;
        }

        .chord-grid-table th,
        .chord-grid-table td {
            color: #000 !important;
            border-color: #000 !important;
            background: #fff !important;
        }

        .lyrics-line,
        .lyrics-chords,
        .lyrics-text {
            color: #000 !important;
            background: #fff !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# CONFIGURATION
# ============================================================

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

def demucs_disponible():
    try:
        import importlib.util
        return importlib.util.find_spec("demucs") is not None
    except Exception:
        return False



# Analyse musicale optimisée
ANALYSE_SR = 22050
HOP_LENGTH = 2048
BEATS_PAR_MESURE = 4

# Détection prudente d'un beat non joué
SILENCE_RMS_RATIO = 0.22
SILENCE_CHROMA_RATIO = 0.18

# Détection très conservative d'un point d'orgue
FERMATA_GAP_RATIO = 1.85
FERMATA_MIN_CONFIDENCE = 0.70

if DEVICE == "cuda":
    st.sidebar.success(f"🚀 GPU actif : {torch.cuda.get_device_name(0)}")
    st.sidebar.write(f"PyTorch : {torch.__version__}")
    st.sidebar.write(f"CUDA : {torch.version.cuda}")
else:
    st.sidebar.info("ℹ️ Mode CPU actif")
    st.sidebar.write(f"PyTorch : {torch.__version__}")

if demucs_disponible():
    st.sidebar.success("🎚️ Demucs : disponible")
else:
    st.sidebar.warning("🎚️ Demucs : non installé")

st.sidebar.caption(
    "Notation : '-' = tenue · '.' = beat non joué · '^' = point d'orgue détecté"
)


# ============================================================
# RÉGLAGES UTILISATEUR
# ============================================================

# Les paramètres d'un morceau ouvert depuis le répertoire doivent être
# injectés AVANT l'instanciation des widgets Streamlit.
_pending_analysis_settings = st.session_state.pop(
    "_pending_analysis_settings",
    None,
)

if _pending_analysis_settings:
    _pending_mapping = {
        "setting_signature_mode": _pending_analysis_settings.get(
            "signature_mode",
            "Auto",
        ),
        "setting_analyse_sr": int(
            _pending_analysis_settings.get("analyse_sr", 22050)
        ),
        "setting_hop_length": int(
            _pending_analysis_settings.get("hop_length", 2048)
        ),
        "setting_silence_rms": float(
            _pending_analysis_settings.get(
                "silence_rms_ratio",
                0.22,
            )
        ),
        "setting_silence_chroma": float(
            _pending_analysis_settings.get(
                "silence_chroma_ratio",
                0.18,
            )
        ),
        "setting_poids_fondamentale": float(
            _pending_analysis_settings.get(
                "poids_fondamentale",
                0.22,
            )
        ),
        "setting_fermata_enabled": bool(
            _pending_analysis_settings.get(
                "fermata_enabled",
                True,
            )
        ),
        "setting_fermata_gap": float(
            _pending_analysis_settings.get(
                "fermata_gap_ratio",
                1.85,
            )
        ),
    }

    for _setting_key, _setting_value in _pending_mapping.items():
        st.session_state[_setting_key] = _setting_value

# Préférences persistantes propres au morceau.
# Elles sont préparées au clic "Ouvrir" puis injectées ici, AVANT
# l'instanciation des widgets Streamlit.
_pending_song_preferences = st.session_state.pop(
    "_pending_song_preferences",
    None,
)

if _pending_song_preferences:
    _pref_settings = dict(
        _pending_song_preferences.get("settings", {}) or {}
    )

    _preference_mapping = {
        "capo_live": int(
            _pending_song_preferences.get("capo", 0) or 0
        ),
        "setting_signature_mode": _pref_settings.get(
            "signature_mode",
            st.session_state.get("setting_signature_mode", "Auto"),
        ),
        "setting_analyse_sr": int(
            _pref_settings.get(
                "analyse_sr",
                st.session_state.get("setting_analyse_sr", 22050),
            )
        ),
        "setting_hop_length": int(
            _pref_settings.get(
                "hop_length",
                st.session_state.get("setting_hop_length", 2048),
            )
        ),
        "setting_silence_rms": float(
            _pref_settings.get(
                "silence_rms_ratio",
                st.session_state.get("setting_silence_rms", 0.22),
            )
        ),
        "setting_silence_chroma": float(
            _pref_settings.get(
                "silence_chroma_ratio",
                st.session_state.get("setting_silence_chroma", 0.18),
            )
        ),
        "setting_poids_fondamentale": float(
            _pref_settings.get(
                "poids_fondamentale",
                st.session_state.get("setting_poids_fondamentale", 0.22),
            )
        ),
        "setting_fermata_enabled": bool(
            _pref_settings.get(
                "fermata_enabled",
                st.session_state.get("setting_fermata_enabled", True),
            )
        ),
        "setting_fermata_gap": float(
            _pref_settings.get(
                "fermata_gap_ratio",
                st.session_state.get("setting_fermata_gap", 1.85),
            )
        ),
        "setting_sections_enabled": bool(
            _pref_settings.get("sections_enabled", True)
        ),
        "setting_section_block_measures": int(
            _pref_settings.get("section_block_measures", 4)
        ),
        "setting_section_similarity": float(
            _pref_settings.get("section_similarity", 0.66)
        ),
    }

    for _setting_key, _setting_value in _preference_mapping.items():
        st.session_state[_setting_key] = _setting_value

# Valeurs par défaut uniquement si aucune restauration n'a déjà alimenté
# Session State. Cela évite les warnings Streamlit "default value + Session State".
_widget_defaults = {
    "capo_live": 0,
    "setting_signature_mode": "Auto",
    "setting_analyse_sr": 22050,
    "setting_hop_length": 2048,
    "setting_silence_rms": 0.22,
    "setting_silence_chroma": 0.18,
    "setting_poids_fondamentale": 0.22,
    "setting_fermata_enabled": True,
    "setting_fermata_gap": 1.85,
    "setting_sections_enabled": True,
    "setting_section_block_measures": 4,
    "setting_section_similarity": 0.66,
}

for _widget_key, _widget_default in _widget_defaults.items():
    if _widget_key not in st.session_state:
        st.session_state[_widget_key] = _widget_default

# Le capo est volontairement HORS du formulaire :
# il ne déclenche aucune nouvelle analyse harmonique.
# Streamlit rerend immédiatement la présentation en utilisant les résultats
# déjà en cache.
capo_user = st.sidebar.selectbox(
    "🎸 Capodastre",
    list(range(0, 13)),
    key="capo_live",
    format_func=lambda x: "0 — sans capo" if x == 0 else f"Capo {x}",
    help=(
        "Affichage uniquement. L'audio, la tonalité réelle et les accords "
        "internes restent inchangés. Exemple : Cm réel + capo 3 => Am affiché."
    )
)

st.sidebar.caption(
    "Le capodastre modifie l'affichage immédiatement, sans relancer Demucs, "
    "Whisper ni l'analyse harmonique."
)

with st.sidebar.expander("⚙️ Réglages avancés", expanded=False):
    with st.form("chordstation_settings"):
        signature_mode = st.selectbox(
            "Signature rythmique",
            [
                "Auto",
                "2/4",
                "4/4",
                "3/4",
                "6/8",
                "12/8",
                "5/4",
                "7/8",
            ],
            key="setting_signature_mode",
            help=(
                "Auto tente d'estimer la signature. "
                "Le résultat reste éditable."
            )
        )

        analyse_sr_user = st.selectbox(
            "Fréquence d'analyse",
            [11025, 22050, 44100],
            key="setting_analyse_sr",
            format_func=lambda x: f"{x} Hz"
        )

        hop_length_user = st.selectbox(
            "Hop length",
            [512, 1024, 2048, 4096],
            key="setting_hop_length"
        )

        silence_rms_user = st.slider(
            "Seuil silence RMS",
            min_value=0.05,
            max_value=0.60,
            step=0.01,
            key="setting_silence_rms"
        )

        silence_chroma_user = st.slider(
            "Seuil silence harmonique",
            min_value=0.05,
            max_value=0.60,
            step=0.01,
            key="setting_silence_chroma"
        )

        poids_fondamentale_user = st.slider(
            "Poids de la fondamentale",
            min_value=0.10,
            max_value=0.45,
            step=0.01,
            key="setting_poids_fondamentale",
            help=(
                "10 % = accompagnement très dominant ; "
                "45 % = la fondamentale grave pèse davantage. "
                "La basse ne prend jamais le contrôle total."
            )
        )

        fermata_enabled_user = st.checkbox(
            "Détection point d'orgue",
            key="setting_fermata_enabled"
        )

        fermata_gap_user = st.slider(
            "Seuil point d'orgue (× durée beat)",
            min_value=1.20,
            max_value=3.00,
            step=0.05,
            key="setting_fermata_gap"
        )

        st.markdown("---")
        st.caption("Structure du morceau")

        sections_enabled_user = st.checkbox(
            "Détection Verse / Chorus / Bridge",
            key="setting_sections_enabled",
        )

        section_block_measures_user = st.selectbox(
            "Taille de bloc structurel",
            [2, 4, 8],
            key="setting_section_block_measures",
            format_func=lambda x: f"{x} mesures",
            help=(
                "4 mesures est un bon compromis. "
                "8 mesures est plus stable mais moins précis."
            )
        )

        section_similarity_user = st.slider(
            "Sensibilité répétition de section",
            min_value=0.45,
            max_value=0.90,
            step=0.01,
            key="setting_section_similarity",
            help=(
                "Plus bas = davantage de blocs regroupés. "
                "Plus haut = détection plus stricte."
            )
        )

        appliquer_reglages = st.form_submit_button(
            "Appliquer les paramètres"
        )

st.sidebar.caption(
    "« Appliquer les paramètres » mémorise les réglages du morceau et "
    "lance l'analyse avec ces valeurs. Le capo est mémorisé immédiatement "
    "et ne relance jamais l'analyse."
)

# Zone réservée à la progression d'analyse.
# Elle reste visible quelle que soit la vue active.
analysis_progress_slot = st.sidebar.container()


# ============================================================
# WHISPER
# ============================================================

@st.cache_resource
def charger_modele_whisper(device):
    return whisper.load_model("small", device=device)


# ============================================================
# OUTILS
# ============================================================

def creer_fichier_temporaire(audio_bytes, extension):
    f = tempfile.NamedTemporaryFile(delete=False, suffix=extension)
    try:
        f.write(audio_bytes)
        return f.name
    finally:
        f.close()


def creer_templates_accords():
    noms_notes = [
        "C", "C#", "D", "D#", "E", "F",
        "F#", "G", "G#", "A", "A#", "B"
    ]

    accords = []
    templates = []

    for i in range(12):
        majeur = np.zeros(12)
        majeur[i] = 1.0
        majeur[(i + 4) % 12] = 1.0
        majeur[(i + 7) % 12] = 1.0
        templates.append(majeur)
        accords.append(noms_notes[i])

        mineur = np.zeros(12)
        mineur[i] = 1.0
        mineur[(i + 3) % 12] = 1.0
        mineur[(i + 7) % 12] = 1.0
        templates.append(mineur)
        accords.append(f"{noms_notes[i]}m")

    templates = np.asarray(templates, dtype=np.float32)
    templates /= np.linalg.norm(templates, axis=1, keepdims=True) + 1e-12
    return templates, accords



# ============================================================
# TONALITÉ / PRIOR HARMONIQUE
# ============================================================

_KK_MAJOR = np.array(
    [6.35, 2.23, 3.48, 2.33, 4.38, 4.09,
     2.52, 5.19, 2.39, 3.66, 2.29, 2.88],
    dtype=float
)

_KK_MINOR = np.array(
    [6.33, 2.68, 3.52, 5.38, 2.60, 3.53,
     2.54, 4.75, 3.98, 2.69, 3.34, 3.17],
    dtype=float
)


def estimer_tonalite(chroma):
    profil = np.mean(chroma, axis=1).astype(float)
    profil -= profil.mean()

    candidats = []

    for tonique in range(12):
        maj = np.roll(_KK_MAJOR, tonique)
        min_ = np.roll(_KK_MINOR, tonique)

        maj = maj - maj.mean()
        min_ = min_ - min_.mean()

        denom_maj = np.linalg.norm(profil) * np.linalg.norm(maj) + 1e-12
        denom_min = np.linalg.norm(profil) * np.linalg.norm(min_) + 1e-12

        score_maj = float(np.dot(profil, maj) / denom_maj)
        score_min = float(np.dot(profil, min_) / denom_min)

        candidats.append((score_maj, tonique, "major"))
        candidats.append((score_min, tonique, "minor"))

    candidats.sort(reverse=True, key=lambda x: x[0])

    meilleur = candidats[0]
    second = candidats[1]

    confiance = max(
        0.0,
        min(1.0, (meilleur[0] - second[0]) / 0.18)
    )

    return {
        "score": meilleur[0],
        "root": meilleur[1],
        "mode": meilleur[2],
        "confidence": confiance,
    }


def creer_prior_accords(tonalite, dictionnaire_accords):
    root = tonalite["root"]
    mode = tonalite["mode"]
    confiance = tonalite["confidence"]

    force = 0.35 + 0.65 * confiance

    if mode == "minor":
        accords_forts = {
            ((root + 0) % 12, True),   # i
            ((root + 3) % 12, False),  # III
            ((root + 5) % 12, True),   # iv
            ((root + 7) % 12, True),   # v
            ((root + 7) % 12, False),  # V harmonique
            ((root + 8) % 12, False),  # VI
            ((root + 10) % 12, False), # VII
        }
        racines_gamme = {
            (root + x) % 12
            for x in (0, 2, 3, 5, 7, 8, 10)
        }
    else:
        accords_forts = {
            ((root + 0) % 12, False),  # I
            ((root + 2) % 12, True),   # ii
            ((root + 4) % 12, True),   # iii
            ((root + 5) % 12, False),  # IV
            ((root + 7) % 12, False),  # V
            ((root + 9) % 12, True),   # vi
        }
        racines_gamme = {
            (root + x) % 12
            for x in (0, 2, 4, 5, 7, 9, 11)
        }

    prior = np.ones(len(dictionnaire_accords), dtype=float)

    for idx in range(len(dictionnaire_accords)):
        racine = idx // 2
        mineur = bool(idx % 2)

        if (racine, mineur) in accords_forts:
            cible = 1.00
        elif racine in racines_gamme:
            cible = 0.62
        else:
            cible = 0.30

        prior[idx] = (1.0 - force) + force * cible

    return prior


def nom_tonalite(tonalite):
    noms = [
        "C", "C#", "D", "D#", "E", "F",
        "F#", "G", "G#", "A", "A#", "B"
    ]
    suffixe = "m" if tonalite["mode"] == "minor" else ""
    return f"{noms[tonalite['root']]}{suffixe}"




# ============================================================
# ANALYSE MUSICALE
# ============================================================



def detecter_signature_tentative(
    y_perc,
    sr,
    hop_length,
    beat_frames,
):
    """
    Estimation TENTATIVE de la signature métrique à partir des accents.

    Hypothèses testées :
      2/4, 3/4, 4/4, 5/4, 6/8, 7/8, 12/8

    Important :
    - ce n'est pas une vérité absolue ;
    - 3/4 et 6/8 peuvent être ambigus ;
    - le résultat est affiché avec un score de confiance ;
    - l'utilisateur peut forcer la signature dans les réglages.
    """
    if len(beat_frames) < 12:
        return {
            "signature": "4/4",
            "beats_par_mesure": 4,
            "confiance": 0.0,
            "phase": 0,
            "scores": {},
        }

    onset_env = librosa.onset.onset_strength(
        y=y_perc,
        sr=sr,
        hop_length=hop_length
    )

    frames = np.asarray(beat_frames, dtype=int)
    frames = np.clip(frames, 0, len(onset_env) - 1)

    strengths = onset_env[frames].astype(np.float64)

    # Normalisation robuste des accents.
    median = float(np.median(strengths))
    mad = float(np.median(np.abs(strengths - median))) + 1e-12
    z = (strengths - median) / mad

    hypotheses = {
        "2/4": 2,
        "3/4": 3,
        "4/4": 4,
        "5/4": 5,
        "6/8": 6,
        "7/8": 7,
        "12/8": 12,
    }

    results = {}

    for signature, n in hypotheses.items():
        best_score = -1e100
        best_phase = 0

        for phase in range(n):
            positions = np.arange(len(z))
            down_mask = ((positions - phase) % n) == 0

            if np.sum(down_mask) < 2:
                continue

            down = z[down_mask]
            other = z[~down_mask]

            accent_score = (
                float(np.mean(down))
                - float(np.mean(other))
            )

            # Périodicité des accents à n beats.
            if len(z) > n:
                a = z[:-n]
                b = z[n:]
                denom = (
                    np.linalg.norm(a)
                    * np.linalg.norm(b)
                    + 1e-12
                )
                periodicite = float(np.dot(a, b) / denom)
            else:
                periodicite = 0.0

            score = (
                0.72 * accent_score
                + 0.28 * periodicite
            )

            # 2/4 : on cherche une alternance fort/faible simple.
            if signature == "2/4":
                pair_positions = (positions - phase) % 2
                strong_mask = pair_positions == 0
                weak_mask = pair_positions == 1

                if np.any(strong_mask) and np.any(weak_mask):
                    simple_duple = (
                        float(np.mean(z[strong_mask]))
                        - float(np.mean(z[weak_mask]))
                    )
                    score += 0.18 * simple_duple

            # Mètres composés : chercher les sous-accents ternaires.
            if signature in ("6/8", "12/8"):
                group_positions = (positions - phase) % n

                if signature == "6/8":
                    secondary_mask = group_positions == 3
                else:
                    secondary_mask = np.isin(
                        group_positions,
                        [3, 6, 9]
                    )

                if np.any(secondary_mask):
                    secondary = float(
                        np.mean(z[secondary_mask])
                    )
                    score += 0.16 * secondary

            if score > best_score:
                best_score = score
                best_phase = phase

        results[signature] = {
            "score": float(best_score),
            "phase": int(best_phase),
            "beats_par_mesure": n,
        }

    ranked = sorted(
        results.items(),
        key=lambda item: item[1]["score"],
        reverse=True
    )

    best_sig, best = ranked[0]

    if len(ranked) > 1:
        second_score = ranked[1][1]["score"]
    else:
        second_score = best["score"]

    margin = best["score"] - second_score

    # Confiance volontairement prudente.
    confiance = float(
        np.clip(
            0.5 + margin / 1.5,
            0.0,
            1.0
        )
    )

    return {
        "signature": best_sig,
        "beats_par_mesure": best["beats_par_mesure"],
        "confiance": confiance,
        "phase": best["phase"],
        "scores": {
            sig: round(data["score"], 3)
            for sig, data in results.items()
        },
    }



def proposer_grille_rythmique_doublee(
    y_perc,
    sr,
    hop_length,
    beat_frames,
    tempo,
    signature_mode,
    signature_initiale,
):
    """
    R11 — teste une ambiguïté d'octave du beat tracker.

    Cas visé :
        ~80 BPM + 2/4 détecté
    alors que le signal porte une pulsation intermédiaire stable pouvant
    correspondre à ~160 BPM + 4/4.

    La grille n'est doublée que si :
    - la signature est en Auto ;
    - le tempo brut est dans une zone prudente ;
    - la signature brute est 2/4 ;
    - les milieux entre beats portent réellement des attaques récurrentes ;
    - la grille doublée produit une hypothèse 4/4 exploitable.
    """
    frames = np.asarray(beat_frames, dtype=int)

    result = {
        "accepted": False,
        "reason": "not_candidate",
        "raw_tempo": float(tempo),
        "effective_tempo": float(tempo),
        "midpoint_strength_ratio": 0.0,
        "midpoint_coverage": 0.0,
        "raw_signature": str(signature_initiale.get("signature", "?")),
        "effective_signature": str(signature_initiale.get("signature", "?")),
        "raw_beat_count": int(len(frames)),
        "effective_beat_count": int(len(frames)),
        "signature_candidate": None,
    }

    if (
        signature_mode != "Auto"
        or len(frames) < 12
        or not (55.0 <= float(tempo) <= 105.0)
        or str(signature_initiale.get("signature", "")) != "2/4"
    ):
        return frames, float(tempo), signature_initiale, result

    midpoint_frames = []
    for left, right in zip(frames[:-1], frames[1:]):
        if right - left < 2:
            continue
        midpoint = int(round((int(left) + int(right)) / 2.0))
        if midpoint > int(left) and midpoint < int(right):
            midpoint_frames.append(midpoint)

    if len(midpoint_frames) < 8:
        result["reason"] = "not_enough_midpoints"
        return frames, float(tempo), signature_initiale, result

    onset_env = librosa.onset.onset_strength(
        y=y_perc,
        sr=sr,
        hop_length=hop_length,
    )

    beat_idx = np.clip(
        frames,
        0,
        max(len(onset_env) - 1, 0),
    )
    mid_idx = np.clip(
        np.asarray(midpoint_frames, dtype=int),
        0,
        max(len(onset_env) - 1, 0),
    )

    beat_strengths = onset_env[beat_idx].astype(np.float64)
    midpoint_strengths = onset_env[mid_idx].astype(np.float64)

    beat_reference = float(
        np.median(beat_strengths[beat_strengths > 0])
    ) if np.any(beat_strengths > 0) else 0.0

    midpoint_reference = float(
        np.median(midpoint_strengths[midpoint_strengths > 0])
    ) if np.any(midpoint_strengths > 0) else 0.0

    strength_ratio = (
        midpoint_reference / (beat_reference + 1e-12)
        if beat_reference > 0
        else 0.0
    )

    threshold = 0.42 * beat_reference
    midpoint_coverage = (
        float(np.mean(midpoint_strengths >= threshold))
        if beat_reference > 0 and len(midpoint_strengths)
        else 0.0
    )

    doubled = []
    for i, frame in enumerate(frames):
        doubled.append(int(frame))
        if i < len(frames) - 1:
            left = int(frame)
            right = int(frames[i + 1])
            midpoint = int(round((left + right) / 2.0))
            if left < midpoint < right:
                doubled.append(midpoint)

    doubled = np.asarray(sorted(set(doubled)), dtype=int)

    signature_candidate = detecter_signature_tentative(
        y_perc=y_perc,
        sr=sr,
        hop_length=hop_length,
        beat_frames=doubled,
    )

    candidate_confidence = float(
        signature_candidate.get("confiance", 0.0)
    )
    raw_confidence = float(
        signature_initiale.get("confiance", 0.0)
    )

    signal_support = (
        strength_ratio >= 0.52
        and midpoint_coverage >= 0.58
    )

    metric_support = (
        str(signature_candidate.get("signature", "")) == "4/4"
        and candidate_confidence >= max(0.42, raw_confidence - 0.12)
    )

    result.update({
        "reason": (
            "accepted"
            if signal_support and metric_support
            else "insufficient_signal_or_meter"
        ),
        "midpoint_strength_ratio": float(strength_ratio),
        "midpoint_coverage": float(midpoint_coverage),
        "signature_candidate": signature_candidate,
    })

    if not (signal_support and metric_support):
        return frames, float(tempo), signature_initiale, result

    effective_tempo = float(tempo) * 2.0

    result.update({
        "accepted": True,
        "effective_tempo": effective_tempo,
        "effective_signature": str(
            signature_candidate.get("signature", "4/4")
        ),
        "effective_beat_count": int(len(doubled)),
    })

    return doubled, effective_tempo, signature_candidate, result



def separer_accompagnement_demucs(audio_bytes, extension):
    """
    Sépare uniquement la voix du reste.
    La détection d'accords reste STRICTEMENT celle de la v9.
    """
    if not demucs_disponible():
        raise RuntimeError(
            "Demucs n'est pas installé. "
            "Installe-le avec : python -m pip install -U demucs"
        )

    workdir = tempfile.mkdtemp(prefix="chordstation_demucs_")
    input_path = Path(workdir) / f"input{extension or '.wav'}"
    output_dir = Path(workdir) / "separated"

    input_path.write_bytes(audio_bytes)

    cmd = [
        sys.executable,
        "-m",
        "demucs.separate",
        "--two-stems=vocals",
        "-n",
        "htdemucs",
        "-o",
        str(output_dir),
        str(input_path),
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        details = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(
            "Échec Demucs : "
            + (details[-1600:] if details else "erreur inconnue")
        )

    candidates = list(output_dir.rglob("no_vocals.wav"))
    if not candidates:
        raise RuntimeError("no_vocals.wav introuvable après Demucs.")

    return workdir, str(input_path), str(candidates[0])


@st.cache_data(show_spinner=False)
def analyser_musique_cache(
    audio_bytes,
    extension,
    signature_mode="Auto",
    analyse_sr=22050,
    hop_length=2048,
    silence_rms_ratio=0.22,
    silence_chroma_ratio=0.18,
    poids_fondamentale=0.22,
    fermata_enabled=True,
    fermata_gap_ratio=1.85,
):
    """
    V16 = moteur harmonique V9 inchangé + séparation vocale Demucs.
    Aucune logique d'accord supplémentaire n'est ajoutée.
    """
    workdir = None
    _music_started = time.perf_counter()

    try:
        _demucs_started = time.perf_counter()
        workdir, original_path, accompaniment_path = (
            separer_accompagnement_demucs(
                audio_bytes,
                extension
            )
        )
        _demucs_seconds = time.perf_counter() - _demucs_started
        _rhythm_started = time.perf_counter()

        # Original uniquement pour le rythme / beat tracking.
        y_original, sr = librosa.load(
            original_path,
            sr=analyse_sr,
            mono=True
        )

        # no_vocals uniquement pour l'harmonie.
        y_accomp, sr_accomp = librosa.load(
            accompaniment_path,
            sr=analyse_sr,
            mono=True
        )

        if sr_accomp != sr:
            raise RuntimeError(
                "Sample rates incohérents après séparation Demucs."
            )

        # IMPORTANT : on conserve exactement la logique V9.
        # HPSS du mix original pour les beats.
        _, y_perc = librosa.effects.hpss(y_original)

        # HPSS de no_vocals pour l'harmonie principale.
        y_harm, _ = librosa.effects.hpss(y_accomp)

        # R12 : on conserve aussi une composante harmonique du mix original.
        # Demucs peut parfois retirer une partie utile de la guitare avec la
        # voix. L'ensemble 72 % no_vocals + 28 % mix évite de perdre ces
        # informations sans remettre la voix au premier plan.
        y_harm_mix, _ = librosa.effects.hpss(y_original)

        # Tempo + beats bruts
        tempo, beat_frames = librosa.beat.beat_track(
            y=y_perc,
            sr=sr,
            hop_length=hop_length
        )
        tempo = float(np.asarray(tempo).squeeze())
        tempo_brut = float(tempo)
        beat_frames_bruts = np.asarray(
            beat_frames,
            dtype=int,
        )

        if len(beat_frames_bruts) < 2:
            raise RuntimeError("Pas assez de beats détectés.")

        signature_auto_brute = detecter_signature_tentative(
            y_perc=y_perc,
            sr=sr,
            hop_length=hop_length,
            beat_frames=beat_frames_bruts,
        )

        (
            beat_frames,
            tempo,
            signature_auto,
            beat_grid_refinement,
        ) = proposer_grille_rythmique_doublee(
            y_perc=y_perc,
            sr=sr,
            hop_length=hop_length,
            beat_frames=beat_frames_bruts,
            tempo=tempo_brut,
            signature_mode=signature_mode,
            signature_initiale=signature_auto_brute,
        )

        beat_times = librosa.frames_to_time(
            beat_frames,
            sr=sr,
            hop_length=hop_length
        )

        if len(beat_times) < 2:
            raise RuntimeError("Pas assez de beats détectés.")

        signature_map = {
            "2/4": 2,
            "4/4": 4,
            "3/4": 3,
            "6/8": 6,
            "12/8": 12,
            "5/4": 5,
            "7/8": 7,
        }

        if signature_mode == "Auto":
            signature_effective = signature_auto["signature"]
            beats_par_mesure = signature_auto["beats_par_mesure"]
        else:
            signature_effective = signature_mode
            beats_par_mesure = signature_map[signature_mode]

        _rhythm_seconds = time.perf_counter() - _rhythm_started
        _harmony_started = time.perf_counter()

        # R12 : deux vues harmoniques du même signal.
        chroma_accomp = librosa.feature.chroma_cqt(
            y=y_harm,
            sr=sr,
            hop_length=hop_length
        )
        chroma_mix = librosa.feature.chroma_cqt(
            y=y_harm_mix,
            sr=sr,
            hop_length=hop_length
        )

        fondamentale_accomp = librosa.feature.chroma_cqt(
            y=y_harm,
            sr=sr,
            hop_length=hop_length,
            fmin=librosa.note_to_hz("E1"),
            n_octaves=2,
        )
        fondamentale_mix = librosa.feature.chroma_cqt(
            y=y_harm_mix,
            sr=sr,
            hop_length=hop_length,
            fmin=librosa.note_to_hz("E1"),
            n_octaves=2,
        )

        # Les sorties Demucs et mix original peuvent différer de quelques
        # frames. On tronque uniquement à la zone réellement commune.
        common_frames = min(
            chroma_accomp.shape[1],
            chroma_mix.shape[1],
            fondamentale_accomp.shape[1],
            fondamentale_mix.shape[1],
        )
        chroma_accomp = chroma_accomp[:, :common_frames]
        chroma_mix = chroma_mix[:, :common_frames]
        fondamentale_accomp = fondamentale_accomp[:, :common_frames]
        fondamentale_mix = fondamentale_mix[:, :common_frames]

        chroma_accomp_norm = librosa.util.normalize(
            chroma_accomp,
            axis=0,
        )
        chroma_mix_norm = librosa.util.normalize(
            chroma_mix,
            axis=0,
        )
        fondamentale_accomp_norm = librosa.util.normalize(
            fondamentale_accomp,
            axis=0,
        )
        fondamentale_mix_norm = librosa.util.normalize(
            fondamentale_mix,
            axis=0,
        )

        chroma_norm = librosa.util.normalize(
            0.72 * chroma_accomp_norm
            + 0.28 * chroma_mix_norm,
            axis=0,
        )
        fondamentale_norm = librosa.util.normalize(
            0.78 * fondamentale_accomp_norm
            + 0.22 * fondamentale_mix_norm,
            axis=0,
        )

        # `chroma` reste le signal de référence pour la tonalité et les
        # diagnostics, mais représente maintenant l'ensemble harmonique.
        chroma = (
            0.72 * chroma_accomp
            + 0.28 * chroma_mix
        )

        templates, dictionnaire_accords = creer_templates_accords()

        tonalite = estimer_tonalite(chroma)
        prior_accords = creer_prior_accords(
            tonalite,
            dictionnaire_accords
        )

        # Évidence de l'accompagnement : triades sur le spectre harmonique.
        scores_accompagnement = np.dot(
            templates,
            chroma_norm
        )
        scores_accompagnement = np.maximum(
            scores_accompagnement,
            1e-8
        )
        scores_accompagnement /= scores_accompagnement.sum(
            axis=0,
            keepdims=True
        )

        # Évidence de fondamentale : la racine uniquement dans le grave.
        # Majeur et mineur partagent ici la même racine ; la qualité de
        # l'accord reste déterminée par l'accompagnement.
        scores_fondamentale = np.zeros_like(
            scores_accompagnement
        )
        for chord_idx in range(len(dictionnaire_accords)):
            root = chord_idx // 2
            scores_fondamentale[chord_idx] = fondamentale_norm[root]

        scores_fondamentale = np.maximum(
            scores_fondamentale,
            1e-8
        )
        scores_fondamentale /= scores_fondamentale.sum(
            axis=0,
            keepdims=True
        )

        poids_fondamentale = float(
            np.clip(poids_fondamentale, 0.10, 0.45)
        )
        poids_accompagnement = 1.0 - poids_fondamentale

        scores = (
            poids_accompagnement * scores_accompagnement
            + poids_fondamentale * scores_fondamentale
        )
        scores = np.maximum(scores, 1e-8)
        scores /= scores.sum(axis=0, keepdims=True)

        # Prior tonal doux : on pénalise les accords chromatiques faibles,
        # mais on ne les interdit jamais.
        scores *= prior_accords[:, None]
        scores /= scores.sum(axis=0, keepdims=True)

        # La décision harmonique est désormais effectuée directement
        # sur les probabilités agrégées par beat. Le Viterbi frame-level
        # a été retiré : il était soit trop collant, soit trop instable
        # selon son réglage.

        # Indices d'activité harmonique pour distinguer '.' d'une tenue
        rms_harm = librosa.feature.rms(
            y=y_harm,
            frame_length=4096,
            hop_length=hop_length
        )[0]

        chroma_strength = np.sum(chroma, axis=0)

        rms_median = float(np.median(rms_harm[rms_harm > 0])) if np.any(rms_harm > 0) else 0.0
        chroma_median = (
            float(np.median(chroma_strength[chroma_strength > 0]))
            if np.any(chroma_strength > 0)
            else 0.0
        )

        beat_intervals = np.diff(beat_times)
        median_interval = (
            float(np.median(beat_intervals))
            if len(beat_intervals)
            else (60.0 / tempo if tempo > 0 else 0.5)
        )

        # ----------------------------------------------------
        # Analyse harmonique PAR BEAT
        #
        # Important :
        # on ne décide plus immédiatement un accord à chaque beat.
        # On collecte d'abord les probabilités harmoniques de tous
        # les beats, puis on les lisse légèrement dans le temps.
        #
        # Objectif :
        #   Am Am Em Em  -> Am-Em-
        #
        # sans générer :
        #   Am C Em A
        # sur quatre beats à cause de petites fluctuations locales.
        # ----------------------------------------------------

        beat_infos = []
        beat_score_rows = []

        for i, beat_time in enumerate(beat_times):
            if i + 1 < len(beat_times):
                beat_end = float(beat_times[i + 1])
            else:
                beat_end = float(beat_time + median_interval)

            frame_start = int(librosa.time_to_frames(
                beat_time,
                sr=sr,
                hop_length=hop_length
            ))
            frame_end = int(librosa.time_to_frames(
                beat_end,
                sr=sr,
                hop_length=hop_length
            ))

            frame_start = max(0, min(frame_start, scores.shape[1] - 1))
            frame_end = max(frame_start + 1, min(frame_end, scores.shape[1]))

            # Probabilité harmonique moyenne du beat.
            beat_scores = np.mean(
                scores[:, frame_start:frame_end],
                axis=1
            ).astype(np.float64)

            beat_scores = np.maximum(beat_scores, 1e-12)
            beat_scores /= beat_scores.sum()

            # Activité harmonique locale pour détecter les vrais "."
            r0 = max(0, min(frame_start, len(rms_harm) - 1))
            r1 = max(r0 + 1, min(frame_end, len(rms_harm)))
            c0 = max(0, min(frame_start, len(chroma_strength) - 1))
            c1 = max(c0 + 1, min(frame_end, len(chroma_strength)))

            rms_local = float(np.mean(rms_harm[r0:r1])) if r1 > r0 else 0.0
            chroma_local = (
                float(np.mean(chroma_strength[c0:c1]))
                if c1 > c0
                else 0.0
            )

            rms_ratio = rms_local / (rms_median + 1e-12)
            chroma_ratio = chroma_local / (chroma_median + 1e-12)

            beat_non_joue = (
                rms_ratio < silence_rms_ratio
                and chroma_ratio < silence_chroma_ratio
            )

            beat_infos.append({
                "index": i,
                "temps": float(beat_time),
                "fin": beat_end,
                "rms_ratio": rms_ratio,
                "chroma_ratio": chroma_ratio,
                "intervalle": beat_end - float(beat_time),
                "silence": beat_non_joue,
            })

            beat_score_rows.append(beat_scores)

        beat_score_matrix = np.vstack(beat_score_rows)

        # ----------------------------------------------------
        # Lissage très léger des probabilités ENTRE beats.
        #
        # [0.20, 0.60, 0.20] :
        # - le beat courant reste dominant ;
        # - un bruit isolé est atténué ;
        # - un vrai changement sur 2 beats (Am Am / Em Em)
        #   reste visible.
        # ----------------------------------------------------

        smoothed_scores = beat_score_matrix.copy()

        if len(smoothed_scores) >= 2:
            if beat_grid_refinement.get("accepted", False):
                center_weight = 0.80
                neighbor_weight = 0.10
            else:
                center_weight = 0.60
                neighbor_weight = 0.20

            for i in range(len(smoothed_scores)):
                total = center_weight * beat_score_matrix[i]
                poids = center_weight

                if i > 0:
                    total += neighbor_weight * beat_score_matrix[i - 1]
                    poids += neighbor_weight

                if i + 1 < len(smoothed_scores):
                    total += neighbor_weight * beat_score_matrix[i + 1]
                    poids += neighbor_weight

                smoothed_scores[i] = total / poids
                smoothed_scores[i] /= smoothed_scores[i].sum()

        # ----------------------------------------------------
        # VOCABULAIRE HARMONIQUE + COUPLE DOMINANT ALTERNÉ
        # ----------------------------------------------------
        # On apprend :
        #   1. les accords récurrents du morceau ;
        #   2. les deux accords dominants ;
        #   3. s'ils forment un vrai motif d'alternance.
        #
        # Exemple attendu sur Suzanne :
        #   Am <-> Em
        #
        # Si cette alternance est réellement présente dans les scores,
        # elle devient une structure privilégiée, sans interdire F/G/C/D...
        # quand l'audio les soutient clairement.

        gagnants_bruts = np.argmax(smoothed_scores, axis=1)

        recurrence = np.bincount(
            gagnants_bruts,
            minlength=len(dictionnaire_accords)
        ).astype(np.float64)

        energie_globale = np.mean(smoothed_scores, axis=0)

        recurrence_norm = recurrence / (recurrence.max() + 1e-12)
        energie_norm = energie_globale / (energie_globale.max() + 1e-12)

        importance_globale = (
            0.58 * recurrence_norm
            + 0.42 * energie_norm
        )

        ordre_vocabulaire = np.argsort(importance_globale)[::-1]
        top_vocabulaire = ordre_vocabulaire[:6]
        top_dominants = ordre_vocabulaire[:2]

        pair_a = int(top_dominants[0])
        pair_b = int(top_dominants[1])
        pair_set = {pair_a, pair_b}

        # ----------------------------------------------------
        # Mesure de couverture / alternance du couple dominant
        # ----------------------------------------------------

        sequence_pair = [
            int(idx)
            for idx in gagnants_bruts
            if int(idx) in pair_set
        ]

        couverture_pair = (
            len(sequence_pair) / max(len(gagnants_bruts), 1)
        )

        transitions_pair = 0
        alternances_pair = 0

        for i in range(1, len(sequence_pair)):
            transitions_pair += 1
            if sequence_pair[i] != sequence_pair[i - 1]:
                alternances_pair += 1

        taux_alternance_pair = (
            alternances_pair / transitions_pair
            if transitions_pair
            else 0.0
        )

        # On considère le couple comme réellement structurant si :
        # - il couvre une part importante du morceau ;
        # - il alterne suffisamment souvent.
        alternance_active = (
            couverture_pair >= 0.48
            and taux_alternance_pair >= 0.28
        )

        # ----------------------------------------------------
        # Prior global
        # ----------------------------------------------------

        # R12 : le contexte global ne doit plus écraser un accord local
        # clairement présent dans l'intro. Il reste un biais doux, pas une
        # décision.
        prior_vocabulaire = np.full(
            len(dictionnaire_accords),
            0.90,
            dtype=np.float64
        )

        prior_vocabulaire[top_vocabulaire] = 1.00

        prior_vocabulaire[pair_a] = 1.08
        prior_vocabulaire[pair_b] = 1.08

        if alternance_active:
            prior_vocabulaire[pair_a] = 1.12
            prior_vocabulaire[pair_b] = 1.12

        scores_contextuels = (
            smoothed_scores
            * prior_vocabulaire[None, :]
        )

        scores_contextuels = np.maximum(
            scores_contextuels,
            1e-12
        )

        scores_contextuels /= scores_contextuels.sum(
            axis=1,
            keepdims=True
        )

        accords_dominants = [
            dictionnaire_accords[pair_a],
            dictionnaire_accords[pair_b],
        ]

        vocabulaire = [
            dictionnaire_accords[int(i)]
            for i in top_vocabulaire
        ]

        # ----------------------------------------------------
        # DÉCODEUR DE RYTHME HARMONIQUE
        # ----------------------------------------------------
        # Au lieu de choisir un accord indépendamment sur chaque beat,
        # on cherche la meilleure segmentation du morceau en blocs de
        # 1, 2, 3 ou 4 beats.
        #
        # Préférences musicales :
        #   2 beats  -> très naturel : Am- / Em-
        #   4 beats  -> accord sur toute la mesure : Am---
        #   1 beat   -> autorisé mais coûteux
        #   3 beats  -> autorisé mais un peu coûteux
        #
        # Cela permet directement :
        #   Am Am Em Em  =>  Am-Em-
        # sans transformer chaque fluctuation de chroma en nouvel accord.

        if beat_grid_refinement.get("accepted", False):
            durees = (1, 2, 3, 4, 6, 8)
            bonus_duree = {
                1: -0.15,
                2:  0.28,
                3: -0.02,
                4:  0.24,
                6:  0.08,
                8:  0.12,
            }
            penalite_changement = 0.15
        else:
            durees = (1, 2, 3, 4)
            bonus_duree = {
                1: -1.25,
                2:  0.58,
                3: -0.45,
                4:  0.18,
            }
            penalite_changement = 0.38

        # Si un couple dominant alterné est détecté, son basculement
        # A <-> B reçoit un bonus spécifique.
        bonus_alternance_pair = (
            0.42
            if alternance_active
            else 0.0
        )
        nb_accords = len(dictionnaire_accords)

        beats = []
        cursor = 0

        while cursor < len(beat_infos):

            # Le silence coupe explicitement la continuité harmonique.
            if beat_infos[cursor]['silence']:
                info = beat_infos[cursor]
                beats.append({
                    **info,
                    'accord': '.',
                    'confiance': 1.0,
                    'ratio_top2': 999.0,
                    'marge_top2': 999.0,
                })
                cursor += 1
                continue

            span_start = cursor
            while (
                cursor < len(beat_infos)
                and not beat_infos[cursor]['silence']
            ):
                cursor += 1
            span_end = cursor

            emissions = scores_contextuels[span_start:span_end]
            n = len(emissions)

            # dp[t, c] = meilleur score pour couvrir les t premiers beats
            # et terminer sur l'accord c.
            neg_inf = -1e100
            dp = np.full((n + 1, nb_accords), neg_inf, dtype=np.float64)
            back = [[None for _ in range(nb_accords)] for _ in range(n + 1)]

            # État virtuel de départ : aucun accord précédent.
            for longueur in durees:
                if longueur > n:
                    continue

                segment = emissions[:longueur]
                log_segment = np.sum(np.log(segment + 1e-12), axis=0)
                score_segment = log_segment + bonus_duree[longueur]

                for accord_idx in range(nb_accords):
                    dp[longueur, accord_idx] = score_segment[accord_idx]
                    back[longueur][accord_idx] = (
                        0,
                        None,
                        longueur,
                        accord_idx,
                    )

            for t in range(1, n + 1):
                for accord_prec in range(nb_accords):
                    score_prec = dp[t, accord_prec]
                    if score_prec <= neg_inf / 2:
                        continue

                    for longueur in durees:
                        fin = t + longueur
                        if fin > n:
                            continue

                        segment = emissions[t:fin]
                        log_segment = np.sum(
                            np.log(segment + 1e-12),
                            axis=0
                        )

                        for accord_idx in range(nb_accords):
                            score = (
                                score_prec
                                + log_segment[accord_idx]
                                + bonus_duree[longueur]
                            )

                            if accord_idx != accord_prec:
                                # Un changement ordinaire coûte un peu.
                                score -= penalite_changement

                                # Mais le basculement entre les deux accords
                                # dominants appris est favorisé lorsque le
                                # morceau montre réellement cette alternance.
                                if (
                                    alternance_active
                                    and accord_prec in pair_set
                                    and accord_idx in pair_set
                                    and accord_idx != accord_prec
                                ):
                                    score += bonus_alternance_pair
                            else:
                                # Continuité autorisée mais pas survalorisée.
                                score += 0.06

                            if score > dp[fin, accord_idx]:
                                dp[fin, accord_idx] = score
                                back[fin][accord_idx] = (
                                    t,
                                    accord_prec,
                                    longueur,
                                    accord_idx,
                                )

            # Reconstruction des segments.
            dernier_accord = int(np.argmax(dp[n]))
            t = n
            segments = []

            while t > 0:
                etape = back[t][dernier_accord]
                if etape is None:
                    # Sécurité : fallback sur le meilleur accord du beat.
                    debut = t - 1
                    accord_idx = int(np.argmax(emissions[debut]))
                    segments.append((debut, t, accord_idx))
                    t = debut
                    dernier_accord = accord_idx
                    continue

                debut, accord_prec, longueur, accord_idx = etape
                segments.append((debut, t, accord_idx))
                t = debut

                if accord_prec is None:
                    break
                dernier_accord = accord_prec

            segments.reverse()

            accords_span = [None] * n
            for debut, fin, accord_idx in segments:
                for local_i in range(debut, fin):
                    accords_span[local_i] = accord_idx

            for local_i, accord_idx in enumerate(accords_span):
                global_i = span_start + local_i
                info = beat_infos[global_i]
                row = scores_contextuels[global_i]
                ordre = np.argsort(row)
                meilleur = float(row[ordre[-1]])
                second = float(row[ordre[-2]])

                beats.append({
                    **info,
                    'accord': dictionnaire_accords[int(accord_idx)],
                    'confiance': meilleur,
                    'ratio_top2': meilleur / (second + 1e-12),
                    'marge_top2': meilleur - second,
                })

        beats.sort(key=lambda b: b['index'])

        # ----------------------------------------------------
        # R12 — PREUVE LOCALE FORTE
        # ----------------------------------------------------
        # Le décodeur régional apporte de la stabilité, mais il ne doit pas
        # effacer un A/D/G/C court et spectralement net. Sur la grille ×2,
        # une évidence locale forte peut donc reprendre la main.
        local_evidence_overrides = 0

        if beat_grid_refinement.get("accepted", False):
            for i, beat in enumerate(beats):
                if beat.get("accord") == ".":
                    continue
                if i >= len(beat_score_matrix):
                    continue

                row_local = beat_score_matrix[i]
                ordre_local = np.argsort(row_local)
                best_idx = int(ordre_local[-1])
                second_idx = int(ordre_local[-2])
                best_score = float(row_local[best_idx])
                second_score = float(row_local[second_idx])
                ratio_local = best_score / (second_score + 1e-12)
                marge_local = best_score - second_score
                accord_local = dictionnaire_accords[best_idx]

                if (
                    accord_local != beat.get("accord")
                    and ratio_local >= 1.16
                    and marge_local >= 0.018
                ):
                    beat["accord"] = accord_local
                    beat["local_evidence_override"] = True
                    beat["local_ratio_top2"] = ratio_local
                    beat["local_marge_top2"] = marge_local
                    local_evidence_overrides += 1

        # ----------------------------------------------------
        # R13 — HYSTÉRÉSIS DE CHANGEMENT D'ACCORD
        # ----------------------------------------------------
        # R12 a rendu la grille assez fine pour retrouver des accords courts,
        # mais cela peut produire trop de micro-régions. R13 conserve l'accord
        # courant tant qu'un nouvel accord n'a pas accumulé assez de preuve.
        #
        # Deux voies permettent un changement :
        #   1. accord très fortement soutenu -> changement immédiat ;
        #   2. même candidat soutenu sur plusieurs beats -> changement validé.
        #
        # Lorsqu'un changement est validé après plusieurs beats, les beats
        # candidats sont rétroactivement affectés au nouvel accord afin de
        # conserver la vraie frontière temporelle.
        hysteresis_switches = 0
        hysteresis_rejected_candidates = 0
        strong_short_chords_kept = 0

        if len(beats) >= 2:
            current_chord = None
            pending_chord = None
            pending_start = None
            pending_count = 0
            pending_log_advantage = 0.0

            for i, beat in enumerate(beats):
                chord_now = str(beat.get("accord", "") or "")

                if chord_now == ".":
                    current_chord = None
                    pending_chord = None
                    pending_start = None
                    pending_count = 0
                    pending_log_advantage = 0.0
                    continue

                if current_chord is None:
                    current_chord = chord_now
                    continue

                if i >= len(beat_score_matrix):
                    continue

                row = beat_score_matrix[i]
                order = np.argsort(row)
                candidate_idx = int(order[-1])
                second_idx = int(order[-2])
                candidate = dictionnaire_accords[candidate_idx]

                try:
                    current_idx = dictionnaire_accords.index(current_chord)
                except ValueError:
                    current_idx = candidate_idx

                candidate_score = float(row[candidate_idx])
                current_score = float(row[current_idx])
                second_score = float(row[second_idx])

                local_ratio = candidate_score / (second_score + 1e-12)
                local_margin = candidate_score - second_score
                versus_current = candidate_score / (current_score + 1e-12)
                log_advantage = float(
                    np.log(candidate_score + 1e-12)
                    - np.log(current_score + 1e-12)
                )

                if candidate == current_chord:
                    if pending_chord is not None:
                        hysteresis_rejected_candidates += 1
                    pending_chord = None
                    pending_start = None
                    pending_count = 0
                    pending_log_advantage = 0.0
                    beat["accord"] = current_chord
                    continue

                # Accord bref mais spectralement très clair :
                # il peut être conservé immédiatement.
                strong_change = (
                    local_ratio >= 1.26
                    and local_margin >= 0.024
                    and versus_current >= 1.14
                )

                if strong_change:
                    current_chord = candidate
                    pending_chord = None
                    pending_start = None
                    pending_count = 0
                    pending_log_advantage = 0.0
                    beat["accord"] = candidate
                    beat["hysteresis_strong_change"] = True
                    strong_short_chords_kept += 1
                    hysteresis_switches += 1
                    continue

                if candidate != pending_chord:
                    if pending_chord is not None:
                        hysteresis_rejected_candidates += 1
                    pending_chord = candidate
                    pending_start = i
                    pending_count = 1
                    pending_log_advantage = max(0.0, log_advantage)
                else:
                    pending_count += 1
                    pending_log_advantage += max(0.0, log_advantage)

                if beat_grid_refinement.get("accepted", False):
                    enough_duration = pending_count >= 2
                    enough_evidence = (
                        pending_log_advantage >= 0.12
                        and versus_current >= 1.04
                    )
                else:
                    enough_duration = pending_count >= 2
                    enough_evidence = (
                        pending_log_advantage >= 0.18
                        and versus_current >= 1.06
                    )

                if enough_duration and enough_evidence:
                    for j in range(int(pending_start), i + 1):
                        if beats[j].get("accord") != ".":
                            beats[j]["accord"] = pending_chord
                            beats[j]["hysteresis_region_change"] = True

                    current_chord = pending_chord
                    hysteresis_switches += 1
                    pending_chord = None
                    pending_start = None
                    pending_count = 0
                    pending_log_advantage = 0.0
                else:
                    beat["accord"] = current_chord

            if pending_chord is not None:
                hysteresis_rejected_candidates += 1

        # ----------------------------------------------------
        # STABILISATION CONSERVATIVE DES MICRO-VARIATIONS
        # ----------------------------------------------------
        # Riffstation montre des régions harmoniques longues. EZScore garde
        # son analyse beat par beat, mais supprime uniquement un accord isolé
        # d'un beat lorsque :
        #   - les voisins portent exactement le même accord ;
        #   - aucun des trois beats n'est un silence ;
        #   - l'accord isolé est faiblement discriminé.
        #
        # Un changement fort ou tenu sur plusieurs beats reste intact.
        micro_variations_stabilisees = 0

        if len(beats) >= 3:
            accords_originaux = [
                str(b.get("accord", ""))
                for b in beats
            ]

            for i in range(1, len(beats) - 1):
                prev_accord = accords_originaux[i - 1]
                accord = accords_originaux[i]
                next_accord = accords_originaux[i + 1]

                if (
                    prev_accord in ("", ".")
                    or accord in ("", ".")
                    or next_accord in ("", ".")
                    or prev_accord != next_accord
                    or accord == prev_accord
                    or beats[i].get("hysteresis_strong_change", False)
                    or beats[i].get("hysteresis_region_change", False)
                ):
                    continue

                ratio = float(beats[i].get("ratio_top2", 999.0))
                marge = float(beats[i].get("marge_top2", 999.0))

                if beat_grid_refinement.get("accepted", False):
                    faible_preuve = (
                        ratio < 1.08
                        and marge < 0.020
                    )
                else:
                    faible_preuve = (
                        ratio < 1.18
                        or marge < 0.045
                    )

                if faible_preuve:
                    beats[i]["accord"] = prev_accord
                    beats[i]["stabilise_micro_variation"] = True
                    micro_variations_stabilisees += 1

        # Détection conservative du point d'orgue :
        # un intervalle anormalement long + harmonie présente + accord actif.
        fermata_beats = set()
        for i in range(len(beats) - 1):
            intervalle = beats[i]["intervalle"]

            harmonie_presente = (
                beats[i]["accord"] != "."
                and beats[i]["rms_ratio"] >= 0.65
                and beats[i]["chroma_ratio"] >= 0.65
            )

            ratio = intervalle / (median_interval + 1e-12)
            confidence = min(1.0, max(0.0, (ratio - 1.0) / max(fermata_gap_ratio - 1.0, 1e-12)))

            if (
                fermata_enabled
                and ratio >= fermata_gap_ratio
                and harmonie_presente
                and confidence >= FERMATA_MIN_CONFIDENCE
            ):
                fermata_beats.add(i)

        # Mesures
        mesures = []

        for start in range(0, len(beats), beats_par_mesure):
            groupe = beats[start:start + beats_par_mesure]
            if not groupe:
                continue

            symboles = [b["accord"] for b in groupe]

            # Dernière mesure incomplète : on garde des beats non joués '.'
            while len(symboles) < beats_par_mesure:
                symboles.append(".")

            indices_groupe = {b["index"] for b in groupe}
            fermata = bool(indices_groupe.intersection(fermata_beats))

            mesures.append({
                "numero": len(mesures) + 1,
                "debut": groupe[0]["temps"],
                "fin": groupe[-1]["fin"],
                "accords": symboles,
                "notation": formatter_mesure_signature(
                    symboles,
                    signature_effective,
                    fermata=fermata
                ),
                "fermata": fermata,
            })

        return {
            "sr": sr,
            "tempo": tempo,
            "tempo_brut": tempo_brut,
            "beat_grid_refinement": beat_grid_refinement,
            "beats": beats,
            "mesures": mesures,
            "median_interval": median_interval,
            "tonalite": tonalite,
            "tonalite_nom": nom_tonalite(tonalite),
            "accords_dominants": accords_dominants,
            "vocabulaire": vocabulaire,
            "alternance_active": alternance_active,
            "couverture_pair": couverture_pair,
            "taux_alternance_pair": taux_alternance_pair,
            "signature": signature_effective,
            "signature_mode": signature_mode,
            "signature_auto": signature_auto,
            "beats_par_mesure": beats_par_mesure,
            "analyse_sr": analyse_sr,
            "hop_length": hop_length,
            "silence_rms_ratio": silence_rms_ratio,
            "silence_chroma_ratio": silence_chroma_ratio,
            "poids_fondamentale": poids_fondamentale,
            "poids_accompagnement": 1.0 - poids_fondamentale,
            "micro_variations_stabilisees": micro_variations_stabilisees,
            "local_evidence_overrides": int(local_evidence_overrides),
            "hysteresis_switches": int(hysteresis_switches),
            "hysteresis_rejected_candidates": int(
                hysteresis_rejected_candidates
            ),
            "strong_short_chords_kept": int(strong_short_chords_kept),
            "harmonic_source_mix": {
                "no_vocals": 0.72,
                "original_mix": 0.28,
            },
            "harmonic_regions": int(
                sum(
                    1
                    for i, beat in enumerate(beats)
                    if (
                        beat.get("accord") != "."
                        and (
                            i == 0
                            or beats[i - 1].get("accord") != beat.get("accord")
                        )
                    )
                )
            ),
            "performance": {
                "demucs_seconds": float(_demucs_seconds),
                "rhythm_seconds": float(_rhythm_seconds),
                "harmony_seconds": float(
                    time.perf_counter() - _harmony_started
                ),
                "music_total_seconds": float(
                    time.perf_counter() - _music_started
                ),
            },
        }

    finally:
        if workdir:
            shutil.rmtree(
                workdir,
                ignore_errors=True
            )


# ============================================================
# TRANSCRIPTION
# ============================================================

@st.cache_data(show_spinner=False)
def transcrire_cache(audio_bytes, extension, device):
    chemin = creer_fichier_temporaire(audio_bytes, extension)

    try:
        modele = charger_modele_whisper(device)

        return modele.transcribe(
            chemin,
            word_timestamps=True,
            fp16=(device == "cuda"),
            verbose=False
        )
    finally:
        try:
            os.remove(chemin)
        except OSError:
            pass


# ============================================================
# ALIGNEMENT MESURES / PAROLES
# ============================================================

# ============================================================
# TIMELINE
# ============================================================

def creer_dataframe_timeline(beats):
    return pd.DataFrame([
        {
            "Accord": beat["accord"],
            "Début": beat["temps"],
            "Fin": beat["fin"],
        }
        for beat in beats
        if beat["accord"] != "."
    ])


# ============================================================
# INTERFACE
# ============================================================

# ============================================================
# NAVIGATION PRINCIPALE
# ============================================================

audio_bytes = None
audio_filename = None
audio_hash = None
song = None
fichier_audio = None

# Changement de menu demandé depuis un widget créé plus bas :
# on l'applique au début du rerun suivant, avant l'instanciation du menu.
_pending_main_menu = st.session_state.pop(
    "_pending_main_menu",
    None,
)

if _pending_main_menu in ("Répertoire", "Chanson", "Import"):
    st.session_state["main_menu"] = _pending_main_menu

if "main_menu" not in st.session_state:
    st.session_state["main_menu"] = "Répertoire"

main_menu = st.radio(
    "Navigation",
    ["Répertoire", "Chanson", "Import"],
    horizontal=True,
    key="main_menu",
    label_visibility="collapsed",
)

# ------------------------------------------------------------
# RÉPERTOIRE
# ------------------------------------------------------------
if main_menu == "Répertoire":
    st.subheader("🎵 Répertoire")

    if "active_song_hash" not in st.session_state:
        st.session_state["active_song_hash"] = get_app_state(
            "last_song_hash",
            "",
        )

    last_sort = get_app_state("catalog_sort", "title")

    sort_choice = st.radio(
        "Classer par",
        ["Titre", "Auteur / Interprète"],
        index=1 if last_sort == "artist" else 0,
        horizontal=True,
        key="catalog_sort_choice",
    )

    sort_key = (
        "artist"
        if sort_choice == "Auteur / Interprète"
        else "title"
    )
    set_app_state("catalog_sort", sort_key)

    catalog = list_song_catalog(sort_by=sort_key)

    st.caption(f"{len(catalog)} chanson(s) dans le répertoire")

    search_query = st.text_input(
        "Rechercher",
        value="",
        placeholder="Titre, auteur ou nom de fichier…",
        key="catalog_search",
    )

    letters = ["Tous", "#"] + [
        chr(c)
        for c in range(ord("A"), ord("Z") + 1)
    ]

    default_letter = get_app_state("catalog_letter", "Tous")
    if default_letter not in letters:
        default_letter = "Tous"

    selected_letter = st.radio(
        "Index",
        letters,
        index=letters.index(default_letter),
        horizontal=True,
        key="catalog_letter",
    )
    set_app_state("catalog_letter", selected_letter)

    filtered_catalog = filter_catalog(
        catalog,
        sort_by=sort_key,
        letter=selected_letter,
        query=search_query,
    )

    if not catalog:
        st.info(
            "Le répertoire est vide. Utilisez le menu Import "
            "pour ajouter votre première chanson."
        )
    elif not filtered_catalog:
        st.info("Aucune chanson ne correspond à ce filtre.")
    else:
        current_hash = st.session_state.get(
            "active_song_hash",
            get_app_state("last_song_hash", ""),
        )

        groups = {}

        for item in filtered_catalog:
            letter = catalog_letter_for_song(
                item,
                sort_by=sort_key,
            )
            groups.setdefault(letter, []).append(item)

        ordered_letters = ["#"] + [
            chr(c)
            for c in range(ord("A"), ord("Z") + 1)
        ]

        for letter in ordered_letters:
            items = groups.get(letter, [])
            if not items:
                continue

            st.markdown(
                f'<div class="catalog-letter-title">{letter}</div>',
                unsafe_allow_html=True,
            )

            for item in items:
                is_current = (
                    item["audio_hash"] == current_hash
                )

                versions = list_analysis_versions(
                    item["audio_hash"]
                )
                version_numbers = [
                    int(v["version_no"]) for v in versions
                ]

                cover_col, c1, c2, c3, c4, c5 = st.columns(
                    [0.55, 1.8, 1.25, 1.1, 0.9, 2.1]
                )

                with cover_col:
                    _catalog_cover = song_cover_path(item)

                    if _catalog_cover is not None:
                        st.image(str(_catalog_cover), width=64)
                    else:
                        st.caption("🎵")

                with c1:
                    primary = catalog_primary_text(
                        item,
                        sort_by=sort_key,
                    )
                    prefix = "▶ " if is_current else ""
                    st.markdown(f"**{prefix}{primary}**")
                    _catalog_workflow = get_song_workflow(
                        item["audio_hash"]
                    )
                    _catalog_editorial_history = (
                        list_song_editorial_versions(
                            item["audio_hash"]
                        )
                    )
                    _catalog_editorial = get_song_editorial_version(
                        item["audio_hash"],
                        _catalog_workflow.get("current_version_no"),
                    )
                    if _catalog_editorial is None:
                        _catalog_editorial = latest_song_editorial_version(
                            item["audio_hash"]
                        )

                    _status_badges = []

                    if version_numbers:
                        _status_badges.append(
                            '<span class="catalog-status-badge '
                            'catalog-status-analyzed">✓ Analysée</span>'
                        )
                    else:
                        _status_badges.append(
                            '<span class="catalog-status-badge '
                            'catalog-status-pending">○ À analyser</span>'
                        )

                    if version_numbers:
                        _catalog_state = str(
                            _catalog_workflow.get("state", "working")
                        )

                        if (
                            _catalog_state == "published"
                            and _catalog_editorial is not None
                        ):
                            _published_date = _editorial_date_fr(
                                _catalog_editorial.get("published_at")
                            )
                            _status_badges.append(
                                '<span class="catalog-status-badge '
                                'catalog-status-published">'
                                f'🌍 Version publiée · '
                                f'V{_catalog_editorial["version_label"]} · '
                                f'{_catalog_editorial["edition_label"]} · '
                                f'R{_catalog_editorial["release_no"]}'
                                + (
                                    f' · {_published_date}'
                                    if _published_date else ''
                                )
                                + '</span>'
                            )

                        elif (
                            _catalog_state == "validated"
                            and _catalog_editorial is not None
                        ):
                            _validated_date = _editorial_date_fr(
                                _catalog_editorial.get("validated_at")
                            )
                            _status_badges.append(
                                '<span class="catalog-status-badge '
                                'catalog-status-validated">'
                                f'✓ Version validée · '
                                f'V{_catalog_editorial["version_label"]}'
                                + (
                                    f' · {_validated_date}'
                                    if _validated_date else ''
                                )
                                + '</span>'
                            )

                        else:
                            _status_badges.append(
                                '<span class="catalog-status-badge '
                                'catalog-status-working">'
                                '● Modification en cours</span>'
                            )

                    st.markdown(
                        '<div class="catalog-status-line">'
                        + ''.join(_status_badges)
                        + '</div>',
                        unsafe_allow_html=True,
                    )

                    _catalog_state = str(
                        _catalog_workflow.get("state", "working")
                    )
                    if (
                        _catalog_state in ("validated", "published")
                        and _catalog_editorial is not None
                    ):
                        _catalog_note = str(
                            _catalog_editorial.get("note", "") or ""
                        ).strip()
                    else:
                        _catalog_note = str(
                            _catalog_workflow.get("working_note", "") or ""
                        ).strip()

                    _last_modified_candidates = [
                        str(item.get("updated_at", "") or ""),
                        str(_catalog_workflow.get("updated_at", "") or ""),
                    ]

                    if _catalog_editorial is not None:
                        _last_modified_candidates.append(
                            str(
                                _catalog_editorial.get(
                                    "updated_at",
                                    "",
                                ) or ""
                            )
                        )

                    _last_modified = max(
                        (
                            x
                            for x in _last_modified_candidates
                            if x
                        ),
                        default="",
                    )

                    st.caption(
                        "🕒 Dernière modification : "
                        + (
                            _editorial_date_fr(
                                _last_modified,
                                with_time=True,
                            )
                            or "—"
                        )
                    )

                    if _catalog_note:
                        st.caption(f"💬 {_catalog_note}")

                with c2:
                    st.caption(
                        catalog_secondary_text(
                            item,
                            sort_by=sort_key,
                        )
                    )

                _catalog_choices = []

                if version_numbers:
                    _latest_snapshot_no = int(version_numbers[0])
                    _catalog_state_for_choices = str(
                        _catalog_workflow.get(
                            "state",
                            "working",
                        )
                    )

                    if _catalog_state_for_choices != "published":
                        _catalog_choices.append({
                            "key": "working",
                            "kind": "working",
                            "snapshot_no": _latest_snapshot_no,
                            "label": (
                                f"V{_normalize_version_label(
                                    _catalog_workflow.get(
                                        'target_version_label',
                                        '1.0',
                                    )
                                )} · "
                                f"{_normalize_edition_label(
                                    _catalog_workflow.get(
                                        'target_edition_label',
                                        'Standard',
                                    )
                                )} · Travail"
                            ),
                        })

                    _known_snapshot_nos = set(version_numbers)

                    for _publication in _catalog_editorial_history:
                        if _publication.get("status") != "published":
                            continue

                        _source_snapshot = _publication.get(
                            "source_analysis_version_no"
                        )
                        if (
                            _source_snapshot is None
                            or int(_source_snapshot)
                            not in _known_snapshot_nos
                        ):
                            continue

                        _catalog_choices.append({
                            "key": (
                                f"published:"
                                f"{_publication['version_no']}"
                            ),
                            "kind": "published",
                            "snapshot_no": int(_source_snapshot),
                            "editorial": _publication,
                            "label": (
                                f"V{_publication['version_label']} · "
                                f"{_publication['edition_label']} · "
                                f"R{_publication['release_no']}"
                            ),
                        })

                    if (
                        not _catalog_choices
                        and _catalog_state_for_choices == "published"
                        and _catalog_editorial is not None
                    ):
                        _fallback_snapshot = (
                            _catalog_editorial.get(
                                "source_analysis_version_no"
                            )
                        )
                        if (
                            _fallback_snapshot is not None
                            and int(_fallback_snapshot)
                            in _known_snapshot_nos
                        ):
                            _catalog_choices.append({
                                "key": "published-current",
                                "kind": "published",
                                "snapshot_no": int(
                                    _fallback_snapshot
                                ),
                                "editorial": _catalog_editorial,
                                "label": (
                                    f"V{_catalog_editorial['version_label']} · "
                                    f"{_catalog_editorial['edition_label']} · "
                                    f"R{_catalog_editorial['release_no']}"
                                ),
                            })

                with c4:
                    if _catalog_choices:
                        _selected_catalog_key = st.selectbox(
                            "Version",
                            [
                                choice["key"]
                                for choice in _catalog_choices
                            ],
                            index=0,
                            format_func=lambda key: next(
                                choice["label"]
                                for choice in _catalog_choices
                                if choice["key"] == key
                            ),
                            key=(
                                f"catalog_editorial_"
                                f"{item['audio_hash']}"
                            ),
                            label_visibility="collapsed",
                        )

                        _selected_catalog_choice = next(
                            choice
                            for choice in _catalog_choices
                            if choice["key"]
                            == _selected_catalog_key
                        )
                        selected_version = int(
                            _selected_catalog_choice[
                                "snapshot_no"
                            ]
                        )
                    else:
                        _selected_catalog_choice = None
                        selected_version = None
                        st.caption("Sans version")

                with c3:
                    selected_version_data = next(
                        (
                            v for v in versions
                            if int(v["version_no"])
                            == int(selected_version)
                        ),
                        None,
                    ) if selected_version is not None else None

                    editor_display = (
                        str(
                            selected_version_data.get("editor", "")
                            or ""
                        ).strip()
                        if selected_version_data
                        else str(item.get("editor", "") or "").strip()
                    )

                    st.caption(
                        f"Éditeur : {editor_display or '—'}"
                    )

                with c5:
                    if selected_version is None:
                        open_col, delete_col = st.columns([1.5, 0.6])

                        with open_col:
                            if st.button(
                                "Ouvrir",
                                key=f"open_{sort_key}_{item['audio_hash']}",
                            ):
                                selected_audio_hash = item["audio_hash"]
                                st.session_state["active_song_hash"] = selected_audio_hash
                                st.session_state.pop("active_analysis_version_no", None)
                                set_app_state("last_song_hash", selected_audio_hash)
                                prepare_song_preferences_for_open(selected_audio_hash)
                                st.session_state["_pending_main_menu"] = "Chanson"
                                st.rerun()

                        with delete_col:
                            with st.popover("🗑"):
                                render_delete_song_controls(
                                    audio_hash=item["audio_hash"],
                                    display_name=catalog_display_name(
                                        item,
                                        sort_by="title",
                                    ),
                                    key_suffix=(
                                        f"{sort_key}_{item['audio_hash']}_noversion"
                                    ),
                                )
                    else:
                        a1, a2, a3 = st.columns([1, 1, 1])

                        with a1:
                            if st.button(
                                "👁 Voir",
                                key=f"view_v_{item['audio_hash']}_{selected_version}",
                            ):
                                selected_audio_hash = item["audio_hash"]
                                st.session_state["active_song_hash"] = selected_audio_hash
                                set_app_state("last_song_hash", selected_audio_hash)
                                prepare_song_preferences_for_open(selected_audio_hash)
                                prepare_analysis_version_for_open(
                                    selected_audio_hash,
                                    selected_version,
                                )
                                st.session_state[
                                    f"song_view_{selected_audio_hash[:12]}"
                                ] = "Paroles + accords"
                                st.session_state[
                                    f"song_mode_{selected_audio_hash[:12]}"
                                ] = "Vue"
                                st.session_state["_pending_main_menu"] = "Chanson"
                                st.rerun()

                        with a2:
                            if st.button(
                                "✏ Modifier",
                                key=f"edit_v_{item['audio_hash']}_{selected_version}",
                            ):
                                selected_audio_hash = item["audio_hash"]
                                if (
                                    _selected_catalog_choice is not None
                                    and _selected_catalog_choice.get(
                                        "kind"
                                    ) == "published"
                                ):
                                    resume_song_modifications(
                                        selected_audio_hash
                                    )
                                st.session_state["active_song_hash"] = selected_audio_hash
                                set_app_state("last_song_hash", selected_audio_hash)
                                prepare_song_preferences_for_open(selected_audio_hash)
                                prepare_analysis_version_for_open(
                                    selected_audio_hash,
                                    selected_version,
                                )
                                st.session_state[
                                    f"song_view_{selected_audio_hash[:12]}"
                                ] = "Grille"
                                st.session_state[
                                    f"song_mode_{selected_audio_hash[:12]}"
                                ] = "Édition"
                                st.session_state["_pending_main_menu"] = "Chanson"
                                st.rerun()

                        with a3:
                            with st.popover("🗑"):
                                render_delete_song_controls(
                                    audio_hash=item["audio_hash"],
                                    display_name=catalog_display_name(
                                        item,
                                        sort_by="title",
                                    ),
                                    key_suffix=(
                                        f"{sort_key}_{item['audio_hash']}_"
                                        f"{selected_version}"
                                    ),
                                )


# ------------------------------------------------------------
# IMPORT
# ------------------------------------------------------------
elif main_menu == "Import":
    st.subheader("📥 Import")

    fichier_audio = st.file_uploader(
        "Importer une nouvelle chanson",
        type=["mp3", "wav", "ogg", "m4a"],
        key="new_song_import",
    )

    if fichier_audio is not None:
        audio_bytes = fichier_audio.getvalue()
        audio_filename = fichier_audio.name
        audio_hash = audio_sha256(audio_bytes)

        persist_audio_source(
            audio_hash,
            audio_filename,
            audio_bytes,
        )

        song = ensure_song(
            audio_hash,
            audio_filename,
        )

        st.session_state["active_song_hash"] = audio_hash
        set_app_state("last_song_hash", audio_hash)
        prepare_song_preferences_for_open(audio_hash)

        # Import = ouverture automatique, sans analyse implicite.
        st.session_state["_pending_main_menu"] = "Chanson"
        st.rerun()

# ------------------------------------------------------------
# CHANSON
# ------------------------------------------------------------
elif main_menu == "Chanson":
    current_hash = st.session_state.get(
        "active_song_hash",
        get_app_state("last_song_hash", ""),
    )

    if not current_hash:
        st.info(
            "Aucune chanson ouverte. "
            "Choisissez un morceau dans le Répertoire."
        )
    else:
        catalog_for_open = list_song_catalog(
            sort_by="title"
        )

        current_song = next(
            (
                item
                for item in catalog_for_open
                if item["audio_hash"] == current_hash
            ),
            None,
        )

        if current_song is None:
            st.warning(
                "Le morceau actif n'existe plus dans le répertoire."
            )
        else:
            persisted_audio_path = find_persisted_audio(
                current_hash
            )

            if persisted_audio_path is None:
                audio_file_count = sum(
                    1
                    for p in AUDIO_DIR.iterdir()
                    if p.is_file()
                )

                st.warning(
                    "L'analyse du morceau est persistée, mais "
                    "aucun fichier audio correspondant à son "
                    "SHA-256 n'a été retrouvé dans "
                    f"{AUDIO_DIR}. "
                    f"{audio_file_count} fichier(s) audio présent(s)."
                )
            else:
                song = current_song
                audio_hash = current_hash
                audio_filename = current_song[
                    "original_filename"
                ]
                audio_bytes = (
                    persisted_audio_path.read_bytes()
                )

if (
    main_menu == "Chanson"
    and audio_bytes is not None
    and audio_hash is not None
    and song is not None
):
    extension = os.path.splitext(audio_filename)[1].lower() or ".mp3"

    # Pour un import neuf ou un ancien morceau réimporté, s'assurer que
    # l'enregistrement songs existe et que le nom de fichier est à jour.
    song = ensure_song(audio_hash, audio_filename)

    # --------------------------------------------------------
    # V39 — VUE DE PARTITION + MODE LOCAL
    # --------------------------------------------------------
    _view_key = f"song_view_{audio_hash[:12]}"
    _mode_key = f"song_mode_{audio_hash[:12]}"

    if _view_key not in st.session_state:
        st.session_state[_view_key] = "Paroles + accords"
    if _mode_key not in st.session_state:
        st.session_state[_mode_key] = "Vue"

    _pending_edit_hash = st.session_state.pop(
        "_pending_song_edit_hash",
        None,
    )
    if _pending_edit_hash == audio_hash:
        st.session_state[_mode_key] = "Édition"
        st.session_state[f"{_mode_key}_radio"] = "✏️ Éditer"

    nav_col, mode_col, print_col = st.columns([1.85, 1.05, 0.12])

    with nav_col:
        song_view = st.radio(
            "Vue",
            ["Grille", "Paroles + accords", "Blocs", "Analyse"],
            horizontal=True,
            key=_view_key,
            label_visibility="collapsed",
        )

    with mode_col:
        if song_view in ("Grille", "Paroles + accords"):
            _mode_options = ["👁 Vue", "✏️ Éditer", "▶ Jouer"]
        elif song_view == "Blocs":
            _mode_options = ["👁 Vue", "✏️ Éditer"]
        else:
            # Analyse est une vue de consultation uniquement.
            _mode_options = ["👁 Vue"]

        _current_mode = st.session_state.get(_mode_key, "Vue")
        if _current_mode == "Édition":
            _current_label = "✏️ Éditer"
        elif _current_mode == "Jouer":
            _current_label = "▶ Jouer"
        else:
            _current_label = "👁 Vue"

        if _current_label not in _mode_options:
            _current_label = "👁 Vue"

        song_mode_label = st.radio(
            "Mode",
            _mode_options,
            horizontal=True,
            key=f"{_mode_key}_radio",
            index=_mode_options.index(_current_label),
            label_visibility="collapsed",
        )

        song_mode = {
            "👁 Vue": "Vue",
            "✏️ Éditer": "Édition",
            "▶ Jouer": "Jouer",
        }[song_mode_label]

        st.session_state[_mode_key] = song_mode

        # Le passage en mode Édition ne modifie jamais implicitement
        # l'état éditorial. La reprise est une action explicite.

    with print_col:
        print_slot = st.empty()

    # --------------------------------------------------------
    # PRÉFÉRENCES DU MORCEAU — SANS RÉANALYSE
    # --------------------------------------------------------
    # Le capo est une préférence d'affichage : chaque changement est
    # persisté immédiatement. Les réglages avancés, eux, ne deviennent
    # la configuration persistante du morceau qu'après "Appliquer".
    _stored_preferences = load_song_preferences(audio_hash)
    _stored_settings = (
        dict(_stored_preferences.get("settings", {}) or {})
        if _stored_preferences
        else {}
    )

    # Pour un ancien morceau sans préférences, amorcer la configuration
    # depuis les widgets actuellement restaurés (eux-mêmes issus de la
    # dernière analyse persistée).
    if not _stored_settings:
        _stored_settings = current_song_settings_payload(DEVICE)

    _stored_capo = (
        int(_stored_preferences.get("capo", 0))
        if _stored_preferences
        else None
    )

    if _stored_capo != int(capo_user):
        save_song_preferences(
            audio_hash=audio_hash,
            capo=capo_user,
            settings=_stored_settings,
        )

    # --------------------------------------------------------
    # MÉTADONNÉES DU MORCEAU
    # --------------------------------------------------------
    metadata_key = audio_hash[:16]

    _sidebar_editor = str(song.get("editor", "") or "").strip()
    _validated_mods = validated_partition_modifications(audio_hash)
    _structure_dirty = _structure_draft_is_dirty(audio_hash)

    _validated_parts = []
    if _validated_mods["grid"]:
        _validated_parts.append(f'Grille : {_validated_mods["grid"]}')
    if _validated_mods["lyrics"]:
        _validated_parts.append(f'Paroles : {_validated_mods["lyrics"]}')
    if _validated_mods["blocks"]:
        _validated_parts.append(f'Blocs : {_validated_mods["blocks"]}')

    st.sidebar.markdown(
        SCORE.render(
            "templates/left-panel.score",
            {
                "panel": {
                    "editor_visible": bool(_sidebar_editor),
                    "editor": _sidebar_editor,
                    "structure_dirty": bool(_structure_dirty),
                    "has_validated": bool(_validated_mods["has_any"]),
                    "no_validated": not bool(_validated_mods["has_any"]),
                    "validated_summary": " · ".join(_validated_parts),
                }
            },
        ),
        unsafe_allow_html=True,
    )

    if song_mode == "Édition":
        st.subheader("📝 Morceau")

        with st.form(
            f"song_metadata_{metadata_key}",
            clear_on_submit=False,
        ):
            meta_col1, meta_col2, meta_col3 = st.columns([1.4, 1.4, 1])

            with meta_col1:
                title_user = st.text_input(
                    "Titre",
                    value=song.get("title", ""),
                    key=f"title_{metadata_key}",
                )

            with meta_col2:
                artist_user = st.text_input(
                    "Auteur / Interprète",
                    value=song.get("artist", ""),
                    key=f"artist_{metadata_key}",
                )

            with meta_col3:
                editor_user = st.text_input(
                    "Éditeur",
                    value=song.get("editor", ""),
                    key=f"editor_{metadata_key}",
                    help="Nom de l'auteur des modifications de cette partition.",
                )

            strum_col1, strum_col2 = st.columns(2)

            with strum_col1:
                strumming_primary_user = st.text_input(
                    "Strumming principal",
                    value=song.get("strumming_primary", ""),
                    key=f"strum_primary_{metadata_key}",
                    placeholder="ex. ↓ ↓↑ ↑↓↑",
                    help="Pattern principal de main droite / médiator.",
                )

            with strum_col2:
                strumming_secondary_user = st.text_input(
                    "Strumming alternatif",
                    value=song.get("strumming_secondary", ""),
                    key=f"strum_secondary_{metadata_key}",
                    placeholder="ex. refrain : ↓↑ ↓↑ ↓↑ ↓↑",
                    help="Pattern alternatif, par exemple pour un refrain.",
                )

            save_metadata = st.form_submit_button(
                "💾 Enregistrer",
                type="primary",
                help="Enregistre les métadonnées sans relancer l'analyse.",
            )

        if save_metadata:
            update_song_metadata(
                audio_hash,
                title_user,
                artist_user,
                editor_user,
                strumming_primary_user,
                strumming_secondary_user,
            )
            song["title"] = str(title_user or "").strip()
            song["artist"] = str(artist_user or "").strip()
            song["editor"] = str(editor_user or "").strip()
            song["strumming_primary"] = str(
                strumming_primary_user or ""
            ).strip()
            song["strumming_secondary"] = str(
                strumming_secondary_user or ""
            ).strip()

            # La version est créée juste après le chargement de l'analyse
            # courante, afin d'enregistrer un snapshot complet sans relancer
            # Demucs / Whisper.
            st.session_state[
                f"_snapshot_metadata_{audio_hash[:12]}"
            ] = True

        st.markdown("#### 🖼 Pochette")
        _cover_now = song_cover_path(song)

        if _cover_now is not None:
            st.image(str(_cover_now), width=180)

        _cover_upload = st.file_uploader(
            "Importer / remplacer la pochette",
            type=["jpg", "jpeg", "png", "webp"],
            key=f"cover_upload_{metadata_key}",
        )

        _cover_a, _cover_b = st.columns([1.3, 1.0])

        with _cover_a:
            if st.button(
                "💾 Enregistrer la pochette",
                disabled=_cover_upload is None,
                key=f"save_cover_{metadata_key}",
            ):
                saved_cover = save_song_cover(
                    audio_hash,
                    _cover_upload,
                )
                if saved_cover is not None:
                    song["cover_path"] = str(
                        saved_cover.relative_to(APP_DIR)
                    )
                st.rerun()

        with _cover_b:
            if _cover_now is not None and st.button(
                "🗑 Supprimer la pochette",
                key=f"delete_cover_{metadata_key}",
            ):
                delete_song_cover(audio_hash)
                song["cover_path"] = ""
                st.rerun()

    # En mode Vue, aucun entête anticipé ici :
    # l'entête unique est rendu après le chargement de l'analyse.

    try:
        analysis_parameters = make_analysis_parameters(
            signature_mode=signature_mode,
            analyse_sr=analyse_sr_user,
            hop_length=hop_length_user,
            silence_rms_ratio=silence_rms_user,
            silence_chroma_ratio=silence_chroma_user,
            poids_fondamentale=poids_fondamentale_user,
            fermata_enabled=fermata_enabled_user,
            fermata_gap_ratio=fermata_gap_user,
            whisper_device=DEVICE,
        )
        analysis_key = make_analysis_key(analysis_parameters)

        # ----------------------------------------------------
        # CONTRAT DE PERSISTANCE
        # ----------------------------------------------------
        # 1. Une ouverture depuis le Répertoire ne doit jamais provoquer
        #    implicitement une nouvelle analyse.
        # 2. Si les paramètres courants correspondent exactement à une
        #    analyse connue, on charge cette variante.
        # 3. Sinon, tant que l'utilisateur n'a pas explicitement cliqué
        #    "Appliquer les paramètres", on charge la dernière analyse
        #    persistée du morceau.
        # 4. Une nouvelle analyse n'est calculée que par action explicite :
        #       « Appliquer les paramètres ».
        #    Sur un morceau neuf : première analyse.
        #    Sur un morceau déjà analysé : nouvelle variante.

        selected_version_no = st.session_state.get(
            "active_analysis_version_no"
        )
        selected_version_data = (
            load_analysis_version(
                audio_hash,
                selected_version_no,
            )
            if selected_version_no is not None
            else None
        )

        persisted = load_persisted_analysis(
            audio_hash,
            analysis_key,
        )

        latest_persisted = load_latest_persisted_analysis(
            audio_hash
        )

        _has_existing_analysis = bool(
            selected_version_data is not None
            or persisted is not None
            or latest_persisted is not None
        )

        if appliquer_reglages:
            save_song_preferences(
                audio_hash=audio_hash,
                capo=capo_user,
                settings=current_song_settings_payload(DEVICE),
            )

        if not _has_existing_analysis and not appliquer_reglages:
            st.markdown("### ▶ Pré-écoute")
            st.audio(
                audio_bytes,
                format={
                    ".mp3": "audio/mpeg",
                    ".wav": "audio/wav",
                    ".ogg": "audio/ogg",
                    ".m4a": "audio/mp4",
                }.get(extension, None),
            )
            st.info(
                "Aucune analyse n'a encore été lancée. "
                "Écoutez le morceau si nécessaire, ajustez les réglages "
                "avancés dans la barre latérale, puis cliquez sur "
                "« Appliquer les paramètres » pour démarrer l'analyse."
            )
            st.stop()

        force_analysis = bool(appliquer_reglages)

        if selected_version_data is not None and not force_analysis:
            musique = selected_version_data["musique"]
            resultat = selected_version_data["resultat"]
            analysis_key = selected_version_data["analysis_key"]
            analysis_parameters = selected_version_data["parameters"]
            analyse_source = "persisted_version"

        elif persisted is not None and not force_analysis:
            musique = persisted["musique"]
            resultat = persisted["resultat"]
            analyse_source = "persisted_exact"

        elif latest_persisted is not None and not force_analysis:
            musique = latest_persisted["musique"]
            resultat = latest_persisted["resultat"]
            analyse_source = "persisted_latest"

            # La clé réellement utilisée reste celle de l'analyse chargée,
            # pas une clé dérivée d'éventuelles valeurs de widgets encore
            # différentes durant ce rerun.
            analysis_key = latest_persisted["analysis_key"]
            analysis_parameters = latest_persisted["parameters"]

        else:
            if force_analysis:
                # « Appliquer les paramètres » doit réellement recalculer
                # l'analyse musicale, même si la clé de paramètres existe déjà.
                # Whisper reste en cache : changer un seuil harmonique ne
                # nécessite pas de retranscrire l'audio.
                analyser_musique_cache.clear()

            spinner_message = (
                "Nouvelle analyse avec les paramètres validés..."
                if latest_persisted is not None
                else "Analyse demandée : accords, beats, mesures et paroles..."
            )

            _analysis_total_started = time.perf_counter()

            with analysis_progress_slot:
                with st.status(
                    spinner_message,
                    expanded=True,
                ) as analysis_status:
                    progress = st.progress(
                        5,
                        text="Analyse en cours — préparation…",
                    )
    
                    # CPU et GPU peuvent travailler simultanément.
                    with ThreadPoolExecutor(max_workers=2) as executor:
                        _music_task_started = time.perf_counter()
                        future_musique = executor.submit(
                            analyser_musique_cache,
                            audio_bytes,
                            extension,
                            signature_mode,
                            analyse_sr_user,
                            hop_length_user,
                            silence_rms_user,
                            silence_chroma_user,
                            poids_fondamentale_user,
                            fermata_enabled_user,
                            fermata_gap_user,
                        )
    
                        _whisper_task_started = time.perf_counter()
                        future_whisper = executor.submit(
                            transcrire_cache,
                            audio_bytes,
                            extension,
                            DEVICE
                        )
    
                        progress.progress(
                            10,
                            text="Demucs + rythme + harmonie · Whisper/cache en parallèle…",
                        )
    
                        _music_done = False
                        _whisper_done = False
                        _music_seconds = None
                        _whisper_seconds = None
    
                        while not (_music_done and _whisper_done):
                            changed = False
    
                            if future_musique.done() and not _music_done:
                                musique = future_musique.result()
                                _music_seconds = (
                                    time.perf_counter()
                                    - _music_task_started
                                )
                                _music_done = True
                                changed = True
    
                            if future_whisper.done() and not _whisper_done:
                                resultat = future_whisper.result()
                                _whisper_seconds = (
                                    time.perf_counter()
                                    - _whisper_task_started
                                )
                                _whisper_done = True
                                changed = True
    
                            _pct = 10
                            if _music_done:
                                _pct += 45
                            if _whisper_done:
                                _pct += 30
    
                            if changed:
                                _done_labels = []
                                if _music_done:
                                    _done_labels.append("analyse musicale ✓")
                                if _whisper_done:
                                    _done_labels.append("paroles Whisper ✓")
    
                                progress.progress(
                                    min(_pct, 85),
                                    text=" · ".join(_done_labels),
                                )
    
                            if not (_music_done and _whisper_done):
                                time.sleep(0.12)
    
                    progress.progress(
                        88,
                        text="Finalisation et sauvegarde…",
                    )
    
                    _parallel_seconds = (
                        time.perf_counter()
                        - _analysis_total_started
                    )
    
                    perf = dict(
                        musique.get("performance", {}) or {}
                    )
                    perf.update({
                        "music_future_seconds": float(
                            _music_seconds or 0.0
                        ),
                        "whisper_seconds": float(
                            _whisper_seconds or 0.0
                        ),
                        "parallel_seconds": float(
                            _parallel_seconds
                        ),
                    })
                    musique["performance"] = perf

            save_persisted_analysis(
                audio_hash=audio_hash,
                analysis_key=analysis_key,
                parameters=analysis_parameters,
                musique=musique,
                resultat=resultat,
            )

            saved_version_no = save_analysis_version(
                audio_hash=audio_hash,
                analysis_key=analysis_key,
                parameters=analysis_parameters,
                musique=musique,
                resultat=resultat,
            )

            analyse_source = "computed"

            if "progress" in locals():
                _total_seconds = (
                    time.perf_counter()
                    - _analysis_total_started
                )
                musique.setdefault(
                    "performance",
                    {},
                )["total_seconds"] = float(
                    _total_seconds
                )
                progress.progress(
                    100,
                    text=f"Analyse terminée en {_total_seconds:.1f} s",
                )
                analysis_status.update(
                    label=f"Analyse terminée en {_total_seconds:.1f} s",
                    state="complete",
                    expanded=False,
                )

            # Première analyse ou nouvelle variante explicitement validée :
            # les réglages visibles deviennent la configuration du morceau.
            save_song_preferences(
                audio_hash=audio_hash,
                capo=capo_user,
                settings=current_song_settings_payload(DEVICE),
            )

        _snapshot_metadata_key = (
            f"_snapshot_metadata_{audio_hash[:12]}"
        )
        if st.session_state.pop(
            _snapshot_metadata_key,
            False,
        ):
            version_no = save_analysis_version(
                audio_hash=audio_hash,
                analysis_key=analysis_key,
                parameters=analysis_parameters,
                musique=musique,
                resultat=resultat,
            )
            st.success(
                f"Métadonnées enregistrées — snapshot technique S{version_no}. "
                "Aucune analyse n'a été relancée."
            )
            st.session_state["active_analysis_version_no"] = version_no

        tempo = musique["tempo"]

        beats_detectes = musique["beats"]
        mesures_detectees = musique["mesures"]

        beat_edits = load_beat_edits(audio_hash)
        beats = appliquer_editions_beats(
            beats_detectes,
            beat_edits,
        )

        # Les corrections de grille par mesure sont désormais la couche
        # musicale principale. Elles écrasent les anciens overrides beat
        # uniquement pour les mesures explicitement éditées.
        beats = appliquer_editions_mesures_aux_beats(
            audio_hash=audio_hash,
            beats=beats,
            beats_par_mesure=musique.get(
                "beats_par_mesure",
                4,
            ),
            signature=musique.get(
                "signature",
                "4/4",
            ),
        )

        tonalite = musique.get("tonalite", {})
        tonalite_nom = musique.get("tonalite_nom", "?")
        accords_dominants = musique.get("accords_dominants", [])
        vocabulaire = musique.get("vocabulaire", [])
        alternance_active = musique.get("alternance_active", False)
        couverture_pair = musique.get("couverture_pair", 0.0)
        taux_alternance_pair = musique.get("taux_alternance_pair", 0.0)
        signature = musique.get("signature", "4/4")
        signature_mode_effective = musique.get("signature_mode", "Auto")
        signature_auto = musique.get("signature_auto", {})
        beats_par_mesure_effectif = musique.get("beats_par_mesure", 4)
        poids_fondamentale_effectif = musique.get("poids_fondamentale", 0.22)
        poids_accompagnement_effectif = musique.get("poids_accompagnement", 0.78)

        mesures = reconstruire_mesures_depuis_beats(
            beats=beats,
            original_mesures=mesures_detectees,
            signature=signature,
            beats_par_mesure=beats_par_mesure_effectif,
        )

        # Le capo ne touche jamais l'analyse audio.
        # On crée seulement une vue transformée pour le guitariste.
        mesures_affichees = preparer_mesures_affichage(
            mesures,
            signature,
            capo_user
        )

        if song_mode == "Édition":
            if analyse_source in (
                "persisted_version",
                "persisted_exact",
                "persisted_latest",
            ):
                st.success(
                    "Analyse persistante chargée — Demucs et Whisper "
                    "n'ont pas été relancés."
                )

                if analyse_source == "persisted_latest":
                    st.caption(
                        "Ouverture protégée : dernière analyse enregistrée "
                        "chargée sans recalcul."
                    )
            else:
                st.success(
                    f"Analyse terminée et sauvegardée comme snapshot "
                    f"S{saved_version_no}."
                )

        # ----------------------------------------------------
        # INFOS
        # ----------------------------------------------------

        titre_affiche = song.get("title", "") or Path(audio_filename).stem
        artiste_affiche = str(song.get("artist", "") or "").strip()

        _version_no = st.session_state.get(
            "active_analysis_version_no"
        )

        _measure_edits_for_status = load_measure_edits(audio_hash)
        _lyric_edits_for_status = load_lyric_block_edits(audio_hash)
        _editor_for_status = str(song.get("editor", "") or "").strip()
        _strum_for_status = bool(
            str(song.get("strumming_primary", "") or "").strip()
            or str(song.get("strumming_secondary", "") or "").strip()
        )

        _has_manual_corrections = bool(
            _measure_edits_for_status
            or _lyric_edits_for_status
            or _editor_for_status
            or _strum_for_status
        )

        if _version_no is not None and _has_manual_corrections:
            _source_status = "Version éditée"
        elif _has_manual_corrections:
            _source_status = "Analyse auto + corrections"
        else:
            _source_status = "Analyse auto"

        _title_left = (
            f"{titre_affiche} — {artiste_affiche}"
            if artiste_affiche
            else str(titre_affiche)
        )

        _editorial_workflow = get_song_workflow(audio_hash)
        _editorial_version = get_song_editorial_version(
            audio_hash,
            _editorial_workflow.get("current_version_no"),
        )
        if _editorial_version is None:
            _editorial_version = latest_song_editorial_version(audio_hash)

        _version_label = editorial_status_label(
            _editorial_workflow,
            _editorial_version,
        )

        st.markdown(
            """
            <style>
            .song-compact-header {
                display:flex;
                align-items:baseline;
                justify-content:space-between;
                gap:1rem;
                margin:0.15rem 0 0.65rem 0;
                flex-wrap:wrap;
            }
            .song-compact-title {
                font-size:2rem;
                font-weight:780;
                line-height:1.05;
            }
            .song-compact-meta {
                font-size:0.90rem;
                opacity:0.68;
                white-space:nowrap;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            SCORE.render(
                "templates/header.score",
                {
                    "song": {
                        "title": _title_left,
                        "version_label": _version_label,
                        "source_status": _source_status,
                    }
                },
            ),
            unsafe_allow_html=True,
        )

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Tempo", f"{tempo:.1f} BPM")
        c2.metric("Signature", signature)
        c3.metric("Tonalité réelle", tonalite_nom)
        c4.metric(
            "Capo",
            "—" if int(capo_user) == 0 else str(int(capo_user)),
        )
        c5.metric("Mesures", len(mesures))

        _strum_primary_header = str(
            song.get("strumming_primary", "") or ""
        ).strip()
        _strum_secondary_header = str(
            song.get("strumming_secondary", "") or ""
        ).strip()

        if _strum_primary_header or _strum_secondary_header:
            _header_parts = []
            if _strum_primary_header:
                _header_parts.append(
                    f"**Strumming** : {_strum_primary_header}"
                )
            if _strum_secondary_header:
                _header_parts.append(
                    f"**Alternatif** : {_strum_secondary_header}"
                )
            st.info("🎸 " + "  ·  ".join(_header_parts))

        _workflow = get_song_workflow(audio_hash)
        _workflow_version = get_song_editorial_version(
            audio_hash,
            _workflow.get("current_version_no"),
        )

        if _workflow_version is None:
            _workflow_version = latest_song_editorial_version(
                audio_hash
            )

        _editorial_history = list_song_editorial_versions(
            audio_hash
        )
        _latest_published = next(
            (
                v
                for v in _editorial_history
                if v.get("status") == "published"
            ),
            None,
        )

        _state = str(_workflow.get("state", "working"))

        _note_initial = (
            _workflow_version.get("note", "")
            if (
                _state == "published"
                and _workflow_version is not None
            )
            else _workflow.get("working_note", "")
        )

        _target_version_label = _normalize_version_label(
            _workflow.get("target_version_label", "1.0")
        )
        _target_edition_label = _normalize_edition_label(
            _workflow.get(
                "target_edition_label",
                "Standard",
            )
        )

        with st.container(border=True):
            st.markdown("### 📝 Publication de la chanson")

            if (
                _state == "published"
                and _workflow_version is not None
            ):
                _state_label = "🌍 Publiée"
                _version_display = (
                    f"V{_workflow_version['version_label']}"
                )
                _edition_display = (
                    _workflow_version["edition_label"]
                )
                _release_display = (
                    f"R{_workflow_version['release_no']}"
                )
                _date_display = _editorial_date_fr(
                    _workflow_version.get("published_at"),
                    with_time=True,
                )
            else:
                _state_label = "● Modification en cours"
                _version_display = f"V{_target_version_label}"
                _edition_display = _target_edition_label
                _release_display = "—"
                _date_display = _editorial_date_fr(
                    _workflow.get("updated_at"),
                    with_time=True,
                )

            _wf_cols = st.columns(5)
            _wf_cols[0].metric("État", _state_label)
            _wf_cols[1].metric("Version", _version_display)
            _wf_cols[2].metric("Édition", _edition_display)
            _wf_cols[3].metric("Release", _release_display)
            _wf_cols[4].metric(
                (
                    "Publication"
                    if _state == "published"
                    else "Dernière modif"
                ),
                _date_display or "—",
            )

            if (
                _state != "published"
                and _latest_published is not None
            ):
                st.caption(
                    "Dernière publication : "
                    f"V{_latest_published['version_label']} · "
                    f"{_latest_published['edition_label']} · "
                    f"R{_latest_published['release_no']} · "
                    f"{_editorial_date_fr(
                        _latest_published.get('published_at'),
                        with_time=True,
                    )}"
                )

            if (
                song_mode == "Édition"
                and _state != "published"
            ):
                vcol, ecol = st.columns([1.0, 1.25])

                with vcol:
                    _target_version_label = st.text_input(
                        "Version cible",
                        value=_target_version_label,
                        key=(
                            f"target_version_"
                            f"{audio_hash[:12]}"
                        ),
                        help=(
                            "Libre : 1.8, 1.9, "
                            "2.0, 1.8.1…"
                        ),
                    )

                with ecol:
                    _edition_options = [
                        "Simplifiée",
                        "Standard",
                        "Avancée",
                        "Personnalisée",
                    ]

                    _edition_index = (
                        _edition_options.index(
                            _target_edition_label
                        )
                        if _target_edition_label
                        in _edition_options
                        else _edition_options.index(
                            "Personnalisée"
                        )
                    )

                    _edition_choice = st.selectbox(
                        "Édition",
                        _edition_options,
                        index=_edition_index,
                        key=(
                            f"target_edition_"
                            f"{audio_hash[:12]}"
                        ),
                    )

                    if (
                        _edition_choice
                        == "Personnalisée"
                    ):
                        _target_edition_label = st.text_input(
                            "Nom de l’édition",
                            value=(
                                _target_edition_label
                                if _target_edition_label
                                not in _edition_options
                                else ""
                            ),
                            key=(
                                f"custom_edition_"
                                f"{audio_hash[:12]}"
                            ),
                            placeholder=(
                                "Ex. Fingerstyle"
                            ),
                        )
                    else:
                        _target_edition_label = (
                            _edition_choice
                        )

                _editor_note = st.text_area(
                    "Note de l’éditeur",
                    value=str(_note_initial or ""),
                    placeholder=(
                        "Ex. Couplet 2 non terminé…"
                    ),
                    key=(
                        f"editor_note_"
                        f"{audio_hash[:12]}_working"
                    ),
                )

                c_save, c_publish = st.columns(
                    [1.2, 1.5]
                )

                with c_save:
                    if st.button(
                        "💾 Enregistrer les modifications",
                        type="primary",
                        key=(
                            f"save_work_"
                            f"{audio_hash[:12]}"
                        ),
                    ):
                        _technical_snapshot_no = (
                            save_analysis_version(
                                audio_hash=audio_hash,
                                analysis_key=analysis_key,
                                parameters=(
                                    analysis_parameters
                                ),
                                musique=musique,
                                resultat=resultat,
                            )
                        )

                        saved_v, saved_e = (
                            save_song_working_state(
                                audio_hash,
                                _editor_note,
                                _target_version_label,
                                _target_edition_label,
                            )
                        )

                        st.session_state[
                            "active_analysis_version_no"
                        ] = _technical_snapshot_no

                        st.success(
                            "Modifications enregistrées "
                            f"pour V{saved_v} · {saved_e}. "
                            "La version éditoriale "
                            "n’a pas été incrémentée."
                        )
                        st.rerun()

                with c_publish:
                    if st.button(
                        (
                            "🌍 Publier "
                            f"V{_normalize_version_label(
                                _target_version_label
                            )} · "
                            f"{_normalize_edition_label(
                                _target_edition_label
                            )}"
                        ),
                        key=(
                            f"publish_song_version_"
                            f"{audio_hash[:12]}"
                        ),
                    ):
                        _technical_snapshot_no = (
                            save_analysis_version(
                                audio_hash=audio_hash,
                                analysis_key=analysis_key,
                                parameters=(
                                    analysis_parameters
                                ),
                                musique=musique,
                                resultat=resultat,
                            )
                        )

                        published = (
                            publish_song_editorial_version(
                                audio_hash,
                                _technical_snapshot_no,
                                _editor_note,
                                _target_version_label,
                                _target_edition_label,
                            )
                        )

                        st.session_state[
                            "active_analysis_version_no"
                        ] = _technical_snapshot_no

                        st.success(
                            f"V{published['version_label']} · "
                            f"{published['edition_label']} · "
                            f"R{published['release_no']} "
                            "publiée."
                        )
                        st.rerun()

            else:
                _editor_note = str(
                    _note_initial or ""
                ).strip()

                st.markdown("**Commentaire**")

                if _editor_note:
                    st.info(_editor_note)
                else:
                    st.caption(
                        "— Aucun commentaire —"
                    )

                if (
                    _state == "published"
                    and _workflow_version is not None
                ):
                    a1, a2 = st.columns(2)

                    with a1:
                        if st.button(
                            (
                                "✏ Nouvelle édition "
                                "de cette version"
                            ),
                            key=(
                                f"resume_same_version_"
                                f"{audio_hash[:12]}"
                            ),
                        ):
                            next_v, next_e = (
                                resume_song_modifications(
                                    audio_hash,
                                    keep_version=True,
                                    edition_label="Standard",
                                )
                            )
                            st.session_state[
                                "_pending_song_edit_hash"
                            ] = audio_hash
                            st.success(
                                "Copie de travail ouverte : "
                                f"V{next_v} · {next_e}."
                            )
                            st.rerun()

                    with a2:
                        if st.button(
                            (
                                "✏ Préparer une "
                                "nouvelle version"
                            ),
                            key=(
                                f"resume_next_version_"
                                f"{audio_hash[:12]}"
                            ),
                        ):
                            next_v, next_e = (
                                resume_song_modifications(
                                    audio_hash,
                                    keep_version=False,
                                    edition_label=(
                                        _workflow_version[
                                            "edition_label"
                                        ]
                                    ),
                                )
                            )
                            st.session_state[
                                "_pending_song_edit_hash"
                            ] = audio_hash
                            st.success(
                                "Copie de travail ouverte : "
                                f"V{next_v} · {next_e}."
                            )
                            st.rerun()

            _published_history = [
                _entry
                for _entry in _editorial_history
                if _entry.get("status") == "published"
            ]

            if _published_history:
                with st.expander(
                    "Historique des publications",
                    expanded=False,
                ):
                    for _entry in _published_history:
                        _entry_date = (
                            _entry.get("published_at")
                            or _entry.get("validated_at")
                        )

                        _label = (
                            f"V{_entry['version_label']} · "
                            f"{_entry['edition_label']} · "
                            f"R{_entry['release_no']} · "
                            f"{_editorial_date_fr(
                                _entry_date,
                                with_time=True,
                            )}"
                        )

                        if _entry.get("note"):
                            st.write(
                                f"**{_label}** — "
                                f"{_entry['note']}"
                            )
                        else:
                            st.write(
                                f"**{_label}**"
                            )

        versions = list_analysis_versions(audio_hash)

        if song_mode == "Édition":
            with st.expander("🗂️ Snapshots techniques", expanded=False):
                st.caption(
                    "Gestion / restauration des snapshots internes. "
                    "Ce panneau est volontairement masqué en mode Vue."
                )

                if not versions:
                    st.caption(
                        "Aucun snapshot explicite enregistré pour ce morceau."
                    )
                else:
                    rows_versions = []
                    for version in versions:
                        p = version["parameters"]
                        rows_versions.append({
                            "Snapshot": version["version_no"],
                            "Éditeur": version.get("editor", "") or "—",
                            "Signature": p.get("signature_mode", "?"),
                            "Fréquence": p.get("analyse_sr", "?"),
                            "Hop": p.get("hop_length", "?"),
                            "Créée": version.get("created_at", ""),
                        })
                    st.dataframe(
                        pd.DataFrame(rows_versions),
                        width="stretch",
                        hide_index=True,
                    )

                if st.button(
                    "💾 Sauver l'analyse courante comme snapshot",
                    key=f"save_analysis_version_{audio_hash[:12]}",
                ):
                    version_no = save_analysis_version(
                        audio_hash=audio_hash,
                        analysis_key=analysis_key,
                        parameters=analysis_parameters,
                        musique=musique,
                        resultat=resultat,
                    )
                    st.success(f"Snapshot S{version_no} enregistré.")
                    st.rerun()

        # ----------------------------------------------------
        # MODE JOUER
        # ----------------------------------------------------
        if song_mode == "Jouer":
            if song_view == "Grille":
                st.markdown(
                    "### 🎧 Comparaison harmonique — MP3 + MIDI"
                )
                st.caption(
                    "Le MP3 pilote une vraie sortie MIDI. "
                    "Un accord est rejoué à chaque temps, avec accentuation "
                    "des temps forts. Aucun oscillateur Web Audio."
                )

                _midi_instrument_label = st.selectbox(
                    "Instrument MIDI",
                    list(MIDI_INSTRUMENTS.keys()),
                    index=0,
                    key=f"midi_instrument_{audio_hash[:12]}",
                )
                _midi_program = MIDI_INSTRUMENTS[
                    _midi_instrument_label
                ]
                _midi_strum_ms = (
                    12.0
                    if _midi_program == 27
                    else 0.0
                )

                _play_midi_events = (
                    build_chord_midi_events(
                        beats=beats,
                        signature=signature,
                        beats_per_measure=(
                            beats_par_mesure_effectif
                        ),
                        program=_midi_program,
                        gate_ratio=0.48,
                        strum_ms=_midi_strum_ms,
                    )
                )

                _play_midi_bytes = build_midi_file(
                    beats=beats,
                    tempo=tempo,
                    signature=signature,
                    beats_per_measure=(
                        beats_par_mesure_effectif
                    ),
                    program=_midi_program,
                    gate_ratio=0.48,
                    strum_ms=_midi_strum_ms,
                )

                _play_midi_filename = (
                    re.sub(
                        r"[^A-Za-z0-9._-]+",
                        "_",
                        str(titre_affiche or "EZScore"),
                    ).strip("_")
                    or "EZScore"
                ) + "_accords.mid"

                st.download_button(
                    "⬇ Télécharger le MIDI des accords",
                    data=_play_midi_bytes,
                    file_name=_play_midi_filename,
                    mime="audio/midi",
                    key=f"play_midi_{audio_hash[:12]}",
                )

                render_editor_midi_player(
                    audio_bytes=audio_bytes,
                    extension=extension,
                    midi_events=_play_midi_events,
                    instrument_label=_midi_instrument_label,
                    program=_midi_program,
                )

            elif song_view == "Paroles + accords":
                st.info(
                    "▶ Player Paroles + accords synchronisé : "
                    "fonction séparée, non remplacée par le player MIDI."
                )

        # Structure calculée sur les accords RÉELS, avant toute représentation capo.
        # ----------------------------------------------------
        # GRILLE — LOOK TYPE EXCEL
        # ----------------------------------------------------

        if song_view == "Grille":
            st.caption(
                "1 case = 1 mesure. Cellules compactes à largeur fixe, "
                "quadrillage par bloc, sans numérotation visible."
            )
            st.caption(
                "`-` = accord tenu · `.` = beat non joué · `^` = point d'orgue détecté "
                "· doublons consécutifs compressés"
            )

        st.markdown(
            """
            <style>
            .chord-grid-wrap {
                width: 100%;
                overflow-x: auto;
                margin-top: 0.35rem;
                margin-bottom: 1.2rem;
            }

            .chord-block-row {
                margin: 0.15rem 0 1.05rem 0;
            }

            .chord-block-name {
                font-size: 1.38rem;
                font-weight: 780;
                color: #0b5fa5;
                padding-top: 0.18rem;
                line-height: 1.0;
            }

            .chord-grid-wrap {
                width: auto;
                max-width: 100%;
                overflow-x: auto;
                margin: 0;
                padding: 0;
            }

            table.chord-grid {
                width: auto;
                border-collapse: collapse;
                table-layout: fixed;
                font-family: Consolas, "Courier New", ui-monospace, monospace;
                background: transparent;
                border: 1.5px solid rgba(35, 35, 35, 0.82);
            }

            table.chord-grid td {
                border: 1px solid rgba(35, 35, 35, 0.72);
                text-align: left;
                vertical-align: middle;
                padding: 0.20rem 0.42rem;
                width: 150px;
                min-width: 150px;
                max-width: 150px;
                height: 1.72rem;
                font-size: 1.90rem;
                font-weight: 780;
                line-height: 0.98;
                letter-spacing: 0;
                white-space: nowrap;
                background: rgba(255,255,255,0.015);
            }

            table.chord-grid td:hover {
                background: rgba(120, 140, 165, 0.07);
            }

            .chord-grid-symbol {
                display: block;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        # La structure doit être calculée AVANT le rendu de la grille,
        # car la grille est elle-même affichée par blocs structurels.
        # Le calcul reste basé sur les accords réels, jamais sur le capo.
        sections_structurelles = []
        sections_detectees = []

        if sections_enabled_user:
            sections_detectees = detecter_sections_structurelles(
                mesures=mesures,
                resultat=resultat,
                block_measures=section_block_measures_user,
                similarity_threshold=section_similarity_user,
            )

            blocs_persistants = ensure_structure_blocks(
                audio_hash=audio_hash,
                detected_sections=sections_detectees,
                total_measures=len(mesures),
            )

            sections_structurelles = materialiser_structure_blocks(
                blocks=blocs_persistants,
                mesures=mesures,
                detected_sections=sections_detectees,
            )

        if (
            song_view == "Blocs"
            and song_mode == "Édition"
            and sections_enabled_user
            and sections_structurelles
        ):
            st.markdown(
                SCORE.render(
                    "templates/views/blocks.score",
                    {
                        "view": {
                            "title": "Structure du morceau",
                            "caption_visible": True,
                            "caption": (
                                "À gauche, modifiez le découpage. À droite, "
                                "contrôlez immédiatement les paroles et accords "
                                "correspondant aux bornes du brouillon."
                            ),
                        }
                    },
                ),
                unsafe_allow_html=True,
            )

            edit_col, preview_col = st.columns(
                [2, 3],
                gap="large",
            )

            with edit_col:
                with st.expander("✏️ Découpage du morceau", expanded=True):
                    st.caption(
                        "Édition séquentielle : modifiez Nom ou Fin puis faites Entrée "
                        "ou cliquez dans une autre cellule. Début et Nb mesures sont "
                        "recalculés immédiatement. Pour supprimer, cochez plusieurs lignes "
                        "si besoin puis cliquez « Supprimer ». Rien n'est persisté avant validation."
                    )

                    total_measures = len(mesures)
                    persisted_blocks = load_structure_blocks(audio_hash)

                    # Réinitialiser un vieux brouillon devenu incompatible avec le morceau.
                    draft_blocks = _get_structure_draft(audio_hash)
                    if not draft_blocks:
                        draft_blocks = _structure_draft_from_persisted(audio_hash)

                    draft_blocks = _normalize_structure_draft(
                        draft_blocks,
                        total_measures,
                    )
                    st.session_state[
                        _structure_draft_key(audio_hash)
                    ] = [dict(b) for b in draft_blocks]

                    action_msg = st.session_state.pop(
                        _structure_action_message_key(audio_hash),
                        None,
                    )
                    if action_msg:
                        st.info(action_msg)

                    rows = []
                    for block in draft_blocks:
                        start_value = int(block["measure_start"])
                        end_value = int(block["measure_end"])
                        rows.append({
                            "Nom": (
                                str(block.get("custom_label", "") or "").strip()
                                or "Nouveau bloc"
                            ),
                            "Début": start_value,
                            "Fin": end_value,
                            "Nb mesures": end_value - start_value + 1,
                            "Supprimer": False,
                        })

                    revision = int(
                        st.session_state.get(
                            _structure_editor_revision_key(audio_hash),
                            0,
                        )
                    )

                    edited_df = st.data_editor(
                        pd.DataFrame(
                            rows,
                            columns=[
                                "Nom",
                                "Début",
                                "Fin",
                                "Nb mesures",
                                "Supprimer",
                            ],
                        ),
                        width="stretch",
                        hide_index=True,
                        num_rows="fixed",
                        disabled=["Début", "Nb mesures"],
                        column_config={
                            "Nom": st.column_config.TextColumn(
                                "Nom",
                                required=True,
                                width="large",
                            ),
                            "Début": st.column_config.NumberColumn(
                                "Début",
                                min_value=1,
                                step=1,
                                width="small",
                            ),
                            "Fin": st.column_config.NumberColumn(
                                "Fin",
                                min_value=1,
                                max_value=total_measures,
                                step=1,
                                required=True,
                                width="small",
                                help=(
                                    "Entrée ou clic ailleurs : la suite est "
                                    "recalculée immédiatement."
                                ),
                            ),
                            "Nb mesures": st.column_config.NumberColumn(
                                "Nb mesures",
                                min_value=1,
                                step=1,
                                width="small",
                            ),
                            "Supprimer": st.column_config.CheckboxColumn(
                                "🗑",
                                width="small",
                                help=(
                                    "Cochez un ou plusieurs blocs, puis utilisez "
                                    "« Supprimer la sélection »."
                                ),
                            ),
                        },
                        key=(
                            f"structure_live_table_{audio_hash[:12]}_"
                            f"{revision}"
                        ),
                    )

                    edited_rows = edited_df.to_dict("records")

                    # Nom / Fin : recalcul immédiat après commit de cellule.
                    live_draft = _apply_structure_table_live_edit(
                        draft_blocks,
                        edited_rows,
                        total_measures,
                    )

                    if (
                        _canonical_structure_rows(live_draft)
                        != _canonical_structure_rows(draft_blocks)
                    ):
                        # Modification de cellule : conserver la même clé de tableau
                        # afin de ne pas perdre les cases cochées ni le focus.
                        st.session_state[
                            _structure_draft_key(audio_hash)
                        ] = [dict(b) for b in live_draft]
                        st.rerun()

                    assigned = sum(
                        int(b["measure_end"]) - int(b["measure_start"]) + 1
                        for b in draft_blocks
                    )
                    is_complete = (
                        bool(draft_blocks)
                        and int(draft_blocks[0]["measure_start"]) == 1
                        and int(draft_blocks[-1]["measure_end"]) == total_measures
                        and assigned == total_measures
                    )

                    status_col, delete_col, add_col = st.columns(
                        [2.2, 1.15, 1.15]
                    )

                    selected_delete_indices = [
                        i
                        for i, row in enumerate(edited_rows)
                        if bool(row.get("Supprimer"))
                    ]

                    with status_col:
                        if is_complete:
                            st.success(
                                f"✓ {assigned} / {total_measures} mesures affectées "
                                "— séquence continue."
                            )
                        else:
                            st.warning(
                                f"⚠ {assigned} / {total_measures} mesures affectées."
                            )

                        if _structure_draft_is_dirty(audio_hash):
                            st.warning(
                                "● Modifications non validées — le tableau visible "
                                "diffère de la dernière version persistée."
                            )
                        else:
                            st.caption(
                                "Aucune modification non validée dans le découpage."
                            )

                    with delete_col:
                        if st.button(
                            (
                                f"🗑 Supprimer ({len(selected_delete_indices)})"
                                if selected_delete_indices
                                else "🗑 Supprimer"
                            ),
                            key=f"delete_structure_selected_{audio_hash[:12]}",
                            width="stretch",
                            disabled=not bool(selected_delete_indices),
                            help=(
                                "Supprime en une seule opération tous les blocs "
                                "cochés dans le tableau."
                            ),
                        ):
                            # Appliquer d'abord les éventuelles modifications Nom/Fin
                            # visibles dans le tableau, puis supprimer la sélection.
                            current_draft = _apply_structure_table_live_edit(
                                draft_blocks,
                                edited_rows,
                                total_measures,
                            )
                            new_draft, message = _delete_structure_draft_rows(
                                current_draft,
                                selected_delete_indices,
                                total_measures,
                            )
                            _set_structure_draft(
                                audio_hash,
                                new_draft,
                                message,
                            )
                            st.rerun()

                    with add_col:
                        if st.button(
                            "＋ Ajouter un bloc en fin",
                            key=f"append_structure_{audio_hash[:12]}",
                            width="stretch",
                            help=(
                                "Crée un nouveau bloc final d'une mesure. "
                                "Ajustez ensuite la Fin du bloc précédent pour "
                                "agrandir le nouveau bloc."
                            ),
                        ):
                            new_draft, message = _append_structure_draft(
                                draft_blocks,
                                total_measures,
                            )
                            _set_structure_draft(
                                audio_hash,
                                new_draft,
                                message,
                            )
                            st.rerun()

                    validate_col, cancel_col, reset_col = st.columns(
                        [1.2, 1.2, 1.7]
                    )

                    with validate_col:
                        if st.button(
                            "✅ Valider ce découpage",
                            type="primary",
                            key=f"validate_structure_draft_{audio_hash[:12]}",
                            disabled=not _structure_draft_is_dirty(audio_hash),
                            help=(
                                "Persiste exactement le découpage visible et crée "
                                "une nouvelle version de la partition."
                            ),
                        ):
                            ok, message = _persist_structure_draft(
                                audio_hash,
                                draft_blocks,
                                total_measures,
                            )

                            if ok:
                                version_no = save_analysis_version(
                                    audio_hash=audio_hash,
                                    analysis_key=analysis_key,
                                    parameters=analysis_parameters,
                                    musique=musique,
                                    resultat=resultat,
                                )
                                st.session_state[
                                    "active_analysis_version_no"
                                ] = version_no
                                st.success(
                                    f"{message} Nouvelle version V{version_no} créée."
                                )
                                st.rerun()
                            else:
                                st.error(message)

                    with cancel_col:
                        if st.button(
                            "↩ Annuler les changements",
                            key=f"cancel_structure_draft_{audio_hash[:12]}",
                            disabled=not _structure_draft_is_dirty(audio_hash),
                            help="Revient au dernier découpage validé.",
                        ):
                            _set_structure_draft(
                                audio_hash,
                                persisted_blocks,
                                "Brouillon annulé ; retour au dernier découpage validé.",
                            )
                            st.rerun()

                    with reset_col:
                        with st.popover("⚙ Réinitialiser depuis l’analyse"):
                            st.warning(
                                "Supprime le découpage validé et les noms de blocs "
                                "personnalisés. L’analyse audio, Whisper et les "
                                "accords corrigés restent intacts."
                            )

                            if st.button(
                                "Confirmer la réinitialisation",
                                key=f"reset_structure_analysis_{audio_hash[:12]}",
                            ):
                                reset_structure_blocks_from_analysis(audio_hash)
                                st.session_state.pop(
                                    _structure_draft_key(audio_hash),
                                    None,
                                )
                                st.session_state[
                                    _structure_editor_revision_key(audio_hash)
                                ] = int(
                                    st.session_state.get(
                                        _structure_editor_revision_key(audio_hash),
                                        0,
                                    )
                                ) + 1
                                st.success(
                                    "Découpage supprimé. La structure sera "
                                    "reconstruite depuis l’analyse persistée."
                                )
                                st.rerun()


            with preview_col:
                st.markdown("### 🎤 Paroles + accords")
                st.caption(
                    "Aperçu live du découpage en cours. Les paroles et accords "
                    "suivent immédiatement les bornes du brouillon ; rien n'est "
                    "persisté avant « Valider ce découpage »."
                )

                _preview_measure_by_no = {
                    int(m["numero"]): m
                    for m in mesures_affichees
                }
                _preview_lyric_edits = load_lyric_block_edits(audio_hash)
                _preview_parts = [
                    '<div class="block-live-preview">',
                    '<div class="block-live-preview-caption">'
                    'Découpage courant — aperçu non persistant'
                    '</div>',
                ]

                for _preview_index, _preview_block in enumerate(draft_blocks):
                    _preview_m0 = int(_preview_block["measure_start"])
                    _preview_m1 = int(_preview_block["measure_end"])
                    _preview_first = _preview_measure_by_no.get(_preview_m0)
                    _preview_last = _preview_measure_by_no.get(_preview_m1)

                    if _preview_first is None or _preview_last is None:
                        continue

                    _preview_t0 = float(_preview_first["debut"])
                    _preview_t1 = float(_preview_last["fin"]) + 0.001
                    _preview_title = (
                        str(
                            _preview_block.get("custom_label", "") or ""
                        ).strip()
                        or f"Bloc {_preview_index + 1}"
                    )
                    _preview_key = _lyric_block_key(
                        _preview_t0,
                        _preview_t1,
                    )
                    _preview_edit = _preview_lyric_edits.get(
                        _preview_key,
                        {},
                    )
                    _preview_corrected = str(
                        _preview_edit.get("corrected_text", "") or ""
                    ).strip()

                    _preview_lines = construire_lignes_paroles_completes_intervalle(
                        mesures=mesures_affichees,
                        resultat=resultat,
                        t0=_preview_t0,
                        t1=_preview_t1,
                        max_chars=52,
                        corrected_block_text=_preview_corrected,
                    )

                    _preview_parts.append(
                        '<div class="block-live-card">'
                        '<div class="block-live-title">'
                        f'{html.escape(_preview_title)}'
                        '<span class="block-live-range">'
                        f'Mesures {_preview_m0}–{_preview_m1}'
                        '</span>'
                        '</div>'
                    )

                    if _preview_lines:
                        for _preview_line in _preview_lines:
                            _preview_parts.append(
                                '<div class="block-live-line">'
                                '<div class="block-live-chords">'
                                f'{html.escape(str(_preview_line.get("accords", "")))}'
                                '</div>'
                                '<div class="block-live-text">'
                                f'{html.escape(str(_preview_line.get("paroles", "")))}'
                                '</div>'
                                '</div>'
                            )
                    else:
                        _preview_parts.append(
                            '<div class="block-live-instrumental">'
                            '[instrumental]'
                            '</div>'
                        )

                    _preview_parts.append('</div>')

                _preview_parts.append('</div>')

                st.markdown(
                    ''.join(_preview_parts),
                    unsafe_allow_html=True,
                )

        if song_view == "Grille":
            st.subheader("🎼 Grille")

            if song_mode == "Vue":
                sections_for_view = (
                    sections_structurelles
                    if sections_structurelles
                    else [{
                        "cluster": "A",
                        "custom_label": "",
                        "measure_start": 1,
                        "measure_end": len(mesures_affichees),
                    }]
                )

                import html as _html_grid

                for section in sections_for_view:
                    m0 = int(section["measure_start"])
                    m1 = int(section["measure_end"])
                    title = libelle_bloc_affiche(section)

                    group = [
                        m for m in mesures_affichees
                        if m0 <= int(m["numero"]) <= m1
                    ]

                    rows_html = []

                    for row_start in range(0, len(group), 4):
                        row = group[row_start:row_start + 4]
                        cells = []

                        for idx in range(4):
                            if idx < len(row):
                                notation = _html_grid.escape(
                                    str(row[idx].get("notation", ""))
                                )
                                cells.append(
                                    '<td>'
                                    f'<span class="chord-grid-symbol">{notation}</span>'
                                    '</td>'
                                )
                            else:
                                cells.append("<td>&nbsp;</td>")

                        rows_html.append(
                            "<tr>" + "".join(cells) + "</tr>"
                        )

                    block_name_col, block_grid_col = st.columns(
                        [0.70, 4.30],
                        gap="small",
                    )

                    with block_name_col:
                        st.markdown(
                            '<div class="chord-block-name">'
                            f'{_html_grid.escape(str(title))}'
                            '</div>',
                            unsafe_allow_html=True,
                        )

                    with block_grid_col:
                        st.markdown(
                            SCORE.render(
                                "templates/views/grid.score",
                                {
                                    "view": {
                                        "rows_html": "".join(rows_html),
                                    }
                                },
                            ),
                            unsafe_allow_html=True,
                        )

                    st.markdown(
                        '<div style="height:0.35rem"></div>',
                        unsafe_allow_html=True,
                    )

                # Document papier autonome, non injecté dans le DOM Streamlit.
                sections_for_print = sections_for_view

                print_parts = ['<div class="print-sheet">']
                print_parts.append(
                    _print_song_header_html(
                        title=titre_affiche,
                        artist=artiste_affiche,
                        editor=song.get("editor", ""),
                        version_label=_version_label,
                        source_status=_source_status,
                        tempo=tempo,
                        signature=signature,
                        key_name=tonalite_nom,
                        capo=capo_user,
                        measures_count=len(mesures),
                        strumming_primary=song.get("strumming_primary", ""),
                        strumming_secondary=song.get("strumming_secondary", ""),
                    )
                )

                grid_print_blocks = []

                for section in sections_for_print:
                    m0 = int(section["measure_start"])
                    m1 = int(section["measure_end"])
                    title = libelle_bloc_affiche(section)

                    group = [
                        m for m in mesures_affichees
                        if m0 <= int(m["numero"]) <= m1
                    ]

                    rows_html = []
                    for row_start in range(0, len(group), 4):
                        row = group[row_start:row_start + 4]
                        cells = []

                        for idx in range(4):
                            if idx < len(row):
                                notation = html.escape(
                                    str(row[idx].get("notation", ""))
                                )
                                cells.append(f"<td>{notation}</td>")
                            else:
                                cells.append("<td>&nbsp;</td>")

                        rows_html.append(
                            "<tr>" + "".join(cells) + "</tr>"
                        )

                    estimated_height_mm = _print_grid_block_height_mm(
                        len(rows_html)
                    )
                    split_class = (
                        " print-allow-split"
                        if estimated_height_mm > _PRINT_PAGE_CONTENT_MM
                        else ""
                    )
                    block_html = (
                        f'<div class="print-grid-block{split_class}">'
                        f'<div class="print-grid-block-name">{html.escape(str(title))}</div>'
                        '<table class="print-chord-grid"><tbody>'
                        + "".join(rows_html)
                        + "</tbody></table>"
                        "</div>"
                    )
                    grid_print_blocks.append({
                        "html": block_html,
                        "height_mm": estimated_height_mm,
                    })

                print_parts.append(
                    _print_paginate_blocks(
                        grid_print_blocks,
                        first_page_used_mm=_PRINT_FIRST_PAGE_HEADER_MM,
                    )
                )
                print_parts.append("</div>")

                grid_print_document = _make_print_document(
                    "grid",
                    "".join(print_parts),
                    title=f"{titre_affiche} — Grille",
                )

                with print_slot.container():
                    _print_icon(
                        f"grid-{audio_hash[:10]}",
                        grid_print_document,
                    )

            elif song_mode == "Édition":
                # ----------------------------------------------------
                # GRILLE ÉDITABLE — 1 CASE = 1 MESURE
                # ----------------------------------------------------

                MESURES_PAR_LIGNE = 4

                st.caption(
                    "Édition musicale : une case = une mesure. "
                    "Notation EZScore conservée (Am---, Am-Em-, D.C-, etc.)."
                )

                st.markdown(
                    """
                    <style>
                    div[data-testid="stTextInput"] input {
                        font-family: Consolas, "Courier New", ui-monospace, monospace;
                        font-size: 1.68rem !important;
                        font-weight: 760 !important;
                        min-height: 2.15rem;
                        padding-top: 0.14rem !important;
                        padding-bottom: 0.14rem !important;
                    }
                    </style>
                    """,
                    unsafe_allow_html=True,
                )

                measure_edits = load_measure_edits(audio_hash)

                if sections_structurelles:
                    sections_for_grid = sections_structurelles
                else:
                    sections_for_grid = [{
                        "cluster": "A",
                        "custom_label": "",
                        "measure_start": 1,
                        "measure_end": len(mesures_affichees),
                    }]

                for section in sections_for_grid:
                    m0 = int(section["measure_start"])
                    m1 = int(section["measure_end"])
                    titre = libelle_bloc_affiche(section)

                    st.markdown(
                        f'<div class="song-block-title">{titre}</div>',
                        unsafe_allow_html=True,
                    )

                    groupe = [
                        m for m in mesures_affichees
                        if m0 <= int(m["numero"]) <= m1
                    ]

                    edited_values = {}

                    for row_start in range(
                        0,
                        len(groupe),
                        MESURES_PAR_LIGNE,
                    ):
                        row = groupe[
                            row_start:row_start + MESURES_PAR_LIGNE
                        ]
                        cols = st.columns(MESURES_PAR_LIGNE)

                        for col_idx in range(MESURES_PAR_LIGNE):
                            with cols[col_idx]:
                                if col_idx >= len(row):
                                    st.empty()
                                    continue

                                mesure = row[col_idx]
                                numero = int(mesure["numero"])

                                current_real = measure_edits.get(numero)
                                if current_real:
                                    current_display = (
                                        notation_affichee_depuis_reelle(
                                            current_real,
                                            signature,
                                            capo_user,
                                            beats_par_mesure_effectif,
                                        )
                                    )
                                else:
                                    current_display = str(
                                        mesure.get("notation", "")
                                    )

                                edited_values[numero] = st.text_input(
                                    f"Mesure {numero}",
                                    value=current_display,
                                    key=(
                                        f"measure_cell_"
                                        f"{audio_hash[:10]}_{numero}_"
                                        f"capo{capo_user}"
                                    ),
                                    label_visibility="collapsed",
                                )

                    save_col, reset_col = st.columns([1, 1])

                    with save_col:
                        if st.button(
                            f"✅ Valider {titre}",
                            key=(
                                f"save_grid_block_"
                                f"{audio_hash[:10]}_"
                                f"{section.get('block_id', m0)}"
                            ),
                            type="primary",
                            help=(
                                "Valide les accords de ce bloc et crée une "
                                "nouvelle version de la partition."
                            ),
                        ):
                            errors = []
                            converted = {}

                            for numero, display_notation in edited_values.items():
                                ok, notation_real, error = (
                                    notation_reelle_depuis_affichage(
                                        display_notation,
                                        signature,
                                        capo_user,
                                        beats_par_mesure_effectif,
                                    )
                                )

                                if not ok:
                                    errors.append(
                                        f"Mesure {numero} : {error}"
                                    )
                                else:
                                    converted[numero] = notation_real

                            if errors:
                                for error in errors:
                                    st.error(error)
                            else:
                                for numero, notation_real in converted.items():
                                    save_measure_edit(
                                        audio_hash,
                                        numero,
                                        notation_real,
                                    )

                                version_no = save_analysis_version(
                                    audio_hash=audio_hash,
                                    analysis_key=analysis_key,
                                    parameters=analysis_parameters,
                                    musique=musique,
                                    resultat=resultat,
                                )
                                st.session_state[
                                    "active_analysis_version_no"
                                ] = version_no
                                st.success(
                                    f"{titre} validé — nouvelle version "
                                    f"V{version_no} créée. "
                                    "Grille et parolier sont synchronisés."
                                )
                                st.rerun()

                    with reset_col:
                        if st.button(
                            f"↩ Réinitialiser {titre}",
                            key=(
                                f"reset_grid_block_"
                                f"{audio_hash[:10]}_"
                                f"{section.get('block_id', m0)}"
                            ),
                        ):
                            for mesure in groupe:
                                delete_measure_edit(
                                    audio_hash,
                                    int(mesure["numero"]),
                                )
                            st.rerun()

                    st.markdown(
                        '<div style="height:0.8rem"></div>',
                        unsafe_allow_html=True,
                    )
        if song_view == "Paroles + accords":
            # ----------------------------------------------------
            # PAROLES + ACCORDS — TIMELINE MONOSPACE
            # ----------------------------------------------------

            st.subheader("🎤 Paroles")

            def html_ligne_paroles(bloc):
                accords = html.escape(str(bloc.get("accords", "")))
                paroles = html.escape(str(bloc.get("paroles", "")))
                return (
                    '<div class="lyrics-line">'
                    f'<div class="lyrics-chords">{accords}</div>'
                    f'<div class="lyrics-text">{paroles}</div>'
                    '</div>'
                )

            # html.escape est utilisé pour rendre le texte saisi sans l'interpréter.
            import html

            edits_by_block = load_lyric_block_edits(audio_hash)
            editor_blocks = []
            html_lyrics = []
            has_lyrics = False

            def render_one_block(title, t0, t1):
                nonlocal_dummy = None
                source_words = _source_words_for_interval(resultat, t0, t1)
                original = " ".join(w["text"] for w in source_words).strip()
                block_key = _lyric_block_key(t0, t1)
                edit = edits_by_block.get(block_key, {})
                corrected = str(edit.get("corrected_text", "") or "").strip()

                lines = construire_lignes_paroles_intervalle(
                    mesures=mesures_affichees,
                    resultat=resultat,
                    t0=t0,
                    t1=t1,
                    max_chars=74,
                    corrected_block_text=corrected,
                )

                html_lyrics.append(
                    '<div class="lyrics-structure-block">'
                    f'<div class="lyrics-block-title">{html.escape(title)}</div>'
                )

                if lines:
                    for line in lines:
                        html_lyrics.append(html_ligne_paroles(line))
                else:
                    html_lyrics.append(
                        '<div class="lyrics-line">'
                        '<div class="lyrics-text" style="opacity:.55">'
                        '[instrumental]</div></div>'
                    )
                html_lyrics.append("</div>")

                if original:
                    editor_blocks.append({
                        "Bloc": title,
                        "block_key": block_key,
                        "original_text": original,
                        "text": corrected or original,
                        "debut": t0,
                        "fin": t1,
                    })
                return bool(lines)

            if sections_structurelles:
                for section in sections_structurelles:
                    title = libelle_bloc_affiche(section)
                    t0 = float(section["time_start"])
                    t1 = float(section["time_end"])
                    has_lyrics = render_one_block(title, t0, t1) or has_lyrics
            elif mesures_affichees:
                t0 = float(mesures_affichees[0]["debut"])
                t1 = float(mesures_affichees[-1]["fin"]) + 0.001
                has_lyrics = render_one_block("Morceau", t0, t1)

            if not has_lyrics:
                st.warning("Aucune parole horodatée n'a été détectée.")

            st.markdown(
                SCORE.render(
                    "templates/views/lyrics.score",
                    {
                        "view": {
                            "body_html": "".join(html_lyrics),
                        }
                    },
                ),
                unsafe_allow_html=True,
            )

            if song_mode == "Vue":
                print_lyrics = ['<div class="print-sheet">']
                print_lyrics.append(
                    _print_song_header_html(
                        title=titre_affiche,
                        artist=artiste_affiche,
                        editor=song.get("editor", ""),
                        version_label=_version_label,
                        source_status=_source_status,
                        tempo=tempo,
                        signature=signature,
                        key_name=tonalite_nom,
                        capo=capo_user,
                        measures_count=len(mesures),
                        strumming_primary=song.get("strumming_primary", ""),
                        strumming_secondary=song.get("strumming_secondary", ""),
                    )
                )

                lyrics_print_blocks = []

                for section in (
                    sections_structurelles
                    if sections_structurelles
                    else [{
                        "custom_label": "Morceau",
                        "cluster": "A",
                        "time_start": float(mesures_affichees[0]["debut"])
                            if mesures_affichees else 0.0,
                        "time_end": (
                            float(mesures_affichees[-1]["fin"]) + 0.001
                            if mesures_affichees else 0.001
                        ),
                    }]
                ):
                    block_title = (
                        libelle_bloc_affiche(section)
                        if sections_structurelles
                        else "Morceau"
                    )
                    t0_print = float(section["time_start"])
                    t1_print = float(section["time_end"])

                    block_key_print = _lyric_block_key(
                        t0_print, t1_print
                    )
                    edit_print = edits_by_block.get(
                        block_key_print, {}
                    )
                    corrected_print = str(
                        edit_print.get("corrected_text", "") or ""
                    ).strip()

                    lines_print = construire_lignes_paroles_completes_intervalle(
                        mesures=mesures_affichees,
                        resultat=resultat,
                        t0=t0_print,
                        t1=t1_print,
                        max_chars=74,
                        corrected_block_text=corrected_print,
                    )

                    line_count = max(1, len(lines_print))
                    estimated_height_mm = _print_lyrics_block_height_mm(
                        line_count
                    )
                    split_class = (
                        " print-allow-split"
                        if estimated_height_mm > _PRINT_PAGE_CONTENT_MM
                        else ""
                    )

                    block_parts = [
                        f'<div class="print-lyrics-block{split_class}">',
                        '<div class="print-lyrics-block-title">',
                        html.escape(str(block_title)),
                        '</div>',
                    ]

                    if lines_print:
                        for line_index, line in enumerate(lines_print):
                            _line_class = (
                                "print-lyrics-line print-lyrics-first-line"
                                if line_index == 0
                                else "print-lyrics-line"
                            )
                            block_parts.append(
                                f'<div class="{_line_class}">'
                                f'<div class="print-lyrics-chords">'
                                f'{html.escape(str(line.get("accords", "")))}</div>'
                                f'<div class="print-lyrics-text">'
                                f'{html.escape(str(line.get("paroles", "")))}</div>'
                                '</div>'
                            )
                    else:
                        block_parts.append(
                            '<div class="print-lyrics-line">'
                            '<div class="print-lyrics-text">[instrumental]</div>'
                            '</div>'
                        )

                    block_parts.append("</div>")
                    lyrics_print_blocks.append({
                        "html": "".join(block_parts),
                        "height_mm": estimated_height_mm,
                    })

                print_lyrics.append(
                    _print_paginate_blocks(
                        lyrics_print_blocks,
                        first_page_used_mm=_PRINT_FIRST_PAGE_HEADER_MM,
                    )
                )
                print_lyrics.append("</div>")

                lyrics_print_document = _make_print_document(
                    "lyrics",
                    "".join(print_lyrics),
                    title=f"{titre_affiche} — Paroles + accords",
                )

                with print_slot.container():
                    _print_icon(
                        f"lyrics-{audio_hash[:10]}",
                        lyrics_print_document,
                    )

            if editor_blocks and song_mode == "Édition":
                with st.expander("✏️ Corriger les paroles", expanded=False):
                    st.caption(
                        "Édition par bloc. Les accords ne bougent jamais. "
                        "Les retours à la ligne saisis ici sont conservés."
                    )

                    for idx, item in enumerate(editor_blocks):
                        st.markdown(f"**{item['Bloc']}**")
                        value = st.text_area(
                            f"Paroles — {item['Bloc']}",
                            value=item["text"],
                            height=140,
                            key=f"lyric_block_{audio_hash[:12]}_{item['block_key']}",
                            label_visibility="collapsed",
                        )
                        item["edited_text"] = value

                    save_col, reset_col = st.columns([1, 1])

                    with save_col:
                        if st.button(
                            "✅ Valider ces paroles",
                            type="primary",
                            key=f"save_lyrics_blocks_{audio_hash[:12]}",
                            help=(
                                "Valide les corrections de paroles de ce morceau "
                                "et crée une nouvelle version de la partition."
                            ),
                        ):
                            for item in editor_blocks:
                                save_lyric_block_edit(
                                    audio_hash=audio_hash,
                                    block_key=item["block_key"],
                                    original_text=item["original_text"],
                                    corrected_text=item.get("edited_text", ""),
                                    time_start=item["debut"],
                                    time_end=item["fin"],
                                )
                            version_no = save_analysis_version(
                                audio_hash=audio_hash,
                                analysis_key=analysis_key,
                                parameters=analysis_parameters,
                                musique=musique,
                                resultat=resultat,
                            )
                            st.session_state[
                                "active_analysis_version_no"
                            ] = version_no
                            st.success(
                                f"Paroles validées — V{version_no}. "
                                "Nouvelle version créée. Accords et timeline inchangés."
                            )
                            st.rerun()

                    with reset_col:
                        with st.popover("↩ Réinitialiser les paroles"):
                            st.warning(
                                "Supprime seulement les corrections de paroles "
                                "et revient au texte Whisper."
                            )
                            if st.button(
                                "Confirmer",
                                key=f"reset_lyrics_blocks_{audio_hash[:12]}",
                            ):
                                reset_lyric_block_edits(audio_hash)
                                st.rerun()

        # ----------------------------------------------------
        # STRUCTURE DU MORCEAU
        # ----------------------------------------------------

        if (
            song_view == "Blocs"
            and sections_enabled_user
            and song_mode == "Vue"
        ):
            st.markdown(
                SCORE.render(
                    "templates/views/blocks.score",
                    {
                        "view": {
                            "title": "Structure du morceau",
                            "caption_visible": bool(sections_structurelles),
                            "caption": (
                                "La détection propose les blocs initiaux ; les bornes "
                                "éditées, scissions et fusions constituent ensuite la "
                                "structure persistante du morceau."
                            ),
                        }
                    },
                ),
                unsafe_allow_html=True,
            )

            if not sections_structurelles:
                st.info(
                    "Aucune structure suffisamment exploitable n'a été détectée."
                )
            else:
                rows_structure = []

                for section in sections_structurelles:
                    rows_structure.append({
                        "Nom": libelle_bloc_affiche(section),
                        "Mesures": (
                            f'{section["measure_start"]}–'
                            f'{section["measure_end"]}'
                        ),
                        "Détection": (
                            f'{section.get("detected_measure_start", section["measure_start"])}–'
                            f'{section.get("detected_measure_end", section["measure_end"])}'
                        ),
                        "Confiance": (
                            f'{100.0 * section["confidence"]:.0f} %'
                        ),
                        "Répétitions": section["cluster_repeats"],
                        "Sim. harmonie": (
                            f'{100.0 * section["harmonic_repeat"]:.0f} %'
                        ),
                        "Sim. paroles": (
                            f'{100.0 * section["lyric_repeat"]:.0f} %'
                        ),
                        "Progression": " | ".join(
                            section.get("measure_patterns", [])
                        ),
                    })

                st.dataframe(
                    pd.DataFrame(rows_structure),
                    width="stretch",
                    hide_index=True,
                )

                # Résumé compact lisible pour le musicien.
                resume = "  →  ".join(
                    libelle_bloc_affiche(s)
                    for s in sections_structurelles
                )
                st.code(resume, language="text")

        # ----------------------------------------------------
        # ANALYSE — VUE AUTONOME
        # ----------------------------------------------------

        if song_view == "Analyse":
            st.markdown(
                SCORE.render(
                    "templates/views/analytic.score",
                    {
                        "view": {
                            "title": "Analyse",
                            "caption_visible": True,
                            "caption": (
                                "Déroulé harmonique interactif : zoom à la molette, "
                                "sélection d'une zone ou barre de navigation. "
                                "Les blocs structurels sont superposés au graphe."
                            ),
                        }
                    },
                ),
                unsafe_allow_html=True,
            )

            st.subheader("📊 Déroulé harmonique")

            regions = creer_regions_harmoniques(beats)

            if not regions:
                st.info("Aucune donnée harmonique disponible pour cette analyse.")
            else:
                fig, regions = creer_figure_deroule_riffstation(
                    beats=beats,
                    sections=sections_structurelles,
                    audio_bytes=audio_bytes,
                    extension=extension,
                )
                fig.update_layout(
                    uirevision=(
                        f"analyse-{audio_hash[:12]}-"
                        f"{_version_no if _version_no is not None else 'current'}"
                    )
                )

                st.plotly_chart(
                    fig,
                    width="stretch",
                    config={
                        "scrollZoom": True,
                        "displaylogo": False,
                        "responsive": True,
                    },
                )

                st.caption(
                    "Waveform + régions d'accords : zoom à la molette, "
                    "barre inférieure ou outils Plotly. Les corrections "
                    "manuelles d'accords sont reflétées automatiquement."
                )

                st.markdown("### 🎧 Comparaison audio / accords")

                _midi_bytes = build_midi_file(
                    beats=beats,
                    tempo=tempo,
                    signature=signature,
                    beats_per_measure=beats_par_mesure_effectif,
                    program=27,
                    gate_ratio=0.48,
                    strum_ms=12.0,
                )
                _midi_filename = (
                    re.sub(
                        r"[^A-Za-z0-9._-]+",
                        "_",
                        str(titre_affiche or "EZScore"),
                    ).strip("_")
                    or "EZScore"
                ) + "_accords.mid"

                midi_col, midi_info_col = st.columns([1.1, 2.0])

                with midi_col:
                    st.download_button(
                        "⬇ Télécharger le MIDI des accords",
                        data=_midi_bytes,
                        file_name=_midi_filename,
                        mime="audio/midi",
                        key=f"midi_{audio_hash[:12]}",
                    )

                with midi_info_col:
                    st.caption(
                        "Le MIDI et le player utilisent les accords effectifs, "
                        "y compris les corrections manuelles."
                    )

                st.caption(
                    "La lecture MIDI synchronisée est disponible dans "
                    "Grille > Jouer."
                )

            _phonetic_timeline = construire_timeline_phonetique(
                resultat
            )
            if _phonetic_timeline:
                st.markdown("### 🔤 Analyse phonétique expérimentale")
                st.caption(
                    "Couche française dérivée du texte Whisper et de ses "
                    "timestamps. Les liaisons probables sont explicitées. "
                    "Cette R12 prépare l'alignement phonème acoustique ; "
                    "elle ne prétend pas encore détecter chaque phonème "
                    "directement dans le signal."
                )

                _phonetic_groups = construire_groupes_phonetiques(
                    _phonetic_timeline
                )

                if _phonetic_groups:
                    preview_rows = []
                    for group in _phonetic_groups[:24]:
                        preview_rows.append({
                            "Temps": (
                                f"{group['debut']:.2f}–"
                                f"{group['fin']:.2f}s"
                            ),
                            "Paroles": group["texte"],
                            "Phonétique": group["phonetique"],
                        })

                    st.dataframe(
                        pd.DataFrame(preview_rows),
                        width="stretch",
                        hide_index=True,
                    )

                    if len(_phonetic_groups) > 24:
                        st.caption(
                            f"{len(_phonetic_groups) - 24} groupe(s) "
                            "phonétique(s) supplémentaire(s) non affiché(s)."
                        )

            st.markdown("### Diagnostics")

            diag_left, diag_right = st.columns(2)

            with diag_left:
                st.write(
                    f"Langue détectée : **{resultat.get('language', '?')}**"
                )
                st.write(f"Whisper : **{DEVICE.upper()}**")
                st.write(
                    f"Signature utilisée : **{signature}** "
                    f"({beats_par_mesure_effectif} positions/mesure)"
                )
                st.write(
                    "Balance harmonique : "
                    f"**{100 * poids_fondamentale_effectif:.0f} % fondamentale / "
                    f"{100 * poids_accompagnement_effectif:.0f} % accompagnement**"
                )
                st.write(
                    "Capodastre (affichage seulement) : "
                    f"**{capo_user}**"
                )
                st.write(f"Tonalité estimée : **{tonalite_nom}**")

                if tonalite:
                    st.write(
                        "Confiance tonalité : "
                        f"**{100.0 * tonalite.get('confidence', 0.0):.0f} %**"
                    )

                if signature_mode_effective == "Auto" and signature_auto:
                    st.write(
                        "Confiance signature : "
                        f"**{100.0 * signature_auto.get('confiance', 0.0):.0f} %**"
                    )
                    st.write(
                        "Phase d'accent proposée : "
                        f"**{signature_auto.get('phase', 0)}**"
                    )

                    scores_signatures = signature_auto.get("scores", {})
                    if scores_signatures:
                        scores_txt = " · ".join(
                            f"{k}: {v:+.2f}"
                            for k, v in sorted(scores_signatures.items())
                        )
                        st.caption(
                            "Scores métriques (diagnostic) — "
                            + scores_txt
                        )

                    st.caption(
                        "Auto-mètre expérimental : il estime un groupement "
                        "d'accents, pas encore un downbeat musicologique complet."
                    )

            with diag_right:
                st.write(
                    "Source accords : **ensemble R12 "
                    "Demucs no_vocals + mix original**"
                )
                _source_mix = dict(
                    musique.get("harmonic_source_mix", {}) or {}
                )
                if _source_mix:
                    st.write(
                        "Fusion harmonique : "
                        f"**{100 * float(_source_mix.get('no_vocals', 0.0)):.0f} % "
                        "no_vocals / "
                        f"{100 * float(_source_mix.get('original_mix', 0.0)):.0f} % "
                        "mix original**"
                    )

                st.write(
                    "Corrections par preuve locale forte : "
                    f"**{int(musique.get('local_evidence_overrides', 0) or 0)}**"
                )

                if accords_dominants:
                    st.write(
                        "Accords dominants appris : "
                        f"**{' / '.join(accords_dominants)}**"
                    )

                if vocabulaire:
                    st.write(
                        "Vocabulaire harmonique : "
                        f"**{', '.join(vocabulaire)}**"
                    )

                if accords_dominants:
                    etat_alternance = (
                        "active"
                        if alternance_active
                        else "non confirmée"
                    )

                    st.write(
                        "Motif dominant : "
                        f"**{accords_dominants[0]} ↔ {accords_dominants[1]}** "
                        f"({etat_alternance})"
                    )
                    st.write(
                        "Couverture du couple : "
                        f"**{100.0 * couverture_pair:.0f} %**"
                    )
                    st.write(
                        "Taux d'alternance : "
                        f"**{100.0 * taux_alternance_pair:.0f} %**"
                    )

                nb_silences = sum(
                    1 for b in beats if b["accord"] == "."
                )
                nb_fermata = sum(
                    1 for m in mesures if m["fermata"]
                )
                changements = sum(
                    1
                    for i in range(1, len(beats))
                    if beats[i]["accord"] != beats[i - 1]["accord"]
                    and beats[i]["accord"] != "."
                    and beats[i - 1]["accord"] != "."
                )

                st.write(f"Beats non joués détectés : **{nb_silences}**")
                st.write(f"Points d'orgue détectés : **{nb_fermata}**")
                st.write(f"Changements harmoniques : **{changements}**")
                st.write(
                    "Sections structurelles : "
                    f"**{len(sections_structurelles)}**"
                )
                st.write(
                    "Corrections de grille : "
                    f"**{len(load_measure_edits(audio_hash))} mesure(s) éditée(s)**"
                )

                if DEVICE == "cuda":
                    st.write(
                        f"GPU : **{torch.cuda.get_device_name(0)}**"
                    )
                    memoire_gpu = torch.cuda.memory_allocated(0) / 1024**2
                    st.write(f"VRAM utilisée : **{memoire_gpu:.0f} Mo**")

            _grid_refinement = dict(
                musique.get("beat_grid_refinement", {}) or {}
            )

            st.markdown("### Résolution rythmique / harmonique")

            rhythm_cols = st.columns(4)

            with rhythm_cols[0]:
                st.metric(
                    "Tempo brut",
                    f"{float(musique.get('tempo_brut', tempo)):.1f} BPM",
                )
            with rhythm_cols[1]:
                st.metric(
                    "Tempo effectif",
                    f"{float(musique.get('tempo', tempo)):.1f} BPM",
                )
            with rhythm_cols[2]:
                st.metric(
                    "Grille ×2",
                    (
                        "Active"
                        if _grid_refinement.get("accepted", False)
                        else "Non"
                    ),
                )
            with rhythm_cols[3]:
                st.metric(
                    "Régions harmoniques",
                    str(int(musique.get("harmonic_regions", 0) or 0)),
                )

            if _grid_refinement:
                st.caption(
                    "Preuve subdivision intermédiaire : "
                    f"{100.0 * float(_grid_refinement.get('midpoint_coverage', 0.0)):.0f} % "
                    "des milieux soutenus · "
                    "force médiane "
                    f"{float(_grid_refinement.get('midpoint_strength_ratio', 0.0)):.2f}× "
                    "les beats bruts."
                )

                if _grid_refinement.get("accepted", False):
                    st.success(
                        "Ambiguïté d'octave validée par le signal : "
                        f"{_grid_refinement.get('raw_tempo', 0.0):.1f} BPM / "
                        f"{_grid_refinement.get('raw_signature', '?')} → "
                        f"{_grid_refinement.get('effective_tempo', 0.0):.1f} BPM / "
                        f"{_grid_refinement.get('effective_signature', '?')}. "
                        "L'éditeur manuel utilise automatiquement cette grille plus fine."
                    )

            _perf = dict(
                musique.get("performance", {}) or {}
            )
            if _perf:
                st.markdown("### Performances")
                perf_cols = st.columns(4)

                with perf_cols[0]:
                    st.metric(
                        "Demucs",
                        f"{_perf.get('demucs_seconds', 0.0):.1f} s",
                    )
                with perf_cols[1]:
                    st.metric(
                        "Rythme + harmonie",
                        f"{(
                            _perf.get('rhythm_seconds', 0.0)
                            + _perf.get('harmony_seconds', 0.0)
                        ):.1f} s",
                    )
                with perf_cols[2]:
                    st.metric(
                        "Whisper",
                        f"{_perf.get('whisper_seconds', 0.0):.1f} s",
                    )
                with perf_cols[3]:
                    st.metric(
                        "Total",
                        f"{_perf.get('total_seconds', _perf.get('parallel_seconds', 0.0)):.1f} s",
                    )

                st.caption(
                    "Demucs et Whisper s'exécutent en parallèle ; "
                    "le total n'est donc pas la somme des colonnes."
                )

            _micro_stab = int(
                musique.get(
                    "micro_variations_stabilisees",
                    0,
                )
                or 0
            )
            st.write(
                "Micro-variations harmoniques stabilisées : "
                f"**{_micro_stab}**"
            )
            st.write(
                "Changements harmoniques validés : "
                f"**{int(musique.get('hysteresis_switches', 0) or 0)}**"
            )
            st.write(
                "Candidats faibles rejetés : "
                f"**{int(musique.get('hysteresis_rejected_candidates', 0) or 0)}**"
            )
            st.write(
                "Accords courts conservés : "
                f"**{int(musique.get('strong_short_chords_kept', 0) or 0)}**"
            )

            st.markdown("### Source et persistance")
            st.write(
                "Persistance : "
                + (
                    "**analyse rechargée depuis SQLite**"
                    if analyse_source in (
                        "persisted_version",
                        "persisted_exact",
                        "persisted_latest",
                    )
                    else "**analyse calculée puis sauvegardée dans SQLite**"
                )
            )
            st.caption(
                f"Identité audio : {audio_hash[:16]}… · "
                f"moteur : {ANALYSIS_ENGINE_VERSION}"
            )
            st.caption(
                "Bibliothèque : métadonnées + analyse en SQLite, "
                "audio archivé dans data/audio."
            )

    except Exception as e:
        st.error(f"Erreur pendant l'analyse : {e}")
        st.exception(e)
