import streamlit as st
import html
import numpy as np
import librosa
import plotly.express as px
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
from datetime import datetime, timezone
from pathlib import Path
import torch
import whisper
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
from collections import Counter
from EZScoreTemplate import ScoreTemplateRenderer

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
    "Les réglages avancés sont mémorisés par chanson après « Appliquer ». "
    "Le capo est mémorisé immédiatement et ne relance jamais l'analyse."
)

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




def normaliser_symboles_mesure(symboles):
    """
    Canonicalise exactement une mesure beat par beat.

    Exemple:
        ["Am", "Am", "Em", "Em"] -> ["Am", "-", "Em", "-"]

    Important:
    - un accord identique au beat précédent devient '-'
    - '.' coupe la tenue
    - aucun doublon consécutif du type 'AmAm-' ne doit survivre
    """
    resultat = []
    precedent = None

    for symbole in symboles:
        if symbole == ".":
            resultat.append(".")
            precedent = None
        elif symbole == "-":
            # '-' explicite n'est valide que si un accord actif le précède.
            if precedent is not None:
                resultat.append("-")
            else:
                resultat.append(".")
        elif symbole == precedent:
            resultat.append("-")
        else:
            resultat.append(symbole)
            precedent = symbole

    return resultat



def formatter_mesure(symboles, fermata=False):
    """
    Exemples :
      ["Am", "Am", "Am", "Am"] -> Am---
      ["Am", "Am", "Em", "Em"] -> Am-Em-
      ["D", ".", "C", "C"]     -> D.C-
    """
    if not symboles:
        return ""

    symboles = normaliser_symboles_mesure(symboles)
    resultat = "".join(symboles)

    if fermata:
        resultat += "^"

    return resultat



def formatter_mesure_signature(symboles, signature, fermata=False):
    """
    Affichage des signatures composées par groupes ternaires.

    6/8  -> 3+3
    12/8 -> 3+3+3+3

    Chaque groupe est formaté indépendamment afin qu'un accord tenu sur
    deux grandes pulsations reste lisible à la guitare :
      Cm Cm Cm Cm Cm Cm -> "Cm-- | Cm--"
      Cm Cm Cm Fm Fm Fm -> "Cm-- | Fm--"
    """
    if signature not in ("6/8", "12/8"):
        return formatter_mesure(symboles, fermata=fermata)

    groupes = []
    for i in range(0, len(symboles), 3):
        groupe = symboles[i:i + 3]
        if groupe:
            groupes.append(
                formatter_mesure(groupe, fermata=False)
            )

    resultat = " | ".join(groupes)
    if fermata:
        resultat += "^"
    return resultat


# ============================================================
# CAPODASTRE — COUCHE D'AFFICHAGE UNIQUEMENT
# ============================================================

_NOTES_SHARP = [
    "C", "C#", "D", "D#", "E", "F",
    "F#", "G", "G#", "A", "A#", "B"
]

_NOTE_TO_PC = {
    "C": 0, "B#": 0,
    "C#": 1, "Db": 1,
    "D": 2,
    "D#": 3, "Eb": 3,
    "E": 4, "Fb": 4,
    "E#": 5, "F": 5,
    "F#": 6, "Gb": 6,
    "G": 7,
    "G#": 8, "Ab": 8,
    "A": 9,
    "A#": 10, "Bb": 10,
    "B": 11, "Cb": 11,
}


def accord_forme_capo(accord_reel, capo):
    """
    Convertit uniquement le NOM affiché de l'accord.

    Exemple :
      accord réel Cm, capo 3 -> Am

    L'analyse et la tonalité réelle restent inchangées.
    Le suffixe est conservé : m, 7, maj7, dim, etc.
    """
    if not accord_reel or accord_reel in (".", "-", "?", "^"):
        return accord_reel

    capo = int(capo or 0)
    if capo == 0:
        return accord_reel

    # Racine = lettre + éventuel #/b.
    root = accord_reel[0]
    suffix_start = 1

    if len(accord_reel) >= 2 and accord_reel[1] in ("#", "b"):
        root += accord_reel[1]
        suffix_start = 2

    if root not in _NOTE_TO_PC:
        return accord_reel

    pc_reel = _NOTE_TO_PC[root]
    pc_forme = (pc_reel - capo) % 12

    return _NOTES_SHARP[pc_forme] + accord_reel[suffix_start:]


def preparer_mesures_affichage(mesures, signature, capo):
    """
    Construit une copie d'affichage des mesures.

    - `accords` internes restent les accords réels détectés ;
    - `notation` affichée devient la forme à jouer avec le capo.
    """
    resultat = []

    for mesure in mesures:
        accords_affiches = [
            accord_forme_capo(a, capo)
            for a in mesure.get("accords", [])
        ]

        copie = dict(mesure)
        copie["accords_affiches"] = accords_affiches
        copie["notation"] = formatter_mesure_signature(
            accords_affiches,
            signature,
            fermata=bool(mesure.get("fermata", False))
        )
        resultat.append(copie)

    return resultat



# ============================================================
# PERSISTANCE EZScore — SQLITE
# ============================================================

PERSISTENCE_SCHEMA_VERSION = 1
ANALYSIS_ENGINE_VERSION = "V25_V9_DEMUCS_STRUCTURE_PROGRESSIONS"

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
AUDIO_DIR = DATA_DIR / "audio"
DB_PATH = DATA_DIR / "EZScore.sqlite3"


def _utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def _json_safe(value):
    """Convertit récursivement les types numpy en JSON standard."""
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    return value


def init_persistence():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS songs (
                audio_hash TEXT PRIMARY KEY,
                original_filename TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT '',
                artist TEXT NOT NULL DEFAULT '',
                editor TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        song_columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(songs)"
            ).fetchall()
        }

        if "editor" not in song_columns:
            conn.execute(
                "ALTER TABLE songs ADD COLUMN editor TEXT NOT NULL DEFAULT ''"
            )

        if "strumming_primary" not in song_columns:
            conn.execute(
                "ALTER TABLE songs ADD COLUMN strumming_primary "
                "TEXT NOT NULL DEFAULT ''"
            )

        if "strumming_secondary" not in song_columns:
            conn.execute(
                "ALTER TABLE songs ADD COLUMN strumming_secondary "
                "TEXT NOT NULL DEFAULT ''"
            )

        conn.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                audio_hash TEXT NOT NULL,
                analysis_key TEXT NOT NULL,
                engine_version TEXT NOT NULL,
                parameters_json TEXT NOT NULL,
                music_json TEXT NOT NULL,
                whisper_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (audio_hash, analysis_key),
                FOREIGN KEY (audio_hash) REFERENCES songs(audio_hash)
                    ON DELETE CASCADE
            )
        """)

        # Prépare la future édition de noms de blocs sans l'activer
        # dans l'interface V25.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS block_edits (
                audio_hash TEXT NOT NULL,
                block_cluster TEXT NOT NULL,
                custom_label TEXT NOT NULL DEFAULT '',
                measure_start INTEGER,
                measure_end INTEGER,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (audio_hash, block_cluster),
                FOREIGN KEY (audio_hash) REFERENCES songs(audio_hash)
                    ON DELETE CASCADE
            )
        """)

        columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(block_edits)"
            ).fetchall()
        }

        if "measure_start" not in columns:
            conn.execute(
                "ALTER TABLE block_edits ADD COLUMN measure_start INTEGER"
            )

        if "measure_end" not in columns:
            conn.execute(
                "ALTER TABLE block_edits ADD COLUMN measure_end INTEGER"
            )


        conn.execute("""
            CREATE TABLE IF NOT EXISTS analysis_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                audio_hash TEXT NOT NULL,
                analysis_key TEXT NOT NULL,
                version_no INTEGER NOT NULL,
                parameters_json TEXT NOT NULL,
                music_json TEXT NOT NULL,
                whisper_json TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT '',
                artist TEXT NOT NULL DEFAULT '',
                editor TEXT NOT NULL DEFAULT '',
                capo INTEGER NOT NULL DEFAULT 0,
                structure_json TEXT NOT NULL DEFAULT '[]',
                measure_edits_json TEXT NOT NULL DEFAULT '{}',
                lyric_edits_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                UNIQUE(audio_hash, version_no),
                FOREIGN KEY (audio_hash) REFERENCES songs(audio_hash)
                    ON DELETE CASCADE
            )
        """)

        version_columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(analysis_versions)"
            ).fetchall()
        }

        _version_migrations = {
            "title": "TEXT NOT NULL DEFAULT ''",
            "artist": "TEXT NOT NULL DEFAULT ''",
            "editor": "TEXT NOT NULL DEFAULT ''",
            "capo": "INTEGER NOT NULL DEFAULT 0",
            "structure_json": "TEXT NOT NULL DEFAULT '[]'",
            "measure_edits_json": "TEXT NOT NULL DEFAULT '{}'",
            "lyric_edits_json": "TEXT NOT NULL DEFAULT '{}'",
            "strumming_primary": "TEXT NOT NULL DEFAULT ''",
            "strumming_secondary": "TEXT NOT NULL DEFAULT ''",
        }

        for _column, _sql_type in _version_migrations.items():
            if _column not in version_columns:
                conn.execute(
                    f"ALTER TABLE analysis_versions "
                    f"ADD COLUMN {_column} {_sql_type}"
                )

        conn.execute("""
            CREATE TABLE IF NOT EXISTS song_editorial_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                audio_hash TEXT NOT NULL,
                version_no INTEGER NOT NULL,
                release_no INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'validated',
                source_analysis_version_no INTEGER,
                note TEXT NOT NULL DEFAULT '',
                validated_at TEXT NOT NULL,
                published_at TEXT,
                updated_at TEXT NOT NULL,
                UNIQUE(audio_hash, version_no),
                FOREIGN KEY (audio_hash) REFERENCES songs(audio_hash)
                    ON DELETE CASCADE
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS song_workflow (
                audio_hash TEXT PRIMARY KEY,
                state TEXT NOT NULL DEFAULT 'working',
                current_version_no INTEGER,
                working_note TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL,
                FOREIGN KEY (audio_hash) REFERENCES songs(audio_hash)
                    ON DELETE CASCADE
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS beat_edits (
                audio_hash TEXT NOT NULL,
                beat_index INTEGER NOT NULL,
                chord_override TEXT,
                time_offset_ms REAL NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (audio_hash, beat_index),
                FOREIGN KEY (audio_hash) REFERENCES songs(audio_hash)
                    ON DELETE CASCADE
            )
        """)


        conn.execute("""
            CREATE TABLE IF NOT EXISTS app_state (
                state_key TEXT PRIMARY KEY,
                state_value TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS song_preferences (
                audio_hash TEXT PRIMARY KEY,
                capo INTEGER NOT NULL DEFAULT 0,
                settings_json TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL,
                FOREIGN KEY (audio_hash) REFERENCES songs(audio_hash)
                    ON DELETE CASCADE
            )
        """)


        conn.execute("""
            CREATE TABLE IF NOT EXISTS structure_blocks (
                audio_hash TEXT NOT NULL,
                block_id INTEGER NOT NULL,
                order_index INTEGER NOT NULL,
                cluster TEXT NOT NULL,
                custom_label TEXT NOT NULL DEFAULT '',
                measure_start INTEGER NOT NULL,
                measure_end INTEGER NOT NULL,
                detected_measure_start INTEGER,
                detected_measure_end INTEGER,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (audio_hash, block_id),
                FOREIGN KEY (audio_hash) REFERENCES songs(audio_hash)
                    ON DELETE CASCADE
            )
        """)


        conn.execute("""
            CREATE TABLE IF NOT EXISTS measure_edits (
                audio_hash TEXT NOT NULL,
                measure_no INTEGER NOT NULL,
                notation_real TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (audio_hash, measure_no),
                FOREIGN KEY (audio_hash) REFERENCES songs(audio_hash)
                    ON DELETE CASCADE
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS lyric_block_edits (
                audio_hash TEXT NOT NULL,
                block_key TEXT NOT NULL,
                original_text TEXT NOT NULL DEFAULT '',
                corrected_text TEXT NOT NULL DEFAULT '',
                time_start REAL NOT NULL,
                time_end REAL NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (audio_hash, block_key),
                FOREIGN KEY (audio_hash) REFERENCES songs(audio_hash)
                    ON DELETE CASCADE
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS lyric_line_edits (
                audio_hash TEXT NOT NULL,
                line_key TEXT NOT NULL,
                original_text TEXT NOT NULL DEFAULT '',
                corrected_text TEXT NOT NULL DEFAULT '',
                time_start REAL NOT NULL,
                time_end REAL NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (audio_hash, line_key),
                FOREIGN KEY (audio_hash) REFERENCES songs(audio_hash)
                    ON DELETE CASCADE
            )
        """)

        conn.commit()


def audio_sha256(audio_bytes):
    return hashlib.sha256(audio_bytes).hexdigest()




def _lyric_block_key(time_start, time_end):
    payload = f"{float(time_start):.3f}|{float(time_end):.3f}"
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def load_lyric_block_edits(audio_hash):
    if not audio_hash:
        return {}
    try:
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(
                """
                SELECT block_key, original_text, corrected_text,
                       time_start, time_end
                FROM lyric_block_edits
                WHERE audio_hash = ?
                """,
                (str(audio_hash),),
            ).fetchall()
    except sqlite3.OperationalError:
        return {}

    return {
        r[0]: {
            "original_text": r[1] or "",
            "corrected_text": r[2] or "",
            "time_start": float(r[3]),
            "time_end": float(r[4]),
        }
        for r in rows
    }


def save_lyric_block_edit(
    audio_hash, block_key, original_text, corrected_text,
    time_start, time_end,
):
    original = str(original_text or "").strip()
    corrected = str(corrected_text or "").strip()

    with sqlite3.connect(DB_PATH) as conn:
        if not corrected or corrected == original:
            conn.execute(
                "DELETE FROM lyric_block_edits "
                "WHERE audio_hash = ? AND block_key = ?",
                (str(audio_hash), str(block_key)),
            )
        else:
            conn.execute(
                """
                INSERT INTO lyric_block_edits (
                    audio_hash, block_key, original_text, corrected_text,
                    time_start, time_end, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(audio_hash, block_key)
                DO UPDATE SET
                    original_text = excluded.original_text,
                    corrected_text = excluded.corrected_text,
                    time_start = excluded.time_start,
                    time_end = excluded.time_end,
                    updated_at = excluded.updated_at
                """,
                (
                    str(audio_hash), str(block_key), original, corrected,
                    float(time_start), float(time_end), _utc_now_iso(),
                ),
            )
        conn.commit()


def reset_lyric_block_edits(audio_hash):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "DELETE FROM lyric_block_edits WHERE audio_hash = ?",
            (str(audio_hash),),
        )
        # Nettoie aussi les anciennes corrections ligne-à-ligne V38c.
        conn.execute(
            "DELETE FROM lyric_line_edits WHERE audio_hash = ?",
            (str(audio_hash),),
        )
        conn.commit()


def _source_words_for_interval(resultat, t0, t1):
    words = []
    for word in extraire_mots(resultat):
        w0 = float(word["start"])
        w1 = float(word["end"])
        midpoint = (w0 + w1) / 2.0
        if float(t0) <= midpoint < float(t1):
            txt = str(word["text"]).strip()
            if txt:
                words.append({
                    "text": txt,
                    "start": w0,
                    "end": w1,
                })
    return words


def _redistribute_corrected_block_text(corrected_text, source_words):
    """
    Redistribue le texte corrigé sur LA MÊME fenêtre vocale.
    Les accords et leurs timestamps ne changent pas.
    Les retours à la ligne saisis sont conservés.
    """
    if not source_words:
        return []

    lines = [
        line.strip()
        for line in str(corrected_text or "").splitlines()
        if line.strip()
    ]
    if not lines:
        return [
            {**w, "manual_line_end": False}
            for w in source_words
        ]

    tokens = []
    line_ends = set()
    for line in lines:
        parts = re.findall(r"\S+", line)
        tokens.extend(parts)
        if parts:
            line_ends.add(len(tokens) - 1)

    if not tokens:
        return []

    src_centers = np.asarray([
        (float(w["start"]) + float(w["end"])) / 2.0
        for w in source_words
    ], dtype=float)

    if len(tokens) == 1:
        centers = np.asarray([(src_centers[0] + src_centers[-1]) / 2.0])
    elif len(src_centers) == 1:
        centers = np.linspace(
            float(source_words[0]["start"]),
            float(source_words[-1]["end"]),
            len(tokens),
        )
    else:
        centers = np.interp(
            np.linspace(0.0, 1.0, len(tokens)),
            np.linspace(0.0, 1.0, len(src_centers)),
            src_centers,
        )

    start_block = float(source_words[0]["start"])
    end_block = float(source_words[-1]["end"])
    duration = max(end_block - start_block, 1e-6)
    nominal = min(0.40, max(0.06, duration / max(len(tokens) * 2.5, 1)))

    result = []
    prev_end = start_block
    for i, (token, center) in enumerate(zip(tokens, centers)):
        start = max(start_block, float(center) - nominal / 2, prev_end)
        end = min(end_block, max(start + 0.02, float(center) + nominal / 2))
        result.append({
            "text": token,
            "start": float(start),
            "end": float(end),
            "manual_line_end": i in line_ends,
        })
        prev_end = float(end)

    return result


def _lyric_line_key(time_start, time_end, original_text):
    payload = (
        f"{float(time_start):.3f}|"
        f"{float(time_end):.3f}|"
        f"{str(original_text).strip()}"
    )
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def load_lyric_line_edits(audio_hash):
    if not audio_hash:
        return {}

    try:
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(
                """
                SELECT
                    line_key,
                    original_text,
                    corrected_text,
                    time_start,
                    time_end
                FROM lyric_line_edits
                WHERE audio_hash = ?
                """,
                (str(audio_hash),),
            ).fetchall()
    except sqlite3.OperationalError:
        return {}

    return {
        row[0]: {
            "original_text": row[1] or "",
            "corrected_text": row[2] or "",
            "time_start": float(row[3]),
            "time_end": float(row[4]),
        }
        for row in rows
    }


def save_lyric_line_edit(
    audio_hash,
    line_key,
    original_text,
    corrected_text,
    time_start,
    time_end,
):
    """
    Corrige uniquement le texte de la ligne.
    Aucun accord, beat, timestamp audio ou résultat d'analyse n'est modifié.
    """
    corrected = str(corrected_text or "").strip()

    with sqlite3.connect(DB_PATH) as conn:
        if not corrected or corrected == str(original_text or "").strip():
            conn.execute(
                """
                DELETE FROM lyric_line_edits
                WHERE audio_hash = ? AND line_key = ?
                """,
                (str(audio_hash), str(line_key)),
            )
        else:
            conn.execute(
                """
                INSERT INTO lyric_line_edits (
                    audio_hash,
                    line_key,
                    original_text,
                    corrected_text,
                    time_start,
                    time_end,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(audio_hash, line_key)
                DO UPDATE SET
                    original_text = excluded.original_text,
                    corrected_text = excluded.corrected_text,
                    time_start = excluded.time_start,
                    time_end = excluded.time_end,
                    updated_at = excluded.updated_at
                """,
                (
                    str(audio_hash),
                    str(line_key),
                    str(original_text or "").strip(),
                    corrected,
                    float(time_start),
                    float(time_end),
                    _utc_now_iso(),
                ),
            )
        conn.commit()


def reset_lyric_line_edits(audio_hash):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "DELETE FROM lyric_line_edits WHERE audio_hash = ?",
            (str(audio_hash),),
        )
        conn.commit()


def _words_from_corrected_text(corrected_text, source_words):
    """
    Redistribue une phrase corrigée DANS LA MÊME FENÊTRE TEMPORELLE.

    Les accords ne bougent jamais.

    Whisper ne donnant ici que des timestamps par mot, on interpole les
    nouveaux mots sur les centres temporels des mots originaux. Cela permet
    de remplacer, par exemple :

        "nous deux mangerons calaux sur l'œil"

    par :

        "Nous ne mangions qu'un jour sur deux"

    sans déplacer la timeline harmonique.
    """
    tokens = re.findall(r"\\S+", str(corrected_text or "").strip())
    if not tokens:
        return []

    if not source_words:
        return []

    source_centers = np.asarray(
        [
            (float(w["start"]) + float(w["end"])) / 2.0
            for w in source_words
        ],
        dtype=float,
    )

    line_start = float(source_words[0]["start"])
    line_end = float(source_words[-1]["end"])
    line_duration = max(line_end - line_start, 1e-6)

    if len(tokens) == 1:
        centers = np.asarray(
            [(line_start + line_end) / 2.0],
            dtype=float,
        )
    elif len(source_centers) == 1:
        centers = np.linspace(
            line_start,
            line_end,
            num=len(tokens),
        )
    else:
        src_axis = np.linspace(0.0, 1.0, num=len(source_centers))
        dst_axis = np.linspace(0.0, 1.0, num=len(tokens))
        centers = np.interp(
            dst_axis,
            src_axis,
            source_centers,
        )

    # Durée locale de chaque nouveau mot : assez courte pour ne pas
    # faire chevaucher artificiellement les ancrages, mais non nulle.
    nominal = min(
        0.45,
        max(0.08, line_duration / max(len(tokens) * 2.2, 1.0)),
    )

    result = []
    previous_end = line_start

    for i, (token, center) in enumerate(zip(tokens, centers)):
        start = max(
            line_start,
            float(center) - nominal / 2.0,
            previous_end,
        )

        if i + 1 < len(centers):
            next_center = float(centers[i + 1])
            end = min(
                line_end,
                float(center) + nominal / 2.0,
                max(start + 0.02, (float(center) + next_center) / 2.0),
            )
        else:
            end = min(
                line_end,
                max(start + 0.02, float(center) + nominal / 2.0),
            )

        result.append({
            "text": token,
            "start": float(start),
            "end": float(max(end, start + 0.02)),
        })
        previous_end = float(max(end, start + 0.02))

    return result


def get_app_state(state_key, default=""):
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            """
            SELECT state_value
            FROM app_state
            WHERE state_key = ?
            """,
            (state_key,),
        ).fetchone()

    if row is None:
        return default

    return row[0]


def set_app_state(state_key, state_value):
    now = _utc_now_iso()

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO app_state (
                state_key, state_value, updated_at
            )
            VALUES (?, ?, ?)
            ON CONFLICT(state_key)
            DO UPDATE SET
                state_value = excluded.state_value,
                updated_at = excluded.updated_at
            """,
            (
                str(state_key),
                str(state_value or ""),
                now,
            ),
        )
        conn.commit()


def load_song_preferences(audio_hash):
    """
    Préférences UI persistantes propres à une chanson.

    Elles sont distinctes de l'analyse :
      - capo : affichage uniquement ;
      - settings : dernière configuration validée/affichée pour le morceau.

    Compatibilité descendante : si la table n'existe pas encore ou si aucun
    enregistrement n'existe, retourne None.
    """
    if not audio_hash:
        return None

    try:
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute(
                """
                SELECT capo, settings_json
                FROM song_preferences
                WHERE audio_hash = ?
                """,
                (str(audio_hash),),
            ).fetchone()
    except sqlite3.OperationalError:
        return None

    if row is None:
        return None

    try:
        settings = json.loads(row[1] or "{}")
    except Exception:
        settings = {}

    return {
        "capo": max(0, min(12, int(row[0] or 0))),
        "settings": settings if isinstance(settings, dict) else {},
    }


def save_song_preferences(audio_hash, capo, settings):
    """
    Sauvegarde sans déclencher aucune analyse.
    """
    if not audio_hash:
        return

    capo_value = max(0, min(12, int(capo or 0)))
    settings_json = json.dumps(
        _json_safe(settings or {}),
        ensure_ascii=False,
        sort_keys=True,
    )

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO song_preferences (
                audio_hash, capo, settings_json, updated_at
            )
            VALUES (?, ?, ?, ?)
            ON CONFLICT(audio_hash)
            DO UPDATE SET
                capo = excluded.capo,
                settings_json = excluded.settings_json,
                updated_at = excluded.updated_at
            """,
            (
                str(audio_hash),
                capo_value,
                settings_json,
                _utc_now_iso(),
            ),
        )
        conn.commit()


def current_song_settings_payload():
    """
    Snapshot complet des réglages avancés visibles.

    Important : cette fonction ne lance aucun calcul.
    """
    return {
        "signature_mode": signature_mode,
        "analyse_sr": int(analyse_sr_user),
        "hop_length": int(hop_length_user),
        "silence_rms_ratio": float(silence_rms_user),
        "silence_chroma_ratio": float(silence_chroma_user),
        "poids_fondamentale": float(poids_fondamentale_user),
        "fermata_enabled": bool(fermata_enabled_user),
        "fermata_gap_ratio": float(fermata_gap_user),
        "sections_enabled": bool(sections_enabled_user),
        "section_block_measures": int(section_block_measures_user),
        "section_similarity": float(section_similarity_user),
        "whisper_model": "small",
        "whisper_device": DEVICE,
    }


def prepare_song_preferences_for_open(audio_hash):
    """
    Prépare le prochain rerun AVANT la création des widgets.

    Priorité :
      1. préférences propres au morceau ;
      2. paramètres de la dernière analyse comme fallback historique.
    """
    preferences = load_song_preferences(audio_hash)
    latest_params = load_latest_analysis_parameters(audio_hash)

    if latest_params:
        st.session_state[
            "_pending_analysis_settings"
        ] = latest_params

    if preferences:
        st.session_state[
            "_pending_song_preferences"
        ] = preferences


def migrate_archived_audio_catalog():
    """
    Répare les cas où un audio est déjà archivé dans data/audio
    mais ne possède pas encore d'entrée songs.

    Les fichiers archivés utilisent le SHA-256 comme nom.
    Sans métadonnées historiques, le titre de secours reste le hash court.
    """
    with sqlite3.connect(DB_PATH) as conn:
        known_hashes = {
            row[0]
            for row in conn.execute(
                "SELECT audio_hash FROM songs"
            ).fetchall()
        }

    for path in AUDIO_DIR.glob("*.*"):
        stem = path.stem.lower()

        if len(stem) != 64:
            continue

        if stem in known_hashes:
            continue

        try:
            raw = path.read_bytes()
        except OSError:
            continue

        actual_hash = hashlib.sha256(raw).hexdigest()
        if actual_hash != stem:
            continue

        ensure_song(
            actual_hash,
            path.name,
        )


def persist_audio_source(audio_hash, original_filename, audio_bytes):
    """
    Archive localement le fichier audio importé afin qu'un morceau du
    catalogue puisse être rouvert sans demander un nouvel upload.
    """
    suffix = Path(original_filename).suffix.lower() or ".audio"
    target = AUDIO_DIR / f"{audio_hash}{suffix}"

    if not target.exists():
        target.write_bytes(audio_bytes)

    return target


def find_persisted_audio(audio_hash):
    """
    Résolution robuste de l'audio archivé.

    1. nom canonique <sha256>.<ext>
    2. nom exact sans extension
    3. dernier recours : scan des fichiers de data/audio et vérification SHA-256

    Le scan permet de réparer automatiquement un ancien archivage dont
    le nom de fichier ne respecte pas exactement le format courant.
    """
    audio_hash = str(audio_hash or "").strip().lower()

    if not audio_hash:
        return None

    candidates = sorted(AUDIO_DIR.glob(f"{audio_hash}.*"))
    if candidates:
        return candidates[0]

    exact_no_ext = AUDIO_DIR / audio_hash
    if exact_no_ext.exists() and exact_no_ext.is_file():
        return exact_no_ext

    for candidate in AUDIO_DIR.iterdir():
        if not candidate.is_file():
            continue

        try:
            digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
        except OSError:
            continue

        if digest.lower() == audio_hash:
            return candidate

    return None


def list_song_catalog(sort_by="title"):
    """
    Catalogue alphabétique au choix :
    - title  : titre puis auteur
    - artist : auteur/interprète puis titre
    """
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT audio_hash, original_filename, title, artist, editor,
                   strumming_primary, strumming_secondary,
                   created_at, updated_at
            FROM songs
            """
        ).fetchall()

    items = [
        {
            "audio_hash": row[0],
            "original_filename": row[1],
            "title": row[2],
            "artist": row[3],
            "editor": row[4] or "",
            "strumming_primary": row[5] or "",
            "strumming_secondary": row[6] or "",
            "created_at": row[7],
            "updated_at": row[8],
        }
        for row in rows
    ]

    def norm(value):
        return str(value or "").strip().casefold()

    if sort_by == "artist":
        items.sort(
            key=lambda s: (
                norm(s.get("artist")) or "\uffff",
                norm(s.get("title"))
                or norm(Path(s.get("original_filename", "")).stem),
            )
        )
    else:
        items.sort(
            key=lambda s: (
                norm(s.get("title"))
                or norm(Path(s.get("original_filename", "")).stem),
                norm(s.get("artist")),
            )
        )

    return items



def catalog_primary_text(song, sort_by="title"):
    title = str(song.get("title", "") or "").strip()
    artist = str(song.get("artist", "") or "").strip()
    filename = str(song.get("original_filename", "") or "").strip()

    title = title or Path(filename).stem or "Sans titre"

    if sort_by == "artist":
        return artist or "Auteur inconnu"

    return title


def catalog_secondary_text(song, sort_by="title"):
    title = str(song.get("title", "") or "").strip()
    artist = str(song.get("artist", "") or "").strip()
    filename = str(song.get("original_filename", "") or "").strip()

    title = title or Path(filename).stem or "Sans titre"

    if sort_by == "artist":
        return title

    return artist or "Auteur inconnu"


def catalog_letter_for_song(song, sort_by="title"):
    raw = catalog_primary_text(song, sort_by=sort_by).strip()

    if not raw:
        return "#"

    first = raw[0].upper()
    return first if "A" <= first <= "Z" else "#"


def filter_catalog(catalog, sort_by, letter="Tous", query=""):
    query_norm = str(query or "").strip().casefold()

    result = []

    for song in catalog:
        if letter not in ("Tous", ""):
            if catalog_letter_for_song(song, sort_by=sort_by) != letter:
                continue

        if query_norm:
            haystack = " ".join([
                str(song.get("title", "") or ""),
                str(song.get("artist", "") or ""),
                str(song.get("original_filename", "") or ""),
            ]).casefold()

            if query_norm not in haystack:
                continue

        result.append(song)

    return result


def catalog_display_name(song, sort_by="title"):
    title = str(song.get("title", "") or "").strip()
    artist = str(song.get("artist", "") or "").strip()
    filename = str(song.get("original_filename", "") or "").strip()

    title = title or Path(filename).stem or "Sans titre"

    if sort_by == "artist":
        return f"{artist or 'Auteur inconnu'} — {title}"

    if artist:
        return f"{title} — {artist}"

    return title


def ensure_song(audio_hash, original_filename):
    now = _utc_now_iso()
    default_title = Path(original_filename).stem

    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            """
            SELECT audio_hash, original_filename, title, artist, editor,
                   strumming_primary, strumming_secondary,
                   created_at, updated_at
            FROM songs
            WHERE audio_hash = ?
            """,
            (audio_hash,),
        ).fetchone()

        if row is None:
            conn.execute(
                """
                INSERT INTO songs (
                    audio_hash, original_filename, title, artist, editor,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, '', '', ?, ?)
                """,
                (
                    audio_hash,
                    original_filename,
                    default_title,
                    now,
                    now,
                ),
            )
            conn.commit()

            return {
                "audio_hash": audio_hash,
                "original_filename": original_filename,
                "title": default_title,
                "artist": "",
                "editor": "",
                "strumming_primary": "",
                "strumming_secondary": "",
                "created_at": now,
                "updated_at": now,
            }

        # Le nom physique peut changer alors que l'audio est identique.
        if row[1] != original_filename:
            conn.execute(
                """
                UPDATE songs
                SET original_filename = ?, updated_at = ?
                WHERE audio_hash = ?
                """,
                (original_filename, now, audio_hash),
            )
            conn.commit()

        return {
            "audio_hash": row[0],
            "original_filename": original_filename,
            "title": row[2],
            "artist": row[3],
            "editor": row[4] or "",
            "strumming_primary": row[5] or "",
            "strumming_secondary": row[6] or "",
            "created_at": row[7],
            "updated_at": now if row[1] != original_filename else row[8],
        }


def update_song_metadata(audio_hash, title, artist, editor, strumming_primary, strumming_secondary):
    now = _utc_now_iso()

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            UPDATE songs
            SET title = ?, artist = ?, editor = ?,
                strumming_primary = ?, strumming_secondary = ?,
                updated_at = ?
            WHERE audio_hash = ?
            """,
            (
                str(title or "").strip(),
                str(artist or "").strip(),
                str(editor or "").strip(),
                str(strumming_primary or "").strip(),
                str(strumming_secondary or "").strip(),
                now,
                audio_hash,
            ),
        )
        conn.commit()



def load_block_edits(audio_hash):
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT block_cluster, custom_label, measure_start, measure_end
            FROM block_edits
            WHERE audio_hash = ?
            """,
            (audio_hash,),
        ).fetchall()

    return {
        row[0]: {
            "custom_label": row[1] or "",
            "measure_start": row[2],
            "measure_end": row[3],
        }
        for row in rows
    }


def save_block_edit(
    audio_hash,
    block_cluster,
    custom_label,
    measure_start,
    measure_end,
):
    now = _utc_now_iso()

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO block_edits (
                audio_hash,
                block_cluster,
                custom_label,
                measure_start,
                measure_end,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(audio_hash, block_cluster)
            DO UPDATE SET
                custom_label = excluded.custom_label,
                measure_start = excluded.measure_start,
                measure_end = excluded.measure_end,
                updated_at = excluded.updated_at
            """,
            (
                audio_hash,
                str(block_cluster),
                str(custom_label or "").strip(),
                int(measure_start),
                int(measure_end),
                now,
            ),
        )
        conn.commit()


def libelle_bloc_affiche(section):
    """
    Affichage utilisateur :
    - nom personnalisé s'il existe ;
    - sinon fallback neutre "Bloc X".

    L'identifiant technique A/B/C reste interne.
    """
    custom = str(
        section.get("custom_label", "") or ""
    ).strip()

    if custom:
        return custom

    return f'Bloc {section["cluster"]}'


def appliquer_editions_blocs(
    sections_structurelles,
    block_edits,
    total_measures,
):
    result = []

    for section in sections_structurelles:
        copie = dict(section)
        cluster = str(section["cluster"])
        edit = block_edits.get(cluster, {})

        detected_start = int(section["measure_start"])
        detected_end = int(section["measure_end"])

        start = edit.get("measure_start")
        end = edit.get("measure_end")

        start = detected_start if start is None else int(start)
        end = detected_end if end is None else int(end)

        start = max(1, min(int(total_measures), start))
        end = max(1, min(int(total_measures), end))

        if start > end:
            start, end = end, start

        copie["detected_measure_start"] = detected_start
        copie["detected_measure_end"] = detected_end
        copie["measure_start"] = start
        copie["measure_end"] = end
        copie["custom_label"] = str(
            edit.get("custom_label", "") or ""
        ).strip()

        result.append(copie)

    return result



def _alpha_label_from_index(index):
    index = int(index)
    letters = ""
    while True:
        letters = chr(ord("A") + (index % 26)) + letters
        index = index // 26 - 1
        if index < 0:
            break
    return letters


def validated_partition_modifications(audio_hash):
    """
    Retourne uniquement les modifications déjà persistées/validées.

    Sont considérées comme modifications de partition :
    - corrections de grille (measure_edits)
    - corrections de paroles (lyric_block_edits)
    - structure manuelle : nom personnalisé, frontière déplacée
      ou bloc sans référence de détection (ex. séparation ajoutée)

    Ce statut ne représente PAS les changements encore présents
    seulement dans les widgets d'édition.
    """
    grid_edits = load_measure_edits(audio_hash)
    lyric_edits = load_lyric_block_edits(audio_hash)

    try:
        blocks = load_structure_blocks(audio_hash)
    except Exception:
        blocks = []

    edited_blocks = []
    for block in blocks:
        custom_label = str(
            block.get("custom_label", "") or ""
        ).strip()

        current_start = int(block.get("measure_start", 0) or 0)
        current_end = int(block.get("measure_end", 0) or 0)

        detected_start = block.get("detected_measure_start")
        detected_end = block.get("detected_measure_end")

        boundary_changed = False

        if detected_start is None or detected_end is None:
            # Cas typique d'un bloc ajouté manuellement.
            boundary_changed = True
        else:
            boundary_changed = (
                current_start != int(detected_start)
                or current_end != int(detected_end)
            )

        if custom_label or boundary_changed:
            edited_blocks.append(block)

    return {
        "grid": len(grid_edits),
        "lyrics": len(lyric_edits),
        "blocks": len(edited_blocks),
        "has_any": bool(
            grid_edits
            or lyric_edits
            or edited_blocks
        ),
    }


def load_structure_blocks(audio_hash):
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT
                block_id,
                order_index,
                cluster,
                custom_label,
                measure_start,
                measure_end,
                detected_measure_start,
                detected_measure_end
            FROM structure_blocks
            WHERE audio_hash = ?
            ORDER BY order_index ASC, block_id ASC
            """,
            (audio_hash,),
        ).fetchall()

    return [
        {
            "block_id": int(row[0]),
            "order_index": int(row[1]),
            "cluster": str(row[2]),
            "custom_label": str(row[3] or ""),
            "measure_start": int(row[4]),
            "measure_end": int(row[5]),
            "detected_measure_start": (
                None if row[6] is None else int(row[6])
            ),
            "detected_measure_end": (
                None if row[7] is None else int(row[7])
            ),
        }
        for row in rows
    ]


def _save_structure_blocks(audio_hash, blocks):
    """
    Sauvegarde atomiquement toute la partition manuelle.
    """
    now = _utc_now_iso()

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "DELETE FROM structure_blocks WHERE audio_hash = ?",
            (audio_hash,),
        )

        for order_index, block in enumerate(blocks):
            conn.execute(
                """
                INSERT INTO structure_blocks (
                    audio_hash,
                    block_id,
                    order_index,
                    cluster,
                    custom_label,
                    measure_start,
                    measure_end,
                    detected_measure_start,
                    detected_measure_end,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audio_hash,
                    int(block["block_id"]),
                    int(order_index),
                    str(block["cluster"]),
                    str(block.get("custom_label", "") or "").strip(),
                    int(block["measure_start"]),
                    int(block["measure_end"]),
                    block.get("detected_measure_start"),
                    block.get("detected_measure_end"),
                    now,
                ),
            )

        conn.commit()


def _normaliser_partition_blocs(blocks, total_measures):
    """
    Garantit une partition continue du morceau :
    - première mesure = 1
    - aucun trou
    - aucun chevauchement
    - dernière mesure = total_measures
    - au moins une mesure par bloc
    """
    if not blocks:
        return []

    total_measures = max(1, int(total_measures))
    blocks = [dict(b) for b in blocks]
    blocks.sort(key=lambda b: int(b.get("order_index", b["block_id"])))

    # Si trop de blocs pour le nombre de mesures, on tronque proprement.
    blocks = blocks[:total_measures]

    boundaries = []
    for i, block in enumerate(blocks[:-1]):
        desired_end = int(block.get("measure_end", i + 1))
        min_end = i + 1
        remaining = len(blocks) - i - 1
        max_end = total_measures - remaining
        desired_end = max(min_end, min(max_end, desired_end))
        boundaries.append(desired_end)

    previous_end = 0
    for i, block in enumerate(blocks):
        start = previous_end + 1
        if i < len(boundaries):
            end = boundaries[i]
        else:
            end = total_measures

        block["order_index"] = i
        block["measure_start"] = start
        block["measure_end"] = end
        previous_end = end

    return blocks


def ensure_structure_blocks(
    audio_hash,
    detected_sections,
    total_measures,
):
    """
    Crée une partition persistante lors de la première ouverture seulement.

    Les anciens noms stockés par cluster dans block_edits sont récupérés,
    mais les anciennes bornes indépendantes sont ignorées : elles pouvaient
    créer chevauchements et trous.
    """
    existing = load_structure_blocks(audio_hash)
    if existing:
        normalized = _normaliser_partition_blocs(
            existing,
            total_measures,
        )
        if normalized != existing:
            _save_structure_blocks(audio_hash, normalized)
        return normalized

    total_measures = max(1, int(total_measures))
    legacy_labels = load_block_edits(audio_hash)

    detected = sorted(
        [dict(s) for s in detected_sections],
        key=lambda s: (
            int(s["measure_start"]),
            int(s["measure_end"]),
        ),
    )

    blocks = []

    if not detected:
        blocks = [{
            "block_id": 1,
            "order_index": 0,
            "cluster": "A",
            "custom_label": "",
            "measure_start": 1,
            "measure_end": total_measures,
            "detected_measure_start": 1,
            "detected_measure_end": total_measures,
        }]
    else:
        # Les débuts détectés définissent les frontières initiales.
        starts = []
        source_for_start = {}

        for section in detected:
            start = max(1, min(total_measures, int(section["measure_start"])))
            if start not in source_for_start:
                starts.append(start)
                source_for_start[start] = section

        if 1 not in source_for_start:
            starts.insert(0, 1)
            source_for_start[1] = detected[0]

        starts = sorted(set(starts))

        for i, start in enumerate(starts):
            end = (
                starts[i + 1] - 1
                if i + 1 < len(starts)
                else total_measures
            )

            if end < start:
                continue

            section = source_for_start[start]
            cluster = str(section.get("cluster", _alpha_label_from_index(i)))
            legacy = legacy_labels.get(cluster, {})

            blocks.append({
                "block_id": i + 1,
                "order_index": i,
                "cluster": cluster,
                "custom_label": str(
                    legacy.get("custom_label", "") or ""
                ).strip(),
                "measure_start": start,
                "measure_end": end,
                "detected_measure_start": int(section.get(
                    "measure_start",
                    start,
                )),
                "detected_measure_end": int(section.get(
                    "measure_end",
                    end,
                )),
            })

    blocks = _normaliser_partition_blocs(
        blocks,
        total_measures,
    )
    _save_structure_blocks(audio_hash, blocks)
    return blocks


def _next_manual_cluster(blocks):
    used = {str(b.get("cluster", "")) for b in blocks}
    index = 0
    while True:
        candidate = _alpha_label_from_index(index)
        if candidate not in used:
            return candidate
        index += 1


def update_structure_block_sequential(
    audio_hash,
    block_id,
    custom_label,
    measure_start,
    measure_end,
    total_measures,
):
    """
    Édition d'un bloc avec recalage automatique des voisins.

    - changer la fin d'un bloc fixe automatiquement le début du suivant ;
    - changer le début fixe automatiquement la fin du précédent.
    """
    blocks = load_structure_blocks(audio_hash)
    if not blocks:
        return False, "Aucun bloc persistant."

    idx = next(
        (i for i, b in enumerate(blocks) if int(b["block_id"]) == int(block_id)),
        None,
    )
    if idx is None:
        return False, "Bloc introuvable."

    total_measures = int(total_measures)
    start = int(measure_start)
    end = int(measure_end)

    if idx == 0:
        start = 1
    if idx == len(blocks) - 1:
        end = total_measures

    # Préserver au moins une mesure pour les voisins.
    if idx > 0:
        min_start = int(blocks[idx - 1]["measure_start"]) + 1
        start = max(min_start, start)
    else:
        start = 1

    if idx < len(blocks) - 1:
        max_end = int(blocks[idx + 1]["measure_end"]) - 1
        end = min(max_end, end)
    else:
        end = total_measures

    if start > end:
        return False, "Bornes incompatibles : le bloc doit contenir au moins une mesure."

    blocks[idx]["custom_label"] = str(custom_label or "").strip()
    blocks[idx]["measure_start"] = start
    blocks[idx]["measure_end"] = end

    if idx > 0:
        blocks[idx - 1]["measure_end"] = start - 1

    if idx < len(blocks) - 1:
        blocks[idx + 1]["measure_start"] = end + 1

    blocks = _normaliser_partition_blocs(
        blocks,
        total_measures,
    )
    _save_structure_blocks(audio_hash, blocks)

    return True, "Bloc enregistré et voisins recalés."




def _structure_draft_key(audio_hash):
    return f"structure_draft_{str(audio_hash)[:16]}"


def _structure_editor_revision_key(audio_hash):
    return f"structure_editor_revision_{str(audio_hash)[:16]}"


def _structure_action_message_key(audio_hash):
    return f"structure_action_message_{str(audio_hash)[:16]}"


def _canonical_structure_rows(blocks):
    """Forme stable pour comparer brouillon et état persisté."""
    return [
        (
            str(b.get("custom_label", "") or "").strip(),
            int(b.get("measure_start", 0) or 0),
            int(b.get("measure_end", 0) or 0),
        )
        for b in blocks
    ]


def _structure_draft_is_dirty(audio_hash):
    draft = st.session_state.get(_structure_draft_key(audio_hash))
    if not draft:
        return False
    persisted = load_structure_blocks(audio_hash)
    return _canonical_structure_rows(draft) != _canonical_structure_rows(persisted)


def _structure_draft_from_persisted(audio_hash):
    blocks = [dict(b) for b in load_structure_blocks(audio_hash)]
    st.session_state[_structure_draft_key(audio_hash)] = blocks
    st.session_state.setdefault(_structure_editor_revision_key(audio_hash), 0)
    return blocks


def _get_structure_draft(audio_hash):
    draft = st.session_state.get(_structure_draft_key(audio_hash))
    if draft is None:
        return _structure_draft_from_persisted(audio_hash)
    return [dict(b) for b in draft]


def _set_structure_draft(audio_hash, blocks, message=None):
    st.session_state[_structure_draft_key(audio_hash)] = [dict(b) for b in blocks]
    rev_key = _structure_editor_revision_key(audio_hash)
    st.session_state[rev_key] = int(st.session_state.get(rev_key, 0)) + 1
    if message:
        st.session_state[_structure_action_message_key(audio_hash)] = str(message)


def _normalize_structure_draft(blocks, total_measures):
    """
    Normalise le brouillon uniquement en mémoire :
    - Début = Fin précédente + 1
    - dernier Fin = total
    - aucun trou / chevauchement
    - au moins 1 mesure par bloc
    """
    if not blocks:
        return []

    total_measures = max(1, int(total_measures))
    blocks = [dict(b) for b in blocks]
    blocks = blocks[:total_measures]

    previous_end = 0
    for i, block in enumerate(blocks):
        start = previous_end + 1
        remaining = len(blocks) - i - 1

        block["order_index"] = i
        block["measure_start"] = start

        if i == len(blocks) - 1:
            end = total_measures
        else:
            requested = int(block.get("measure_end", start) or start)
            min_end = start
            max_end = total_measures - remaining
            end = max(min_end, min(max_end, requested))

        block["measure_end"] = end
        previous_end = end

    return blocks


def _apply_structure_table_live_edit(blocks, edited_rows, total_measures):
    """
    Applique immédiatement Nom/Fin du tableau puis recalcule Début/Nb mesures.

    Si une frontière change, les blocs suivants sont décalés en conservant
    leurs durées antérieures autant que possible.
    """
    blocks = [dict(b) for b in blocks]
    if len(edited_rows) != len(blocks):
        return _normalize_structure_draft(blocks, total_measures)

    durations = [
        max(1, int(b["measure_end"]) - int(b["measure_start"]) + 1)
        for b in blocks
    ]

    changed_index = None
    requested_end = None

    for i, row in enumerate(edited_rows):
        blocks[i]["custom_label"] = str(row.get("Nom", "") or "").strip() or "Nouveau bloc"

        if i < len(blocks) - 1:
            try:
                candidate = int(row.get("Fin"))
            except Exception:
                candidate = int(blocks[i]["measure_end"])

            if candidate != int(blocks[i]["measure_end"]) and changed_index is None:
                changed_index = i
                requested_end = candidate

    if changed_index is None:
        return _normalize_structure_draft(blocks, total_measures)

    # Refaire toute la chaîne, puis préserver au mieux les durées après le pivot.
    previous_end = 0
    for i, block in enumerate(blocks):
        start = previous_end + 1
        block["measure_start"] = start
        block["order_index"] = i

        if i == len(blocks) - 1:
            end = int(total_measures)
        elif i == changed_index:
            remaining = len(blocks) - i - 1
            max_end = int(total_measures) - remaining
            end = max(start, min(max_end, int(requested_end)))
        elif i > changed_index:
            remaining = len(blocks) - i - 1
            max_end = int(total_measures) - remaining
            end = min(start + durations[i] - 1, max_end)
            end = max(start, end)
        else:
            end = int(block["measure_end"])
            remaining = len(blocks) - i - 1
            end = max(start, min(int(total_measures) - remaining, end))

        block["measure_end"] = end
        previous_end = end

    return _normalize_structure_draft(blocks, total_measures)


def _next_structure_draft_id(blocks):
    positive = [int(b.get("block_id", 0) or 0) for b in blocks]
    return (max(positive) if positive else 0) + 1


def _insert_structure_draft_after(blocks, row_index, total_measures):
    """
    Insère un bloc après la ligne choisie.
    Le nouveau bloc prend par défaut la dernière mesure du bloc courant.
    """
    blocks = _normalize_structure_draft(blocks, total_measures)
    if not blocks:
        return blocks, "Aucun bloc disponible."

    row_index = max(0, min(len(blocks) - 1, int(row_index)))
    target = blocks[row_index]

    if int(target["measure_end"]) <= int(target["measure_start"]):
        return blocks, "Ce bloc ne contient qu'une mesure : impossible de le scinder ici."

    old_end = int(target["measure_end"])
    target["measure_end"] = old_end - 1

    new_block = {
        "block_id": _next_structure_draft_id(blocks),
        "order_index": row_index + 1,
        "cluster": _next_manual_cluster(blocks),
        "custom_label": "Nouveau bloc",
        "measure_start": old_end,
        "measure_end": old_end,
        "detected_measure_start": None,
        "detected_measure_end": None,
    }
    blocks.insert(row_index + 1, new_block)
    blocks = _normalize_structure_draft(blocks, total_measures)
    return blocks, "Bloc inséré. Ajustez sa frontière si nécessaire."


def _append_structure_draft(blocks, total_measures):
    """Ajoute un bloc final en prenant 1 mesure au dernier bloc."""
    if not blocks:
        return blocks, "Aucun bloc disponible."
    return _insert_structure_draft_after(
        blocks,
        len(blocks) - 1,
        total_measures,
    )


def _delete_structure_draft_row(blocks, row_index, total_measures):
    """
    Supprime un bloc sans trou :
    - premier bloc : sa plage est absorbée par le suivant ;
    - sinon : sa plage est absorbée par le précédent.
    """
    blocks = _normalize_structure_draft(blocks, total_measures)

    if len(blocks) <= 1:
        return blocks, "Le dernier bloc restant ne peut pas être supprimé."

    row_index = max(0, min(len(blocks) - 1, int(row_index)))
    victim = blocks[row_index]

    if row_index == 0:
        blocks[1]["measure_start"] = int(victim["measure_start"])
    else:
        blocks[row_index - 1]["measure_end"] = int(victim["measure_end"])

    del blocks[row_index]
    blocks = _normalize_structure_draft(blocks, total_measures)
    return blocks, "Bloc supprimé ; la séquence a été refermée automatiquement."



def _delete_structure_draft_rows(blocks, row_indices, total_measures):
    """
    Supprime plusieurs blocs en une seule opération.

    Les cases restent cochables librement dans le tableau ; aucune suppression
    n'est appliquée avant clic sur "Supprimer la sélection".
    """
    blocks = _normalize_structure_draft(blocks, total_measures)

    selected = sorted({
        int(i)
        for i in row_indices
        if 0 <= int(i) < len(blocks)
    })

    if not selected:
        return blocks, "Aucun bloc sélectionné."

    if len(selected) >= len(blocks):
        return blocks, "Il faut conserver au moins un bloc."

    survivors = [
        dict(block)
        for i, block in enumerate(blocks)
        if i not in set(selected)
    ]

    survivors = _normalize_structure_draft(
        survivors,
        total_measures,
    )

    return (
        survivors,
        f"{len(selected)} bloc(s) supprimé(s) ; "
        "la séquence a été refermée automatiquement.",
    )


def _persist_structure_draft(audio_hash, draft, total_measures):
    """
    Persiste exactement le brouillon visible.
    Une nouvelle version est créée par l'appelant.
    """
    blocks = _normalize_structure_draft(draft, total_measures)

    if not blocks:
        return False, "Le morceau doit conserver au moins un bloc."

    _save_structure_blocks(audio_hash, blocks)
    st.session_state[_structure_draft_key(audio_hash)] = [dict(b) for b in blocks]
    return True, "Découpage validé."



def save_structure_blocks_from_table(
    audio_hash,
    blocks,
    edited_rows,
    total_measures,
):
    """
    Sauvegarde un découpage strictement séquentiel.

    Principe musicien :
      - on modifie le NOM et éventuellement la FIN d'un bloc ;
      - le bloc suivant commence automatiquement à FIN + 1 ;
      - si une frontière est déplacée, tous les blocs suivants sont
        décalés en conservant leur durée d'origine autant que possible ;
      - le dernier bloc absorbe le reliquat jusqu'à la dernière mesure.

    Exemple :
      Refrain 1 finit à 33
      -> Couplet 2 commence automatiquement à 34
      -> les blocs suivants sont décalés.
    """
    if not blocks:
        return False, "Aucun bloc à enregistrer."

    total_measures = int(total_measures)
    new_blocks = [dict(b) for b in blocks]

    if len(edited_rows) != len(new_blocks):
        return False, "Le nombre de lignes du tableau ne correspond plus aux blocs."

    # Durée actuelle de chaque bloc avant édition.
    durations = [
        max(
            1,
            int(block["measure_end"]) - int(block["measure_start"]) + 1,
        )
        for block in new_blocks
    ]

    # La première frontière modifiée devient le pivot.
    # Les blocs suivants sont ensuite décalés en gardant leur durée.
    changed_index = None
    requested_end = None

    for i, row in enumerate(edited_rows[:-1]):
        try:
            candidate_end = int(row.get("Fin"))
        except Exception:
            return False, f"Ligne {i + 1} : fin invalide."

        old_end = int(new_blocks[i]["measure_end"])

        if candidate_end != old_end and changed_index is None:
            changed_index = i
            requested_end = candidate_end

    # Mettre à jour les noms dans tous les cas.
    for i, row in enumerate(edited_rows):
        label = str(row.get("Nom", "") or "").strip()
        new_blocks[i]["custom_label"] = label or "Nouveau bloc"

    # Si aucune frontière n'a changé, on normalise simplement les débuts.
    if changed_index is None:
        previous_end = 0
        for i, block in enumerate(new_blocks):
            block["measure_start"] = previous_end + 1

            if i == len(new_blocks) - 1:
                block["measure_end"] = total_measures
            else:
                # Conserver la fin actuellement affichée si elle reste valide.
                end_value = int(block["measure_end"])
                min_end = int(block["measure_start"])
                remaining = len(new_blocks) - i - 1
                max_end = total_measures - remaining
                block["measure_end"] = max(
                    min_end,
                    min(max_end, end_value),
                )

            block["order_index"] = i
            previous_end = int(block["measure_end"])

        _save_structure_blocks(audio_hash, new_blocks)
        return True, "Découpage enregistré."

    # Valider la nouvelle fin du bloc pivot.
    pivot_start = int(new_blocks[changed_index]["measure_start"])
    remaining_blocks = len(new_blocks) - changed_index - 1
    max_pivot_end = total_measures - remaining_blocks

    if requested_end < pivot_start or requested_end > max_pivot_end:
        return (
            False,
            (
                f"Fin {requested_end} impossible pour "
                f"{new_blocks[changed_index].get('custom_label') or 'ce bloc'}. "
                f"Valeur attendue entre {pivot_start} et {max_pivot_end}."
            ),
        )

    # Tout ce qui précède reste inchangé, sauf normalisation des débuts.
    previous_end = 0

    for i in range(changed_index):
        block = new_blocks[i]
        block["measure_start"] = previous_end + 1
        block["order_index"] = i
        previous_end = int(block["measure_end"])

    # Bloc pivot.
    pivot = new_blocks[changed_index]
    pivot["measure_start"] = previous_end + 1
    pivot["measure_end"] = int(requested_end)
    pivot["order_index"] = changed_index
    previous_end = int(requested_end)

    # Décaler les suivants en conservant leur durée.
    for i in range(changed_index + 1, len(new_blocks)):
        block = new_blocks[i]
        block["measure_start"] = previous_end + 1
        block["order_index"] = i

        if i == len(new_blocks) - 1:
            block["measure_end"] = total_measures
        else:
            proposed_end = (
                int(block["measure_start"])
                + int(durations[i])
                - 1
            )

            remaining_after = len(new_blocks) - i - 1
            max_end = total_measures - remaining_after

            block["measure_end"] = min(
                proposed_end,
                max_end,
            )

        previous_end = int(block["measure_end"])

    # Dernière sécurité : partition continue jusqu'à la fin.
    if new_blocks:
        new_blocks[0]["measure_start"] = 1
        for i in range(1, len(new_blocks)):
            new_blocks[i]["measure_start"] = (
                int(new_blocks[i - 1]["measure_end"]) + 1
            )
        new_blocks[-1]["measure_end"] = total_measures

    _save_structure_blocks(audio_hash, new_blocks)

    next_txt = ""
    if changed_index + 1 < len(new_blocks):
        nxt = new_blocks[changed_index + 1]
        next_txt = (
            f" Le bloc suivant commence maintenant à "
            f"{nxt['measure_start']}."
        )

    return True, "Découpage décalé automatiquement." + next_txt


def reset_structure_blocks_from_analysis(audio_hash):
    """
    Supprime seulement la structure manuelle.
    Au prochain rerun, ensure_structure_blocks() la reconstruit
    depuis l'analyse persistée.
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            DELETE FROM structure_blocks
            WHERE audio_hash = ?
            """,
            (audio_hash,),
        )
        conn.commit()


def add_structure_separator(
    audio_hash,
    split_after_measure,
    total_measures,
):
    """
    Ajoute une frontière après une mesure en scindant le bloc
    qui contient cette mesure.
    """
    blocks = load_structure_blocks(audio_hash)

    if not blocks:
        return False, "Aucun bloc disponible."

    split_after = int(split_after_measure)

    if split_after < 1 or split_after >= int(total_measures):
        return False, "La séparation doit être située avant la dernière mesure."

    # Si cette frontière existe déjà, ne rien faire.
    for block in blocks[:-1]:
        if int(block["measure_end"]) == split_after:
            return False, "Une séparation existe déjà à cet endroit."

    target = next(
        (
            block
            for block in blocks
            if int(block["measure_start"]) <= split_after < int(block["measure_end"])
        ),
        None,
    )

    if target is None:
        return False, "Impossible de trouver le bloc à scinder."

    ok, message = split_structure_block(
        audio_hash=audio_hash,
        block_id=int(target["block_id"]),
        split_after_measure=split_after,
        total_measures=total_measures,
    )

    if not ok:
        return ok, message

    # Le nouveau bloc créé par la scission reçoit un nom neutre lisible.
    blocks_after = load_structure_blocks(audio_hash)
    new_block = next(
        (
            b
            for b in blocks_after
            if int(b["measure_start"]) == split_after + 1
        ),
        None,
    )

    if new_block is not None and not str(
        new_block.get("custom_label", "") or ""
    ).strip():
        new_block["custom_label"] = "Nouveau bloc"
        _save_structure_blocks(audio_hash, blocks_after)

    return True, f"Séparation ajoutée après la mesure {split_after}."


def split_structure_block(
    audio_hash,
    block_id,
    split_after_measure,
    total_measures,
):
    """
    Scinde un bloc après la mesure choisie.
    """
    blocks = load_structure_blocks(audio_hash)
    idx = next(
        (i for i, b in enumerate(blocks) if int(b["block_id"]) == int(block_id)),
        None,
    )
    if idx is None:
        return False, "Bloc introuvable."

    block = blocks[idx]
    split_after = int(split_after_measure)

    if not (
        int(block["measure_start"])
        <= split_after
        < int(block["measure_end"])
    ):
        return False, "La scission doit être située à l'intérieur du bloc."

    new_id = max(int(b["block_id"]) for b in blocks) + 1
    new_cluster = _next_manual_cluster(blocks)

    new_block = {
        "block_id": new_id,
        "order_index": idx + 1,
        "cluster": new_cluster,
        "custom_label": "",
        "measure_start": split_after + 1,
        "measure_end": int(block["measure_end"]),
        "detected_measure_start": int(block["detected_measure_start"])
            if block.get("detected_measure_start") is not None else None,
        "detected_measure_end": int(block["detected_measure_end"])
            if block.get("detected_measure_end") is not None else None,
    }

    blocks[idx]["measure_end"] = split_after
    blocks.insert(idx + 1, new_block)

    blocks = _normaliser_partition_blocs(blocks, total_measures)
    _save_structure_blocks(audio_hash, blocks)

    return True, f"Bloc scindé après la mesure {split_after}."


def merge_structure_block_with_next(
    audio_hash,
    block_id,
    total_measures,
):
    blocks = load_structure_blocks(audio_hash)
    idx = next(
        (i for i, b in enumerate(blocks) if int(b["block_id"]) == int(block_id)),
        None,
    )

    if idx is None:
        return False, "Bloc introuvable."

    if idx >= len(blocks) - 1:
        return False, "Le dernier bloc ne peut pas être fusionné avec un suivant."

    blocks[idx]["measure_end"] = int(
        blocks[idx + 1]["measure_end"]
    )
    del blocks[idx + 1]

    blocks = _normaliser_partition_blocs(blocks, total_measures)
    _save_structure_blocks(audio_hash, blocks)

    return True, "Fusion effectuée."


def materialiser_structure_blocks(
    blocks,
    mesures,
    detected_sections,
):
    """
    Convertit la partition persistante dans le format attendu par
    grille, parolier et diagnostic.
    """
    result = []

    def overlap(a0, a1, b0, b1):
        return max(0, min(a1, b1) - max(a0, b0) + 1)

    for block in blocks:
        start = int(block["measure_start"])
        end = int(block["measure_end"])

        groupe = [
            m for m in mesures
            if start <= int(m["numero"]) <= end
        ]

        if not groupe:
            continue

        best = None
        best_overlap = -1

        for detected in detected_sections:
            ov = overlap(
                start,
                end,
                int(detected["measure_start"]),
                int(detected["measure_end"]),
            )
            if ov > best_overlap:
                best_overlap = ov
                best = detected

        best = best or {}

        result.append({
            "block_id": int(block["block_id"]),
            "order_index": int(block["order_index"]),
            "cluster": str(block["cluster"]),
            "custom_label": str(block.get("custom_label", "") or ""),
            "measure_start": start,
            "measure_end": end,
            "detected_measure_start": block.get("detected_measure_start"),
            "detected_measure_end": block.get("detected_measure_end"),
            "time_start": float(groupe[0]["debut"]),
            "time_end": float(groupe[-1]["fin"]),
            "measure_patterns": [
                _normaliser_pattern_mesure(m.get("notation", ""))
                for m in groupe
            ],
            "confidence": float(best.get("confidence", 0.0)),
            "cluster_repeats": int(best.get("cluster_repeats", 1)),
            "lyric_repeat": float(best.get("lyric_repeat", 0.0)),
            "harmonic_repeat": float(best.get("harmonic_repeat", 0.0)),
            "type": libelle_bloc_affiche({
                "cluster": str(block["cluster"]),
                "custom_label": str(block.get("custom_label", "") or ""),
            }),
        })

    return result



_CHORD_TOKEN_RE = re.compile(
    r"""
    (?P<chord>
        [A-G]
        (?:\#|b)?
        (?:
            maj7
            |m7b5
            |dim7
            |dim
            |m7
            |7
            |m
        )?
    )
    |
    (?P<hold>-)
    |
    (?P<silence>\.)
    """,
    re.VERBOSE,
)


def accord_reel_depuis_forme_capo(accord_forme, capo):
    """
    Inverse de accord_forme_capo :
      forme jouée Am, capo 3 -> accord réel Cm
    """
    if not accord_forme or accord_forme in (".", "-", "?", "^"):
        return accord_forme

    capo = int(capo or 0)
    if capo == 0:
        return accord_forme

    root = accord_forme[0]
    suffix_start = 1

    if len(accord_forme) >= 2 and accord_forme[1] in ("#", "b"):
        root += accord_forme[1]
        suffix_start = 2

    if root not in _NOTE_TO_PC:
        return accord_forme

    pc_forme = _NOTE_TO_PC[root]
    pc_reel = (pc_forme + capo) % 12

    return _NOTES_SHARP[pc_reel] + accord_forme[suffix_start:]


def parser_notation_mesure(notation, expected_positions):
    """
    Parse la notation EZScore d'UNE mesure.

    Exemples :
      Am---           -> 4 positions
      Am-Em-          -> 4 positions
      D.C-            -> 4 positions
      Am-- | Em--     -> 6 positions

    '-' signifie : tenir l'accord de la position précédente.
    '.' signifie : silence harmonique.
    '^' final est le point d'orgue.
    """
    raw = str(notation or "").strip()
    fermata = raw.endswith("^")

    if fermata:
        raw = raw[:-1].rstrip()

    # Les barres des signatures composées sont purement visuelles.
    compact = raw.replace("|", "").replace(" ", "")

    if not compact:
        return False, [], fermata, "Mesure vide."

    tokens = []
    cursor = 0

    for match in _CHORD_TOKEN_RE.finditer(compact):
        if match.start() != cursor:
            bad = compact[cursor:match.start()]
            return (
                False,
                [],
                fermata,
                f"Syntaxe inconnue : {bad!r}.",
            )

        cursor = match.end()

        if match.group("chord"):
            tokens.append(match.group("chord"))
        elif match.group("silence"):
            tokens.append(".")
        else:
            # tenue
            if not tokens or tokens[-1] == ".":
                return (
                    False,
                    [],
                    fermata,
                    "'-' ne peut pas suivre un silence ou commencer une mesure.",
                )
            tokens.append(tokens[-1])

    if cursor != len(compact):
        return (
            False,
            [],
            fermata,
            f"Syntaxe inconnue : {compact[cursor:]!r}.",
        )

    if len(tokens) != int(expected_positions):
        return (
            False,
            tokens,
            fermata,
            (
                f"{len(tokens)} position(s) lue(s), "
                f"{int(expected_positions)} attendue(s)."
            ),
        )

    return True, tokens, fermata, ""


def load_measure_edits(audio_hash):
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT measure_no, notation_real
            FROM measure_edits
            WHERE audio_hash = ?
            ORDER BY measure_no
            """,
            (audio_hash,),
        ).fetchall()

    return {
        int(row[0]): str(row[1])
        for row in rows
    }


def save_measure_edit(
    audio_hash,
    measure_no,
    notation_real,
):
    now = _utc_now_iso()

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO measure_edits (
                audio_hash,
                measure_no,
                notation_real,
                updated_at
            )
            VALUES (?, ?, ?, ?)
            ON CONFLICT(audio_hash, measure_no)
            DO UPDATE SET
                notation_real = excluded.notation_real,
                updated_at = excluded.updated_at
            """,
            (
                audio_hash,
                int(measure_no),
                str(notation_real),
                now,
            ),
        )
        conn.commit()


def delete_measure_edit(audio_hash, measure_no):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            DELETE FROM measure_edits
            WHERE audio_hash = ? AND measure_no = ?
            """,
            (audio_hash, int(measure_no)),
        )
        conn.commit()


def appliquer_editions_mesures_aux_beats(
    audio_hash,
    beats,
    beats_par_mesure,
    signature,
):
    """
    Les corrections de grille sont appliquées aux beats internes,
    puis le reste de EZScore reconstruit ses mesures normalement.
    """
    edits = load_measure_edits(audio_hash)

    if not edits:
        return beats

    resultat = [dict(b) for b in beats]
    positions = int(beats_par_mesure)

    for measure_no, notation_real in edits.items():
        ok, symbols, _fermata, _error = parser_notation_mesure(
            notation_real,
            positions,
        )

        if not ok:
            continue

        start = (int(measure_no) - 1) * positions

        for offset, accord in enumerate(symbols):
            idx = start + offset
            if idx >= len(resultat):
                break
            resultat[idx]["accord"] = accord

    return resultat


def notation_affichee_depuis_reelle(
    notation_real,
    signature,
    capo,
    expected_positions,
):
    ok, symbols, fermata, _error = parser_notation_mesure(
        notation_real,
        expected_positions,
    )
    if not ok:
        return notation_real

    affiches = [
        accord_forme_capo(a, capo)
        for a in symbols
    ]

    return formatter_mesure_signature(
        affiches,
        signature,
        fermata=fermata,
    )


def notation_reelle_depuis_affichage(
    notation_affichee,
    signature,
    capo,
    expected_positions,
):
    ok, symbols, fermata, error = parser_notation_mesure(
        notation_affichee,
        expected_positions,
    )

    if not ok:
        return False, "", error

    reels = [
        accord_reel_depuis_forme_capo(a, capo)
        for a in symbols
    ]

    notation_real = formatter_mesure_signature(
        reels,
        signature,
        fermata=fermata,
    )

    return True, notation_real, ""


def _placer_texte_monospaced(
    items,
    origin_time,
    end_time,
    target_width,
    min_gap=1,
):
    """
    Place une suite d'éléments horodatés sur une ligne monospace.

    Les positions temporelles donnent la position idéale. En cas de
    collision textuelle, on décale uniquement le texte vers la droite.
    """
    if not items:
        return "", []

    origin_time = float(origin_time)
    end_time = max(float(end_time), origin_time + 1e-6)
    target_width = max(int(target_width), 1)

    placements = []
    previous_end = -1

    for item in items:
        txt = str(item["text"])
        t = float(item["time"])

        ratio = np.clip(
            (t - origin_time) / (end_time - origin_time),
            0.0,
            1.0,
        )
        ideal = int(round(ratio * max(target_width - 1, 0)))

        pos = max(ideal, previous_end + int(min_gap))
        placements.append((pos, txt, t))
        previous_end = pos + len(txt) - 1

    width = max(
        target_width,
        max(pos + len(txt) for pos, txt, _ in placements),
    )
    chars = [" "] * width

    for pos, txt, _ in placements:
        if pos + len(txt) > len(chars):
            chars.extend(
                [" "] * (pos + len(txt) - len(chars))
            )
        for j, ch in enumerate(txt):
            chars[pos + j] = ch

    return "".join(chars).rstrip(), placements


def _placer_accords_monospaced(
    events,
    origin_time,
    end_time,
    target_width,
    min_gap=2,
):
    """
    Place les notations de mesure sur la timeline.

    Contrairement aux paroles, les accords restent à leur position
    temporelle de référence ; seuls les accords qui se chevaucheraient
    sont repoussés juste assez pour rester lisibles.
    """
    if not events:
        return "", []

    origin_time = float(origin_time)
    end_time = max(float(end_time), origin_time + 1e-6)
    target_width = max(int(target_width), 1)

    placements = []
    previous_end = -1

    for event in events:
        txt = str(event["text"])
        t = float(event["time"])

        ratio = np.clip(
            (t - origin_time) / (end_time - origin_time),
            0.0,
            1.0,
        )
        ideal = int(round(ratio * max(target_width - 1, 0)))
        pos = max(ideal, previous_end + int(min_gap))

        placements.append((pos, txt, t))
        previous_end = pos + len(txt) - 1

    width = max(
        target_width,
        max(pos + len(txt) for pos, txt, _ in placements),
    )
    chars = [" "] * width

    for pos, txt, _ in placements:
        if pos + len(txt) > len(chars):
            chars.extend(
                [" "] * (pos + len(txt) - len(chars))
            )
        for j, ch in enumerate(txt):
            chars[pos + j] = ch

    return "".join(chars).rstrip(), placements


def _decaler_paroles_sous_accords(
    words,
    chord_placements,
    origin_time,
    end_time,
    target_width,
):
    """
    V38c — accords fixes, texte lisible.

    Les accords ne bougent jamais.

    Pour les paroles :
      - jamais de suppression d'espaces naturels ;
      - jamais de découpage artificiel d'un mot ;
      - on ajoute des espaces ENTRE les mots pour amener le mot
        correspondant sous l'accord.

    Si un accord tombe au milieu d'un mot et qu'on ne possède pas de
    timestamps syllabiques, le mot entier est ancré au plus près sans
    introduire de "_" dans son orthographe.
    """
    if not words:
        return ""

    anchors_by_word = {i: [] for i in range(len(words))}

    for chord_pos, _notation, chord_time in chord_placements:
        target_index = None

        for i, word in enumerate(words):
            w0 = float(word["start"])
            w1 = float(word["end"])

            if w0 <= chord_time <= w1:
                target_index = i
                break

            if chord_time < w0:
                target_index = i
                break

        if target_index is not None:
            anchors_by_word[target_index].append(
                int(chord_pos)
            )

    output = []
    cursor = 0

    for i, word in enumerate(words):
        txt = str(word["text"]).strip()
        if not txt:
            continue

        # Toujours au moins un espace naturel entre deux mots.
        if output:
            output.append(" ")
            cursor += 1

        desired_start = cursor
        anchors = anchors_by_word.get(i, [])

        if anchors:
            # Le mot peut être repoussé vers la droite, jamais vers la gauche.
            desired_start = max(
                desired_start,
                min(anchors),
            )

        if desired_start > cursor:
            output.append(" " * (desired_start - cursor))
            cursor = desired_start

        output.append(txt)
        cursor += len(txt)

    return "".join(output).rstrip()

def construire_lignes_paroles_intervalle(
    mesures,
    resultat,
    t0,
    t1,
    max_chars=74,
    corrected_block_text=None,
):
    """
    V38d : correction par bloc.
    Les accords restent fixes. Le texte corrigé est redistribué sur
    la timeline Whisper d'origine. Les retours à la ligne manuels sont
    respectés.
    """
    source_words = _source_words_for_interval(resultat, t0, t1)
    if not source_words:
        return []

    manual_mode = bool(str(corrected_block_text or "").strip())
    if manual_mode:
        mots = _redistribute_corrected_block_text(
            corrected_block_text, source_words
        )
    else:
        mots = [{**w, "manual_line_end": False} for w in source_words]

    groupes, courant, longueur = [], [], 0

    for i, word in enumerate(mots):
        txt = str(word["text"]).strip()
        if not txt:
            continue

        ajout = len(txt) + (1 if courant else 0)
        if not manual_mode and courant and longueur + ajout > int(max_chars):
            groupes.append(courant)
            courant, longueur = [], 0

        courant.append(word)
        longueur += ajout

        if manual_mode and word.get("manual_line_end"):
            groupes.append(courant)
            courant, longueur = [], 0
            continue

        if not manual_mode:
            punctuation = txt.endswith((".", "!", "?", ";", ":"))
            pause = 0.0
            if i + 1 < len(mots):
                pause = float(mots[i + 1]["start"]) - float(word["end"])
            if ((punctuation and longueur >= 24)
                    or (pause >= 0.75 and longueur >= 20)):
                groupes.append(courant)
                courant, longueur = [], 0

    if courant:
        groupes.append(courant)

    lignes = []

    for groupe in groupes:
        lt0 = float(groupe[0]["start"])
        lt1 = float(groupe[-1]["end"])

        mesures_ligne = [
            m for m in mesures
            if (
                float(m["fin"]) > lt0
                and float(m["debut"]) < lt1 + 1e-6
                and float(m["fin"]) > float(t0)
                and float(m["debut"]) < float(t1)
            )
        ]

        if mesures_ligne:
            origin_time = max(float(t0), float(mesures_ligne[0]["debut"]))
            line_end = min(
                float(t1),
                max(lt1, float(mesures_ligne[-1]["fin"])),
            )
        else:
            origin_time, line_end = lt0, lt1

        duration = max(line_end - origin_time, 1e-6)
        compact = " ".join(str(w["text"]) for w in groupe)
        notation_chars = sum(
            len(str(m.get("notation", ""))) + 2 for m in mesures_ligne
        )

        target_width = max(
            len(compact) + 6,
            notation_chars,
            int(round(duration * 7.0)),
            32,
        )
        target_width = min(target_width, 118)

        chord_events = [
            {
                "time": max(origin_time, float(m["debut"])),
                "text": str(m["notation"]),
            }
            for m in mesures_ligne
        ]

        accords, placements = _placer_accords_monospaced(
            events=chord_events,
            origin_time=origin_time,
            end_time=line_end,
            target_width=target_width,
            min_gap=2,
        )

        paroles = _decaler_paroles_sous_accords(
            words=groupe,
            chord_placements=placements,
            origin_time=origin_time,
            end_time=line_end,
            target_width=target_width,
        )

        lignes.append({
            "accords": accords,
            "paroles": paroles,
            "debut": lt0,
            "fin": lt1,
        })

    return lignes



def make_analysis_parameters(
    signature_mode,
    analyse_sr,
    hop_length,
    silence_rms_ratio,
    silence_chroma_ratio,
    poids_fondamentale,
    fermata_enabled,
    fermata_gap_ratio,
):
    return {
        "schema_version": PERSISTENCE_SCHEMA_VERSION,
        "engine_version": ANALYSIS_ENGINE_VERSION,
        "signature_mode": signature_mode,
        "analyse_sr": int(analyse_sr),
        "hop_length": int(hop_length),
        "silence_rms_ratio": float(silence_rms_ratio),
        "silence_chroma_ratio": float(silence_chroma_ratio),
        "poids_fondamentale": float(poids_fondamentale),
        "fermata_enabled": bool(fermata_enabled),
        "fermata_gap_ratio": float(fermata_gap_ratio),
        "whisper_model": "small",
        "whisper_device": DEVICE,
    }


def make_analysis_key(parameters):
    canonical = json.dumps(
        _json_safe(parameters),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()



def load_latest_analysis_parameters(audio_hash):
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            """
            SELECT parameters_json
            FROM analyses
            WHERE audio_hash = ?
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (audio_hash,),
        ).fetchone()

    if row is None:
        return None

    try:
        return json.loads(row[0])
    except Exception:
        return None


def hydrate_settings_from_parameters(parameters):
    """
    Prépare les valeurs des widgets pour le prochain rerun.
    """
    if not parameters:
        return

    mapping = {
        "setting_signature_mode": parameters.get("signature_mode", "Auto"),
        "setting_analyse_sr": int(parameters.get("analyse_sr", 22050)),
        "setting_hop_length": int(parameters.get("hop_length", 2048)),
        "setting_silence_rms": float(parameters.get("silence_rms_ratio", 0.22)),
        "setting_silence_chroma": float(parameters.get("silence_chroma_ratio", 0.18)),
        "setting_poids_fondamentale": float(parameters.get("poids_fondamentale", 0.22)),
        "setting_fermata_enabled": bool(parameters.get("fermata_enabled", True)),
        "setting_fermata_gap": float(parameters.get("fermata_gap_ratio", 1.85)),
    }

    for key, value in mapping.items():
        st.session_state[key] = value


def next_analysis_version_no(audio_hash):
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            """
            SELECT COALESCE(MAX(version_no), 0)
            FROM analysis_versions
            WHERE audio_hash = ?
            """,
            (audio_hash,),
        ).fetchone()

    return int(row[0] or 0) + 1


def _song_version_snapshot_payload(audio_hash):
    with sqlite3.connect(DB_PATH) as conn:
        song_row = conn.execute(
            """
            SELECT title, artist, editor,
                   strumming_primary, strumming_secondary
            FROM songs
            WHERE audio_hash = ?
            """,
            (audio_hash,),
        ).fetchone()

        pref_row = conn.execute(
            """
            SELECT capo
            FROM song_preferences
            WHERE audio_hash = ?
            """,
            (audio_hash,),
        ).fetchone()

    title = song_row[0] if song_row else ""
    artist = song_row[1] if song_row else ""
    editor = song_row[2] if song_row else ""
    strumming_primary = song_row[3] if song_row else ""
    strumming_secondary = song_row[4] if song_row else ""
    capo = int(pref_row[0] or 0) if pref_row else 0

    structure = load_structure_blocks(audio_hash)
    measure_edits = load_measure_edits(audio_hash)
    lyric_edits = load_lyric_block_edits(audio_hash)

    return {
        "title": str(title or ""),
        "artist": str(artist or ""),
        "editor": str(editor or ""),
        "strumming_primary": str(strumming_primary or ""),
        "strumming_secondary": str(strumming_secondary or ""),
        "capo": int(capo),
        "structure": structure,
        "measure_edits": measure_edits,
        "lyric_edits": lyric_edits,
    }



def _editorial_date_fr(value):
    raw = str(value or "").strip()
    if not raw:
        return ""
    try:
        return datetime.fromisoformat(
            raw.replace("Z", "+00:00")
        ).strftime("%d/%m/%Y")
    except Exception:
        return raw[:10]


def get_song_workflow(audio_hash):
    now = _utc_now_iso()
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            """
            SELECT state, current_version_no, working_note, updated_at
            FROM song_workflow
            WHERE audio_hash = ?
            """,
            (audio_hash,),
        ).fetchone()

        if row is None:
            conn.execute(
                """
                INSERT INTO song_workflow (
                    audio_hash, state, current_version_no,
                    working_note, updated_at
                )
                VALUES (?, 'working', NULL, '', ?)
                """,
                (audio_hash, now),
            )
            conn.commit()
            return {
                "state": "working",
                "current_version_no": None,
                "working_note": "",
                "updated_at": now,
            }

    return {
        "state": str(row[0] or "working"),
        "current_version_no": (
            int(row[1]) if row[1] is not None else None
        ),
        "working_note": str(row[2] or ""),
        "updated_at": str(row[3] or ""),
    }


def list_song_editorial_versions(audio_hash):
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT version_no, release_no, status,
                   source_analysis_version_no, note,
                   validated_at, published_at, updated_at
            FROM song_editorial_versions
            WHERE audio_hash = ?
            ORDER BY version_no DESC
            """,
            (audio_hash,),
        ).fetchall()

    return [
        {
            "version_no": int(row[0]),
            "release_no": int(row[1] or 0),
            "status": str(row[2] or "validated"),
            "source_analysis_version_no": (
                int(row[3]) if row[3] is not None else None
            ),
            "note": str(row[4] or ""),
            "validated_at": str(row[5] or ""),
            "published_at": str(row[6] or "") if row[6] else "",
            "updated_at": str(row[7] or ""),
        }
        for row in rows
    ]


def latest_song_editorial_version(audio_hash):
    versions = list_song_editorial_versions(audio_hash)
    return versions[0] if versions else None


def get_song_editorial_version(audio_hash, version_no):
    if version_no is None:
        return None
    for item in list_song_editorial_versions(audio_hash):
        if int(item["version_no"]) == int(version_no):
            return item
    return None


def save_working_note(audio_hash, note):
    now = _utc_now_iso()
    workflow = get_song_workflow(audio_hash)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            UPDATE song_workflow
            SET working_note = ?, updated_at = ?
            WHERE audio_hash = ?
            """,
            (str(note or ""), now, audio_hash),
        )
        conn.commit()


def update_song_editorial_note(audio_hash, version_no, note):
    now = _utc_now_iso()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            UPDATE song_editorial_versions
            SET note = ?, updated_at = ?
            WHERE audio_hash = ? AND version_no = ?
            """,
            (str(note or ""), now, audio_hash, int(version_no)),
        )
        conn.execute(
            """
            UPDATE song_workflow
            SET working_note = ?, updated_at = ?
            WHERE audio_hash = ?
            """,
            (str(note or ""), now, audio_hash),
        )
        conn.commit()


def validate_song_editorial_version(
    audio_hash,
    source_analysis_version_no,
    note,
):
    versions = list_song_editorial_versions(audio_hash)
    version_no = (
        max(v["version_no"] for v in versions) + 1
        if versions else 1
    )
    now = _utc_now_iso()

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO song_editorial_versions (
                audio_hash, version_no, release_no, status,
                source_analysis_version_no, note,
                validated_at, published_at, updated_at
            )
            VALUES (?, ?, 0, 'validated', ?, ?, ?, NULL, ?)
            """,
            (
                audio_hash,
                int(version_no),
                int(source_analysis_version_no),
                str(note or ""),
                now,
                now,
            ),
        )
        conn.execute(
            """
            INSERT INTO song_workflow (
                audio_hash, state, current_version_no,
                working_note, updated_at
            )
            VALUES (?, 'validated', ?, ?, ?)
            ON CONFLICT(audio_hash)
            DO UPDATE SET
                state = 'validated',
                current_version_no = excluded.current_version_no,
                working_note = excluded.working_note,
                updated_at = excluded.updated_at
            """,
            (
                audio_hash,
                int(version_no),
                str(note or ""),
                now,
            ),
        )
        conn.commit()

    return version_no


def publish_song_editorial_version(audio_hash, version_no, note):
    current = get_song_editorial_version(audio_hash, version_no)
    if current is None:
        return None

    release_no = max(1, int(current.get("release_no", 0) or 0))
    now = _utc_now_iso()

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            UPDATE song_editorial_versions
            SET release_no = ?,
                status = 'published',
                note = ?,
                published_at = ?,
                updated_at = ?
            WHERE audio_hash = ? AND version_no = ?
            """,
            (
                release_no,
                str(note or ""),
                now,
                now,
                audio_hash,
                int(version_no),
            ),
        )
        conn.execute(
            """
            UPDATE song_workflow
            SET state = 'published',
                current_version_no = ?,
                working_note = ?,
                updated_at = ?
            WHERE audio_hash = ?
            """,
            (
                int(version_no),
                str(note or ""),
                now,
                audio_hash,
            ),
        )
        conn.commit()

    return release_no


def resume_song_modifications(audio_hash):
    workflow = get_song_workflow(audio_hash)
    current = get_song_editorial_version(
        audio_hash,
        workflow.get("current_version_no"),
    )
    note = (
        current.get("note", "")
        if current is not None
        else workflow.get("working_note", "")
    )
    now = _utc_now_iso()

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            UPDATE song_workflow
            SET state = 'working',
                working_note = ?,
                updated_at = ?
            WHERE audio_hash = ?
            """,
            (str(note or ""), now, audio_hash),
        )
        conn.commit()


def editorial_status_label(workflow, version=None):
    state = str((workflow or {}).get("state", "working"))

    if state == "published" and version is not None:
        return (
            f"V{version['version_no']} · R{version['release_no']} · "
            f"Version publiée · "
            f"{_editorial_date_fr(version.get('published_at'))}"
        )

    if state == "validated" and version is not None:
        return (
            f"V{version['version_no']} · Version validée · "
            f"{_editorial_date_fr(version.get('validated_at'))}"
        )

    if version is not None:
        suffix = f" · à partir de V{version['version_no']}"
        if int(version.get("release_no", 0) or 0) > 0:
            suffix += f" · R{version['release_no']}"
        return "Modification en cours" + suffix

    return "Modification en cours"



def save_analysis_version(
    audio_hash,
    analysis_key,
    parameters,
    musique,
    resultat,
):
    """
    V39d : une version n'est plus seulement une analyse.
    C'est un snapshot complet de la partition courante.
    """
    version_no = next_analysis_version_no(audio_hash)
    now = _utc_now_iso()
    snapshot = _song_version_snapshot_payload(audio_hash)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO analysis_versions (
                audio_hash,
                analysis_key,
                version_no,
                parameters_json,
                music_json,
                whisper_json,
                title,
                artist,
                editor,
                capo,
                strumming_primary,
                strumming_secondary,
                structure_json,
                measure_edits_json,
                lyric_edits_json,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                audio_hash,
                analysis_key,
                version_no,
                json.dumps(
                    _json_safe(parameters),
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                json.dumps(_json_safe(musique), ensure_ascii=False),
                json.dumps(_json_safe(resultat), ensure_ascii=False),
                snapshot["title"],
                snapshot["artist"],
                snapshot["editor"],
                int(snapshot["capo"]),
                snapshot["strumming_primary"],
                snapshot["strumming_secondary"],
                json.dumps(
                    _json_safe(snapshot["structure"]),
                    ensure_ascii=False,
                ),
                json.dumps(
                    _json_safe(snapshot["measure_edits"]),
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                json.dumps(
                    _json_safe(snapshot["lyric_edits"]),
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                now,
            ),
        )
        conn.commit()

    return version_no


def list_analysis_versions(audio_hash):
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT
                version_no,
                analysis_key,
                parameters_json,
                created_at,
                title,
                artist,
                editor,
                capo,
                strumming_primary,
                strumming_secondary
            FROM analysis_versions
            WHERE audio_hash = ?
            ORDER BY version_no DESC
            """,
            (audio_hash,),
        ).fetchall()

    result = []

    for row in rows:
        try:
            params = json.loads(row[2])
        except Exception:
            params = {}

        result.append({
            "version_no": int(row[0]),
            "analysis_key": row[1],
            "parameters": params,
            "created_at": row[3],
            "title": str(row[4] or ""),
            "artist": str(row[5] or ""),
            "editor": str(row[6] or ""),
            "capo": int(row[7] or 0),
            "strumming_primary": str(row[8] or ""),
            "strumming_secondary": str(row[9] or ""),
        })

    return result


def load_analysis_version(audio_hash, version_no):
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            """
            SELECT
                version_no,
                analysis_key,
                parameters_json,
                music_json,
                whisper_json,
                created_at,
                title,
                artist,
                editor,
                capo,
                strumming_primary,
                strumming_secondary,
                structure_json,
                measure_edits_json,
                lyric_edits_json
            FROM analysis_versions
            WHERE audio_hash = ? AND version_no = ?
            """,
            (audio_hash, int(version_no)),
        ).fetchone()

    if row is None:
        return None

    try:
        return {
            "version_no": int(row[0]),
            "analysis_key": row[1],
            "parameters": json.loads(row[2]),
            "musique": json.loads(row[3]),
            "resultat": json.loads(row[4]),
            "created_at": row[5],
            "title": str(row[6] or ""),
            "artist": str(row[7] or ""),
            "editor": str(row[8] or ""),
            "capo": int(row[9] or 0),
            "strumming_primary": str(row[10] or ""),
            "strumming_secondary": str(row[11] or ""),
            "structure": json.loads(row[12] or "[]"),
            "measure_edits": json.loads(row[13] or "{}"),
            "lyric_edits": json.loads(row[14] or "{}"),
        }
    except Exception:
        return None


def delete_analysis_version(audio_hash, version_no):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            DELETE FROM analysis_versions
            WHERE audio_hash = ? AND version_no = ?
            """,
            (audio_hash, int(version_no)),
        )
        conn.commit()


def _restore_song_version_snapshot(audio_hash, version):
    """
    Restaure le snapshot de partition sélectionné comme copie de travail.
    Les versions restent immuables dans analysis_versions.
    """
    if not version:
        return

    now = _utc_now_iso()

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            UPDATE songs
            SET title = ?, artist = ?, editor = ?,
                strumming_primary = ?, strumming_secondary = ?,
                updated_at = ?
            WHERE audio_hash = ?
            """,
            (
                str(version.get("title", "") or ""),
                str(version.get("artist", "") or ""),
                str(version.get("editor", "") or ""),
                str(version.get("strumming_primary", "") or ""),
                str(version.get("strumming_secondary", "") or ""),
                now,
                audio_hash,
            ),
        )

        # Capo : ne touche jamais l'analyse.
        pref = conn.execute(
            """
            SELECT settings_json
            FROM song_preferences
            WHERE audio_hash = ?
            """,
            (audio_hash,),
        ).fetchone()

        settings_json = (
            pref[0]
            if pref and pref[0]
            else json.dumps(
                _json_safe(version.get("parameters", {}) or {}),
                ensure_ascii=False,
                sort_keys=True,
            )
        )

        conn.execute(
            """
            INSERT INTO song_preferences (
                audio_hash, capo, settings_json, updated_at
            )
            VALUES (?, ?, ?, ?)
            ON CONFLICT(audio_hash)
            DO UPDATE SET
                capo = excluded.capo,
                settings_json = excluded.settings_json,
                updated_at = excluded.updated_at
            """,
            (
                audio_hash,
                int(version.get("capo", 0) or 0),
                settings_json,
                now,
            ),
        )

        conn.execute(
            "DELETE FROM structure_blocks WHERE audio_hash = ?",
            (audio_hash,),
        )
        for order_index, block in enumerate(version.get("structure", []) or []):
            conn.execute(
                """
                INSERT INTO structure_blocks (
                    audio_hash,
                    block_id,
                    order_index,
                    cluster,
                    custom_label,
                    measure_start,
                    measure_end,
                    detected_measure_start,
                    detected_measure_end,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audio_hash,
                    int(block["block_id"]),
                    int(order_index),
                    str(block.get("cluster", "")),
                    str(block.get("custom_label", "") or ""),
                    int(block["measure_start"]),
                    int(block["measure_end"]),
                    block.get("detected_measure_start"),
                    block.get("detected_measure_end"),
                    now,
                ),
            )

        conn.execute(
            "DELETE FROM measure_edits WHERE audio_hash = ?",
            (audio_hash,),
        )
        for measure_no, notation in (
            version.get("measure_edits", {}) or {}
        ).items():
            conn.execute(
                """
                INSERT INTO measure_edits (
                    audio_hash, measure_no, notation_real, updated_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    audio_hash,
                    int(measure_no),
                    str(notation),
                    now,
                ),
            )

        conn.execute(
            "DELETE FROM lyric_block_edits WHERE audio_hash = ?",
            (audio_hash,),
        )
        for block_key, edit in (
            version.get("lyric_edits", {}) or {}
        ).items():
            conn.execute(
                """
                INSERT INTO lyric_block_edits (
                    audio_hash,
                    block_key,
                    original_text,
                    corrected_text,
                    time_start,
                    time_end,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audio_hash,
                    str(block_key),
                    str(edit.get("original_text", "") or ""),
                    str(edit.get("corrected_text", "") or ""),
                    float(edit.get("time_start", 0.0) or 0.0),
                    float(edit.get("time_end", 0.0) or 0.0),
                    now,
                ),
            )

        conn.commit()


def prepare_analysis_version_for_open(audio_hash, version_no):
    version = load_analysis_version(audio_hash, version_no)

    if version is None:
        return False

    _restore_song_version_snapshot(audio_hash, version)

    st.session_state["active_analysis_version_no"] = int(version_no)
    st.session_state["_pending_analysis_settings"] = dict(
        version.get("parameters", {}) or {}
    )
    st.session_state["_pending_song_preferences"] = {
        "capo": int(version.get("capo", 0) or 0),
        "settings": dict(version.get("parameters", {}) or {}),
    }

    return True



def load_beat_edits(audio_hash):
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT beat_index, chord_override, time_offset_ms
            FROM beat_edits
            WHERE audio_hash = ?
            """,
            (audio_hash,),
        ).fetchall()

    return {
        int(row[0]): {
            "chord_override": row[1],
            "time_offset_ms": float(row[2] or 0.0),
        }
        for row in rows
    }


def save_beat_edit(
    audio_hash,
    beat_index,
    chord_override,
    time_offset_ms,
):
    now = _utc_now_iso()

    chord = str(chord_override or "").strip()
    chord_value = chord if chord else None

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO beat_edits (
                audio_hash, beat_index, chord_override,
                time_offset_ms, updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(audio_hash, beat_index)
            DO UPDATE SET
                chord_override = excluded.chord_override,
                time_offset_ms = excluded.time_offset_ms,
                updated_at = excluded.updated_at
            """,
            (
                audio_hash,
                int(beat_index),
                chord_value,
                float(time_offset_ms),
                now,
            ),
        )
        conn.commit()


def clear_beat_edits_for_measure(
    audio_hash,
    beat_indices,
):
    if not beat_indices:
        return

    placeholders = ",".join("?" for _ in beat_indices)
    params = [audio_hash] + [int(i) for i in beat_indices]

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            f"""
            DELETE FROM beat_edits
            WHERE audio_hash = ?
              AND beat_index IN ({placeholders})
            """,
            params,
        )
        conn.commit()


def appliquer_editions_beats(beats_detectes, beat_edits):
    """
    Produit les beats effectifs utilisés partout dans l'UI.
    Les accords et temps détectés bruts restent intacts dans l'analyse.
    """
    beats = []

    for beat in beats_detectes:
        copie = dict(beat)
        idx = int(copie["index"])
        edit = beat_edits.get(idx, {})

        detected_t = float(copie["temps"])
        offset_ms = float(edit.get("time_offset_ms", 0.0))
        accord_override = edit.get("chord_override")

        copie["detected_temps"] = detected_t
        copie["edit_offset_ms"] = offset_ms
        copie["temps"] = detected_t + offset_ms / 1000.0

        if accord_override not in (None, ""):
            copie["accord"] = str(accord_override).strip()

        beats.append(copie)

    beats.sort(key=lambda b: int(b["index"]))

    # Garder un ordre temporel strict.
    for i in range(1, len(beats)):
        if beats[i]["temps"] <= beats[i - 1]["temps"] + 0.005:
            beats[i]["temps"] = beats[i - 1]["temps"] + 0.005

    for i in range(len(beats)):
        if i + 1 < len(beats):
            beats[i]["fin"] = beats[i + 1]["temps"]
            beats[i]["intervalle"] = beats[i + 1]["temps"] - beats[i]["temps"]
        else:
            interval = float(beats[i].get("intervalle", 0.5))
            beats[i]["fin"] = beats[i]["temps"] + max(interval, 0.05)

    return beats


def reconstruire_mesures_depuis_beats(
    beats,
    original_mesures,
    signature,
    beats_par_mesure,
):
    mesures = []

    for start in range(0, len(beats), int(beats_par_mesure)):
        groupe = beats[start:start + int(beats_par_mesure)]
        if not groupe:
            continue

        symboles = [b["accord"] for b in groupe]
        while len(symboles) < int(beats_par_mesure):
            symboles.append(".")

        numero = len(mesures) + 1
        original = (
            original_mesures[numero - 1]
            if numero - 1 < len(original_mesures)
            else {}
        )
        fermata = bool(original.get("fermata", False))

        mesures.append({
            "numero": numero,
            "debut": float(groupe[0]["temps"]),
            "fin": float(groupe[-1]["fin"]),
            "accords": symboles,
            "notation": formatter_mesure_signature(
                symboles,
                signature,
                fermata=fermata,
            ),
            "fermata": fermata,
        })

    return mesures


def render_beat_editor(
    context_key,
    audio_hash,
    beats,
    mesures,
    beats_par_mesure,
):
    """
    Éditeur partagé grille/parolier.
    Toute correction est persistée dans beat_edits et se répercute partout.
    """
    if not mesures:
        return

    with st.expander("✏️ Corriger accords / battements", expanded=False):
        st.caption(
            "Les corrections sont communes à la grille et au parolier. "
            "Accord et placement temporel sont persistés sans réanalyse."
        )

        measure_numbers = [int(m["numero"]) for m in mesures]
        selected_measure = st.selectbox(
            "Mesure à corriger",
            measure_numbers,
            key=f"beat_editor_measure_{context_key}_{audio_hash[:10]}",
        )

        start = (int(selected_measure) - 1) * int(beats_par_mesure)
        groupe = beats[start:start + int(beats_par_mesure)]

        with st.form(
            f"beat_editor_form_{context_key}_{audio_hash[:10]}_{selected_measure}",
            clear_on_submit=False,
        ):
            values = []

            for local_pos, beat in enumerate(groupe, start=1):
                c1, c2, c3 = st.columns([0.7, 1.4, 1.0])

                with c1:
                    st.markdown(f"**Beat {local_pos}**")

                with c2:
                    chord_value = st.text_input(
                        "Accord",
                        value=str(beat.get("accord", "")),
                        key=(
                            f"beat_chord_{context_key}_{audio_hash[:10]}_"
                            f"{beat['index']}"
                        ),
                    )

                with c3:
                    offset_value = st.number_input(
                        "Décalage (ms)",
                        min_value=-800.0,
                        max_value=800.0,
                        value=float(beat.get("edit_offset_ms", 0.0)),
                        step=10.0,
                        key=(
                            f"beat_offset_{context_key}_{audio_hash[:10]}_"
                            f"{beat['index']}"
                        ),
                    )

                values.append(
                    (
                        int(beat["index"]),
                        chord_value,
                        float(offset_value),
                    )
                )

            save_changes = st.form_submit_button(
                "💾 Enregistrer les corrections",
                type="primary",
            )

        if save_changes:
            for beat_index, chord_value, offset_value in values:
                save_beat_edit(
                    audio_hash,
                    beat_index,
                    chord_value,
                    offset_value,
                )

            st.success(
                "Corrections enregistrées. Grille et parolier seront synchronisés."
            )
            st.rerun()

        if st.button(
            "Réinitialiser cette mesure",
            key=f"reset_measure_{context_key}_{audio_hash[:10]}_{selected_measure}",
        ):
            clear_beat_edits_for_measure(
                audio_hash,
                [int(b["index"]) for b in groupe],
            )
            st.rerun()



def load_latest_persisted_analysis(audio_hash):
    """
    Charge la dernière analyse persistée d'un morceau, indépendamment
    de la clé correspondant aux widgets actuellement affichés.

    Utilisé à l'ouverture depuis le Répertoire afin qu'une chanson
    déjà analysée ne soit JAMAIS recalculée implicitement.
    """
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            """
            SELECT
                analysis_key,
                parameters_json,
                music_json,
                whisper_json,
                updated_at
            FROM analyses
            WHERE audio_hash = ?
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (audio_hash,),
        ).fetchone()

    if row is None:
        return None

    try:
        parameters = json.loads(row[1])
        musique = json.loads(row[2])
        resultat = json.loads(row[3])
    except Exception:
        return None

    return {
        "analysis_key": row[0],
        "parameters": parameters,
        "musique": musique,
        "resultat": resultat,
        "updated_at": row[4],
    }


def load_persisted_analysis(audio_hash, analysis_key):
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            """
            SELECT music_json, whisper_json
            FROM analyses
            WHERE audio_hash = ? AND analysis_key = ?
            """,
            (audio_hash, analysis_key),
        ).fetchone()

    if row is None:
        return None

    return {
        "musique": json.loads(row[0]),
        "resultat": json.loads(row[1]),
    }


def save_persisted_analysis(
    audio_hash,
    analysis_key,
    parameters,
    musique,
    resultat,
):
    now = _utc_now_iso()

    parameters_json = json.dumps(
        _json_safe(parameters),
        ensure_ascii=False,
        sort_keys=True,
    )
    music_json = json.dumps(
        _json_safe(musique),
        ensure_ascii=False,
    )
    whisper_json = json.dumps(
        _json_safe(resultat),
        ensure_ascii=False,
    )

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO analyses (
                audio_hash,
                analysis_key,
                engine_version,
                parameters_json,
                music_json,
                whisper_json,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(audio_hash, analysis_key)
            DO UPDATE SET
                engine_version = excluded.engine_version,
                parameters_json = excluded.parameters_json,
                music_json = excluded.music_json,
                whisper_json = excluded.whisper_json,
                updated_at = excluded.updated_at
            """,
            (
                audio_hash,
                analysis_key,
                ANALYSIS_ENGINE_VERSION,
                parameters_json,
                music_json,
                whisper_json,
                now,
                now,
            ),
        )
        conn.commit()


init_persistence()


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

    try:
        workdir, original_path, accompaniment_path = (
            separer_accompagnement_demucs(
                audio_bytes,
                extension
            )
        )

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

        # HPSS de no_vocals pour l'harmonie.
        y_harm, _ = librosa.effects.hpss(y_accomp)

        # Tempo + beats
        tempo, beat_frames = librosa.beat.beat_track(
            y=y_perc,
            sr=sr,
            hop_length=hop_length
        )
        tempo = float(np.asarray(tempo).squeeze())

        beat_times = librosa.frames_to_time(
            beat_frames,
            sr=sr,
            hop_length=hop_length
        )

        if len(beat_times) < 2:
            raise RuntimeError("Pas assez de beats détectés.")

        # ----------------------------------------------------
        # SIGNATURE RYTHMIQUE — TENTATIVE
        # ----------------------------------------------------

        signature_auto = detecter_signature_tentative(
            y_perc=y_perc,
            sr=sr,
            hop_length=hop_length,
            beat_frames=beat_frames,
        )

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

        # Chroma CQT conservé pour la qualité
        chroma = librosa.feature.chroma_cqt(
            y=y_harm,
            sr=sr,
            hop_length=hop_length
        )

        # Indice de fondamentale dans les deux octaves graves.
        # Il sert uniquement de confirmation de racine.
        chroma_fondamentale = librosa.feature.chroma_cqt(
            y=y_harm,
            sr=sr,
            hop_length=hop_length,
            fmin=librosa.note_to_hz("E1"),
            n_octaves=2,
        )

        templates, dictionnaire_accords = creer_templates_accords()

        tonalite = estimer_tonalite(chroma)
        prior_accords = creer_prior_accords(
            tonalite,
            dictionnaire_accords
        )

        # Normalisation colonne par colonne
        chroma_norm = librosa.util.normalize(chroma, axis=0)
        fondamentale_norm = librosa.util.normalize(
            chroma_fondamentale,
            axis=0
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
            for i in range(len(smoothed_scores)):
                total = 0.60 * beat_score_matrix[i]
                poids = 0.60

                if i > 0:
                    total += 0.20 * beat_score_matrix[i - 1]
                    poids += 0.20

                if i + 1 < len(smoothed_scores):
                    total += 0.20 * beat_score_matrix[i + 1]
                    poids += 0.20

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

        prior_vocabulaire = np.full(
            len(dictionnaire_accords),
            0.68,
            dtype=np.float64
        )

        prior_vocabulaire[top_vocabulaire] = 1.00

        # Les deux dominants obtiennent un bonus sensible.
        prior_vocabulaire[pair_a] = 1.32
        prior_vocabulaire[pair_b] = 1.32

        # Si le motif alterné est détecté, on renforce encore légèrement
        # le couple, mais jamais au point d'interdire un autre accord.
        if alternance_active:
            prior_vocabulaire[pair_a] = 1.48
            prior_vocabulaire[pair_b] = 1.48

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

        durees = (1, 2, 3, 4)
        bonus_duree = {
            1: -1.25,
            2:  0.58,
            3: -0.45,
            4:  0.18,
        }

        # Changement harmonique générique.
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

def extraire_mots(resultat):
    mots = []

    for segment in resultat.get("segments", []):
        for word in segment.get("words", []):
            texte = str(word.get("word", "")).strip()
            if not texte:
                continue

            debut = float(word.get("start", 0.0))
            fin = float(word.get("end", debut))

            mots.append({
                "text": texte,
                "start": debut,
                "end": fin,
            })

    return mots


def position_caractere_pour_temps(mots, temps):
    """
    Calcule une position visuelle approximative dans une ligne de paroles
    à partir des timestamps Whisper. Si le temps tombe dans un mot,
    on interpole à l'intérieur du mot.
    """
    if not mots:
        return 0

    position = 0

    for i, mot in enumerate(mots):
        largeur = len(mot["text"])
        espace = 1 if i > 0 else 0

        if temps < mot["start"]:
            return position

        if mot["start"] <= temps <= mot["end"]:
            duree = max(mot["end"] - mot["start"], 1e-6)
            ratio = np.clip((temps - mot["start"]) / duree, 0.0, 1.0)
            return position + espace + int(round(ratio * max(largeur - 1, 0)))

        position += espace + largeur

    return position


def construire_bloc_paroles(mesures, resultat, max_chars=78):
    """
    Produit des blocs :
      ligne accords : motifs complets de mesure (Am---, D.C-, ...)
      ligne paroles : texte Whisper

    Chaque motif de mesure est projeté au-dessus de la parole au moment
    du début de la mesure.
    """
    mots = extraire_mots(resultat)
    if not mots:
        return []

    blocs = []
    i = 0

    while i < len(mots):
        debut = i
        longueur = 0

        while i < len(mots):
            ajout = len(mots[i]["text"]) + (1 if i > debut else 0)

            if longueur + ajout > max_chars and i > debut:
                break

            longueur += ajout
            i += 1

        groupe = mots[debut:i]
        ligne_paroles = " ".join(m["text"] for m in groupe)

        t0 = groupe[0]["start"]
        t1 = groupe[-1]["end"]

        evenements = []
        for mesure in mesures:
            if t0 <= mesure["debut"] <= t1:
                evenements.append((mesure["debut"], mesure["notation"]))

        # Si une mesure commence juste avant le premier mot et couvre le début
        # de cette ligne, on l'affiche également.
        if not evenements:
            candidates = [
                m for m in mesures
                if m["debut"] <= t0 < m["fin"]
            ]
            if candidates:
                m = candidates[-1]
                evenements.append((t0, m["notation"]))

        largeur_accords = max(len(ligne_paroles), 1)
        ligne_accords = [" "] * largeur_accords

        derniere_fin = -2

        for temps, notation in evenements:
            pos = position_caractere_pour_temps(groupe, temps)
            pos = max(0, min(pos, largeur_accords - 1))

            # Ne jamais concaténer deux motifs de mesures.
            # Ex. "Am" + "Am-Em-" ne doit jamais devenir "AmAm-Em-".
            if pos <= derniere_fin + 1:
                pos = derniere_fin + 2

            besoin = pos + len(notation)
            if besoin > len(ligne_accords):
                ligne_accords.extend([" "] * (besoin - len(ligne_accords)))

            for j, ch in enumerate(notation):
                if pos + j < len(ligne_accords):
                    ligne_accords[pos + j] = ch

            derniere_fin = pos + len(notation) - 1

        blocs.append({
            "accords": "".join(ligne_accords).rstrip(),
            "paroles": ligne_paroles,
            "debut": float(t0),
            "fin": float(t1),
        })

    return blocs


# ============================================================
# DÉTECTION DE STRUCTURE — A/B/C puis Verse/Chorus/Bridge
# ============================================================

def _normaliser_texte_structure(texte):
    texte = (texte or "").lower()
    nettoye = []
    for ch in texte:
        if ch.isalnum() or ch.isspace():
            nettoye.append(ch)
        else:
            nettoye.append(" ")
    return " ".join("".join(nettoye).split())


def _lyrics_for_interval(resultat, t0, t1):
    mots = []
    for segment in resultat.get("segments", []):
        for word in segment.get("words", []):
            w0 = float(word.get("start", 0.0))
            w1 = float(word.get("end", w0))
            if w1 < t0 or w0 > t1:
                continue
            txt = str(word.get("word", "")).strip()
            if txt:
                mots.append(txt)
    return " ".join(mots)


def _chord_tokens_for_measures(mesures):
    tokens = []
    for mesure in mesures:
        for accord in mesure.get("accords", []):
            if accord in (".", "-", "", None):
                continue
            tokens.append(str(accord))
    return tokens


def _sequence_similarity(a, b):
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _token_jaccard(a, b):
    sa = set(_normaliser_texte_structure(a).split())
    sb = set(_normaliser_texte_structure(b).split())
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / max(len(sa | sb), 1)


def _normaliser_pattern_mesure(notation):
    """
    Normalise seulement les détails non structurels.

    Le rythme harmonique interne reste intact :
      Am---  != Am-Em-
      D.C-   != D-C-

    Le point d'orgue final est ignoré pour le regroupement structurel.
    """
    notation = str(notation or "").strip()
    if notation.endswith("^"):
        notation = notation[:-1]
    return notation


def _measure_progression_similarity(a_patterns, b_patterns):
    """
    Compare deux progressions MESURE PAR MESURE.

    Exemple :
      ["Am-Em-", "Am---", "Em---", "D-C-"]

    Le score ne repose pas sur un simple vocabulaire d'accords.
    Il conserve :
    - l'ordre des mesures ;
    - le rythme harmonique interne de chaque mesure ;
    - la position des changements dans la mesure.
    """
    if not a_patterns and not b_patterns:
        return 1.0
    if not a_patterns or not b_patterns:
        return 0.0

    n = min(len(a_patterns), len(b_patterns))
    if n == 0:
        return 0.0

    scores_mesures = []
    exacts = 0

    for i in range(n):
        a = _normaliser_pattern_mesure(a_patterns[i])
        b = _normaliser_pattern_mesure(b_patterns[i])

        if a == b:
            exacts += 1
            scores_mesures.append(1.0)
        else:
            # Similarité textuelle de la NOTATION DE MESURE complète.
            # Elle permet une petite tolérance sans aplatir le pattern.
            scores_mesures.append(
                SequenceMatcher(None, a, b).ratio()
            )

    mean_measure = float(np.mean(scores_mesures))
    exact_ratio = exacts / n

    # Pénalité si les longueurs de blocs diffèrent.
    length_ratio = min(len(a_patterns), len(b_patterns)) / max(
        len(a_patterns),
        len(b_patterns)
    )

    return (
        0.72 * mean_measure
        + 0.20 * exact_ratio
        + 0.08 * length_ratio
    )


def detecter_sections_structurelles(
    mesures,
    resultat,
    block_measures=4,
    similarity_threshold=0.66,
):
    """
    Détection prudente en deux passes :

    1. Regrouper des blocs similaires sous des labels A/B/C...
    2. Nommer Verse/Chorus/Bridge seulement si les indices sont suffisants.

    Aucun nom de section n'est imposé si la confiance est faible.
    """
    if not mesures:
        return []

    block_measures = max(2, int(block_measures))
    blocs = []

    for start in range(0, len(mesures), block_measures):
        groupe = mesures[start:start + block_measures]
        if not groupe:
            continue

        t0 = float(groupe[0]["debut"])
        t1 = float(groupe[-1]["fin"])
        lyrics = _lyrics_for_interval(resultat, t0, t1)

        # Signature structurelle = progression de MESURES complètes.
        measure_patterns = [
            _normaliser_pattern_mesure(m.get("notation", ""))
            for m in groupe
        ]

        blocs.append({
            "index": len(blocs),
            "measure_start": int(groupe[0]["numero"]),
            "measure_end": int(groupe[-1]["numero"]),
            "time_start": t0,
            "time_end": t1,
            "lyrics": lyrics,
            "lyrics_norm": _normaliser_texte_structure(lyrics),
            "measure_patterns": measure_patterns,
            "has_lyrics": bool(_normaliser_texte_structure(lyrics)),
        })

    if not blocs:
        return []

    # Pairwise similarities.
    n = len(blocs)
    pair_h = np.zeros((n, n), dtype=float)
    pair_l = np.zeros((n, n), dtype=float)
    pair_total = np.zeros((n, n), dtype=float)

    for i in range(n):
        pair_h[i, i] = 1.0
        pair_l[i, i] = 1.0
        pair_total[i, i] = 1.0

        for j in range(i + 1, n):
            h = _measure_progression_similarity(
                blocs[i]["measure_patterns"],
                blocs[j]["measure_patterns"]
            )

            l_seq = _sequence_similarity(
                blocs[i]["lyrics_norm"],
                blocs[j]["lyrics_norm"]
            )
            l_jac = _token_jaccard(
                blocs[i]["lyrics_norm"],
                blocs[j]["lyrics_norm"]
            )
            l = 0.65 * l_seq + 0.35 * l_jac

            # IMPORTANT :
            # le cluster A/B/C est défini par la progression de mesures.
            # Les paroles ne servent PAS à décider si deux blocs musicaux
            # sont le même pattern.
            total = h

            pair_h[i, j] = pair_h[j, i] = h
            pair_l[i, j] = pair_l[j, i] = l
            pair_total[i, j] = pair_total[j, i] = total

    # Greedy clustering into A/B/C...
    clusters = []
    labels = [None] * n

    for i in range(n):
        best_cluster = None
        best_score = -1.0

        for ci, members in enumerate(clusters):
            sim = float(np.mean([
                pair_total[i, m]
                for m in members
            ]))
            if sim > best_score:
                best_score = sim
                best_cluster = ci

        if (
            best_cluster is not None
            and best_score >= similarity_threshold
        ):
            clusters[best_cluster].append(i)
            labels[i] = best_cluster
        else:
            clusters.append([i])
            labels[i] = len(clusters) - 1

    # Cluster statistics.
    cluster_stats = {}

    for ci, members in enumerate(clusters):
        repeats = len(members)
        has_lyrics = [blocs[m]["has_lyrics"] for m in members]
        lyric_density = sum(has_lyrics) / max(repeats, 1)

        lyric_sims = []
        harm_sims = []

        for a_pos in range(len(members)):
            for b_pos in range(a_pos + 1, len(members)):
                a = members[a_pos]
                b = members[b_pos]
                lyric_sims.append(pair_l[a, b])
                harm_sims.append(pair_h[a, b])

        lyric_repeat = (
            float(np.mean(lyric_sims))
            if lyric_sims
            else 0.0
        )
        harmonic_repeat = (
            float(np.mean(harm_sims))
            if harm_sims
            else 0.0
        )

        cluster_stats[ci] = {
            "repeats": repeats,
            "lyric_density": lyric_density,
            "lyric_repeat": lyric_repeat,
            "harmonic_repeat": harmonic_repeat,
        }

    # Labels structurels neutres.
    # V25 : aucune interprétation Verse / Chorus / Bridge / Intro / Outro.
    # Le cluster A/B/C/... identifie uniquement une famille de progression
    # de mesures. Son nom sera éditable ultérieurement.
    def alpha_label(idx):
        idx = int(idx)
        letters = ""
        while True:
            letters = chr(ord("A") + (idx % 26)) + letters
            idx = idx // 26 - 1
            if idx < 0:
                break
        return letters

    sections = []

    for i, bloc in enumerate(blocs):
        ci = labels[i]
        stats = cluster_stats[ci]
        cluster_name = alpha_label(ci)

        confidence = (
            stats["harmonic_repeat"]
            if stats["repeats"] >= 2
            else 0.45
        )

        sections.append({
            **bloc,
            "cluster": cluster_name,
            "type": f"Bloc {cluster_name}",
            "confidence": float(confidence),
            "cluster_repeats": stats["repeats"],
            "lyric_repeat": stats["lyric_repeat"],
            "harmonic_repeat": stats["harmonic_repeat"],
            "measure_patterns": bloc["measure_patterns"],
        })

    # Fusionner uniquement des occurrences consécutives du même cluster.
    merged = []

    for section in sections:
        if (
            merged
            and merged[-1]["type"] == section["type"]
            and merged[-1]["cluster"] == section["cluster"]
            and merged[-1]["measure_end"] + 1 == section["measure_start"]
        ):
            prev = merged[-1]
            prev["measure_end"] = section["measure_end"]
            prev["time_end"] = section["time_end"]
            prev["lyrics"] = (
                (prev["lyrics"] + " " + section["lyrics"]).strip()
            )
            prev["confidence"] = float(
                (prev["confidence"] + section["confidence"]) / 2.0
            )
        else:
            merged.append(dict(section))

    return merged



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
# IMPRESSION V41
# ============================================================

def _print_song_header_html(
    title,
    artist,
    editor,
    version_label,
    source_status,
    tempo,
    signature,
    key_name,
    capo,
    measures_count,
    strumming_primary="",
    strumming_secondary="",
):
    """Entête compact dédié à la sortie papier."""
    title = html.escape(str(title or ""))
    artist = html.escape(str(artist or ""))
    editor = html.escape(str(editor or ""))
    version_label = html.escape(str(version_label or ""))
    source_status = html.escape(str(source_status or ""))
    signature = html.escape(str(signature or ""))
    key_name = html.escape(str(key_name or ""))
    strumming_primary = html.escape(str(strumming_primary or "").strip())
    strumming_secondary = html.escape(str(strumming_secondary or "").strip())

    title_line = title + (f" — {artist}" if artist else "")
    capo_label = "—" if int(capo or 0) == 0 else str(int(capo))

    strum = []
    if strumming_primary:
        strum.append(f"<strong>Strumming</strong> : {strumming_primary}")
    if strumming_secondary:
        strum.append(f"<strong>Alternatif</strong> : {strumming_secondary}")

    editor_html = (
        f'<div class="print-editor">Éditeur : {editor}</div>'
        if editor else ""
    )
    strum_html = (
        '<div class="print-strumming">🎸 ' + " · ".join(strum) + "</div>"
        if strum else ""
    )

    return (
        '<div class="print-song-header">'
        '<div class="print-title-row">'
        f'<div class="print-title">{title_line}</div>'
        f'<div class="print-version">· {version_label} · {source_status}</div>'
        '</div>'
        f'{editor_html}'
        '<div class="print-metrics">'
        f'<span><b>Tempo</b> {float(tempo):.1f} BPM</span>'
        f'<span><b>Signature</b> {signature}</span>'
        f'<span><b>Tonalité</b> {key_name}</span>'
        f'<span><b>Capo</b> {capo_label}</span>'
        f'<span><b>Mesures</b> {int(measures_count)}</span>'
        '</div>'
        f'{strum_html}'
        '</div>'
    )



# ============================================================
# PAGINATION PAPIER — BLOCS MUSICAUX
# ============================================================

_PRINT_PAGE_CONTENT_MM = 279.0
_PRINT_FIRST_PAGE_HEADER_MM = 32.0
_PRINT_GRID_ROW_MM = 7.0
_PRINT_GRID_BLOCK_MARGIN_MM = 3.0
_PRINT_LYRICS_TITLE_MM = 7.0
_PRINT_LYRICS_LINE_MM = 9.6
_PRINT_LYRICS_BLOCK_MARGIN_MM = 3.0


def _print_paginate_blocks(blocks, first_page_used_mm=0.0):
    """
    Insère un saut AVANT tout bloc qui ne tient plus sur la page courante.

    Un bloc qui tient sur une page est gardé entier. Un bloc exceptionnellement
    plus haut qu'une page commence sur une page neuve puis peut être coupé par
    le navigateur.
    """
    rendered = []
    used_mm = max(0.0, float(first_page_used_mm or 0.0))

    for block in blocks:
        block_html = str(block.get("html", ""))
        block_height_mm = max(0.0, float(block.get("height_mm", 0.0)))
        fits_one_page = block_height_mm <= _PRINT_PAGE_CONTENT_MM

        if used_mm > 0.0 and (
            (fits_one_page and used_mm + block_height_mm > _PRINT_PAGE_CONTENT_MM)
            or not fits_one_page
        ):
            rendered.append(
                '<div class="print-page-break" aria-hidden="true"></div>'
            )
            used_mm = 0.0

        rendered.append(block_html)
        used_mm = (
            used_mm + block_height_mm
            if fits_one_page
            else _PRINT_PAGE_CONTENT_MM
        )

    return "".join(rendered)


def _print_grid_block_height_mm(row_count):
    return (
        max(1, int(row_count)) * _PRINT_GRID_ROW_MM
        + _PRINT_GRID_BLOCK_MARGIN_MM
    )


def _print_lyrics_block_height_mm(line_count):
    return (
        _PRINT_LYRICS_TITLE_MM
        + max(1, int(line_count)) * _PRINT_LYRICS_LINE_MM
        + _PRINT_LYRICS_BLOCK_MARGIN_MM
    )

def _print_css_text(kind):
    """
    CSS autonome pour la fenêtre d'impression.
    Toujours A4 portrait.
    """
    return """
    @page {
        size: A4 portrait;
        margin: 9mm;
    }

    html, body {
        margin: 0;
        padding: 0;
        background: #fff;
        color: #000;
        font-family: Arial, Helvetica, sans-serif;
    }

    body {
        padding: 0;
    }

    .print-sheet {
        width: 100%;
        box-sizing: border-box;
    }

    .print-song-header {
        border-bottom: 1.5px solid #111;
        padding: 0 0 7px 0;
        margin: 0 0 10px 0;
    }

    .print-title-row {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        gap: 12px;
    }

    .print-title {
        font-size: 20pt;
        font-weight: 800;
        line-height: 1.05;
    }

    .print-version {
        font-size: 8.5pt;
        color: #444;
        white-space: nowrap;
    }

    .print-editor {
        font-size: 8.5pt;
        margin-top: 2px;
        color: #444;
    }

    .print-metrics {
        display: flex;
        flex-wrap: wrap;
        gap: 5px 18px;
        font-size: 9.5pt;
        margin-top: 6px;
    }

    .print-strumming {
        font-size: 10pt;
        margin-top: 5px;
    }

    .print-page-break {
        display: block;
        height: 0;
        margin: 0;
        padding: 0;
        break-before: page;
        page-break-before: always;
    }

    .print-grid-block {
        display: grid;
        grid-template-columns: 82px minmax(0, 1fr);
        gap: 6px;
        align-items: start;
        margin: 0 0 8px 0;
        break-inside: avoid;
        page-break-inside: avoid;
        break-before: auto;
        page-break-before: auto;
    }

    .print-grid-block.print-allow-split,
    .print-lyrics-block.print-allow-split {
        break-inside: auto;
        page-break-inside: auto;
    }

    .print-grid-block-name {
        font-size: 11.5pt;
        font-weight: 800;
        padding-top: 3px;
        break-after: avoid;
        page-break-after: avoid;
    }

    table.print-chord-grid {
        border-collapse: collapse;
        table-layout: fixed;
        width: 100%;
        font-family: Consolas, "Courier New", monospace;
    }

    table.print-chord-grid tr {
        break-inside: avoid;
        page-break-inside: avoid;
    }

    table.print-chord-grid td {
        border: 1px solid #111;
        width: 25%;
        height: 22px;
        padding: 2px 5px;
        vertical-align: middle;
        text-align: left;
        font-size: 13.5pt;
        font-weight: 800;
        line-height: 1;
        white-space: nowrap;
        overflow: hidden;
    }

    .print-lyrics-block {
        margin: 0 0 8px 0;
        break-inside: avoid;
        page-break-inside: avoid;
    }

    .print-lyrics-block-title {
        font-size: 12pt;
        font-weight: 800;
        margin: 7px 0 3px 0;
        break-after: avoid;
        page-break-after: avoid;
        orphans: 2;
        widows: 2;
    }

    .print-lyrics-line {
        font-family: Consolas, "Courier New", monospace;
        break-inside: avoid;
        page-break-inside: avoid;
        margin: 0 0 5px 0;
        orphans: 2;
        widows: 2;
    }

    .print-lyrics-first-line {
        break-before: avoid;
        page-break-before: avoid;
    }

    .print-lyrics-chords {
        white-space: pre;
        font-size: 12pt;
        line-height: 1;
        font-weight: 800;
    }

    .print-lyrics-text {
        white-space: pre;
        font-size: 13.5pt;
        line-height: 1.04;
        font-weight: 500;
    }

    @media print {
        html, body {
            margin: 0 !important;
            padding: 0 !important;
        }

        .print-sheet {
            width: 100% !important;
        }
    }
    """


def _make_print_document(kind, body_html, title="EZScore"):
    """
    Document HTML autonome.
    L'impression ne dépend plus du DOM Streamlit.
    """
    css = _print_css_text(kind)
    return SCORE.render(
        "EZScore.score",
        {
            "document": {
                "lang": "fr",
                "title": str(title),
                "css": css,
                "body_class": f"ezscore-print ezscore-print-{kind}",
                "body": str(body_html),
            }
        },
    )


def _print_icon(key_suffix, print_document):
    """
    Icône SVG compacte : ouvre une fenêtre HTML autonome puis le dialogue
    d'impression. Aucun masquage CSS de la page Streamlit.
    """
    import json

    payload = json.dumps(str(print_document), ensure_ascii=False)
    payload = payload.replace("</", "<\\/")

    st.iframe(
        f"""
        <!doctype html>
        <html>
        <head>
          <meta charset="utf-8">
          <style>
            html, body {{
              width:40px; height:40px; margin:0; padding:0;
              overflow:hidden; background:transparent;
            }}
            body {{ display:flex; align-items:center; justify-content:center; }}
            button {{
              width:34px; height:34px; margin:0; padding:0;
              display:inline-flex; align-items:center; justify-content:center;
              border:1px solid rgba(120,120,120,.45);
              border-radius:7px; background:transparent; color:#f2f2f2;
              cursor:pointer;
            }}
            button:hover {{ background:rgba(127,127,127,.10); }}
            svg {{
              width:18px; height:18px; fill:none; stroke:currentColor;
              stroke-width:1.8; stroke-linecap:round; stroke-linejoin:round;
            }}
          </style>
        </head>
        <body>
          <button
            id="print-{html.escape(str(key_suffix))}"
            title="Imprimer cette vue"
            aria-label="Imprimer cette vue"
            onclick='
              const doc = {payload};
              const w = window.open("", "_blank");
              if (!w) {{
                alert("Le navigateur a bloqué la fenêtre d’impression.");
                return;
              }}
              w.document.open();
              w.document.write(doc);
              w.document.close();
              const launchPrint = () => {{
                w.focus();
                setTimeout(() => w.print(), 120);
              }};
              if (w.document.readyState === "complete") {{
                launchPrint();
              }} else {{
                w.addEventListener("load", launchPrint, {{ once:true }});
                setTimeout(launchPrint, 350);
              }}
            '
          >
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M7 8V3h10v5"/>
              <rect x="6" y="14" width="12" height="7" rx="1"/>
              <path d="M6 17H4a2 2 0 0 1-2-2v-4a3 3 0 0 1 3-3h14a3 3 0 0 1 3 3v4a2 2 0 0 1-2 2h-2"/>
              <path d="M17 11h.01"/>
            </svg>
          </button>
        </body>
        </html>
        """,
        width=40,
        height=40,
    )



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

                c1, c2, c3, c4, c5 = st.columns(
                    [1.8, 1.25, 1.1, 0.8, 2.1]
                )

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
                                f'V{_catalog_editorial["version_no"]} · '
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
                                f'V{_catalog_editorial["version_no"]}'
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

                with c2:
                    st.caption(
                        catalog_secondary_text(
                            item,
                            sort_by=sort_key,
                        )
                    )

                with c4:
                    if version_numbers:
                        selected_version = st.selectbox(
                            "Version",
                            version_numbers,
                            index=0,
                            format_func=lambda n: f"V{n}",
                            key=f"catalog_version_{item['audio_hash']}",
                            label_visibility="collapsed",
                        )
                    else:
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
                                st.warning(
                                    f"Supprimer uniquement la version V{selected_version} ?"
                                )
                                if st.button(
                                    "Confirmer",
                                    key=f"delete_v_{item['audio_hash']}_{selected_version}",
                                ):
                                    delete_analysis_version(
                                        item["audio_hash"],
                                        selected_version,
                                    )
                                    if (
                                        item["audio_hash"]
                                        == st.session_state.get("active_song_hash")
                                        and int(selected_version)
                                        == int(
                                            st.session_state.get(
                                                "active_analysis_version_no",
                                                -1,
                                            )
                                        )
                                    ):
                                        st.session_state.pop(
                                            "active_analysis_version_no",
                                            None,
                                        )
                                    st.rerun()


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

        song = ensure_song(
            audio_hash,
            audio_filename,
        )

        persist_audio_source(
            audio_hash,
            audio_filename,
            audio_bytes,
        )

        st.session_state[
            "active_song_hash"
        ] = audio_hash

        set_app_state(
            "last_song_hash",
            audio_hash,
        )

        prepare_song_preferences_for_open(
            audio_hash
        )

        st.session_state[
            "_pending_main_menu"
        ] = "Chanson"

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

        if song_mode == "Édition":
            _workflow_edit = get_song_workflow(audio_hash)
            if _workflow_edit.get("state") != "working":
                resume_song_modifications(audio_hash)

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
        _stored_settings = current_song_settings_payload()

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
        # 4. Une nouvelle analyse n'est calculée que :
        #       - pour un morceau jamais analysé ;
        #       - ou après validation explicite de paramètres nouveaux.

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

        force_analysis = bool(appliquer_reglages)

        if appliquer_reglages:
            save_song_preferences(
                audio_hash=audio_hash,
                capo=capo_user,
                settings=current_song_settings_payload(),
            )

        if selected_version_data is not None and not force_analysis:
            musique = selected_version_data["musique"]
            resultat = selected_version_data["resultat"]
            analysis_key = selected_version_data["analysis_key"]
            analysis_parameters = selected_version_data["parameters"]
            analyse_source = "persisted_version"

        elif persisted is not None:
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
            spinner_message = (
                "Nouvelle analyse avec les paramètres validés..."
                if latest_persisted is not None
                else "Première analyse : accords, beats, mesures et paroles..."
            )

            with st.spinner(spinner_message):
                # CPU et GPU peuvent travailler simultanément.
                with ThreadPoolExecutor(max_workers=2) as executor:
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
                    future_whisper = executor.submit(
                        transcrire_cache,
                        audio_bytes,
                        extension,
                        DEVICE
                    )

                    musique = future_musique.result()
                    resultat = future_whisper.result()

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

            # Première analyse ou nouvelle variante explicitement validée :
            # les réglages visibles deviennent la configuration du morceau.
            save_song_preferences(
                audio_hash=audio_hash,
                capo=capo_user,
                settings=current_song_settings_payload(),
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
                f"Métadonnées enregistrées — nouvelle version V{version_no}. "
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
                    f"Analyse terminée et sauvegardée comme version "
                    f"{saved_version_no}."
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
            _workflow_version = latest_song_editorial_version(audio_hash)

        with st.expander(
            "📝 Version de la chanson · "
            + editorial_status_label(_workflow, _workflow_version),
            expanded=False,
        ):
            _note_initial = (
                _workflow_version.get("note", "")
                if (
                    _workflow.get("state") in ("validated", "published")
                    and _workflow_version is not None
                )
                else _workflow.get("working_note", "")
            )

            _editor_note = st.text_area(
                "Note de l’éditeur",
                value=str(_note_initial or ""),
                placeholder=(
                    "Ex. Refrain corrigé, structure validée pour la scène, "
                    "version préparée pour le set acoustique…"
                ),
                key=(
                    f"editor_note_{audio_hash[:12]}_"
                    f"{_workflow.get('state')}_"
                    f"{_workflow.get('current_version_no')}"
                ),
                help=(
                    "Note pour et par l’éditeur. "
                    "Elle reste modifiable."
                ),
            )

            note_col, action_col, resume_col = st.columns(
                [1.0, 1.2, 1.2]
            )

            with note_col:
                if st.button(
                    "💾 Enregistrer la note",
                    key=f"save_editor_note_{audio_hash[:12]}",
                ):
                    if (
                        _workflow.get("state") in ("validated", "published")
                        and _workflow_version is not None
                    ):
                        update_song_editorial_note(
                            audio_hash,
                            _workflow_version["version_no"],
                            _editor_note,
                        )
                    else:
                        save_working_note(
                            audio_hash,
                            _editor_note,
                        )
                    st.success("Note de l’éditeur enregistrée.")
                    st.rerun()

            with action_col:
                if _workflow.get("state") == "working":
                    if st.button(
                        "✅ Valider cette version",
                        type="primary",
                        key=f"validate_song_version_{audio_hash[:12]}",
                    ):
                        _technical_version_no = save_analysis_version(
                            audio_hash=audio_hash,
                            analysis_key=analysis_key,
                            parameters=analysis_parameters,
                            musique=musique,
                            resultat=resultat,
                        )
                        _editorial_version_no = validate_song_editorial_version(
                            audio_hash=audio_hash,
                            source_analysis_version_no=_technical_version_no,
                            note=_editor_note,
                        )
                        st.session_state[
                            "active_analysis_version_no"
                        ] = _technical_version_no
                        st.success(
                            f"Version V{_editorial_version_no} validée."
                        )
                        st.rerun()

                elif (
                    _workflow.get("state") == "validated"
                    and _workflow_version is not None
                ):
                    if st.button(
                        "🌍 Publier cette version",
                        type="primary",
                        key=f"publish_song_version_{audio_hash[:12]}",
                    ):
                        _release_no = publish_song_editorial_version(
                            audio_hash,
                            _workflow_version["version_no"],
                            _editor_note,
                        )
                        st.success(
                            f"V{_workflow_version['version_no']} · "
                            f"R{_release_no} publiée."
                        )
                        st.rerun()
                else:
                    st.caption("Cette version est publiée.")

            with resume_col:
                if _workflow.get("state") in ("validated", "published"):
                    if st.button(
                        "✏ Reprendre les modifications",
                        key=f"resume_song_{audio_hash[:12]}",
                    ):
                        resume_song_modifications(audio_hash)
                        st.session_state[_mode_key] = "Édition"
                        st.rerun()

            _editorial_history = list_song_editorial_versions(
                audio_hash
            )
            if _editorial_history:
                st.markdown("**Historique**")
                for _entry in _editorial_history:
                    if _entry["status"] == "published":
                        _entry_label = (
                            f"V{_entry['version_no']} · "
                            f"R{_entry['release_no']} · Publiée · "
                            f"{_editorial_date_fr(_entry['published_at'])}"
                        )
                    else:
                        _entry_label = (
                            f"V{_entry['version_no']} · Validée · "
                            f"{_editorial_date_fr(_entry['validated_at'])}"
                        )

                    if _entry.get("note"):
                        st.caption(
                            f"{_entry_label} — {_entry['note']}"
                        )
                    else:
                        st.caption(_entry_label)

        versions = list_analysis_versions(audio_hash)

        if song_mode == "Édition":
            with st.expander("🗂️ Versions d'analyse", expanded=False):
                st.caption(
                    "Gestion / restauration des versions. "
                    "Ce panneau est volontairement masqué en mode Vue."
                )

                if not versions:
                    st.caption(
                        "Aucune version explicite enregistrée pour ce morceau."
                    )
                else:
                    rows_versions = []
                    for version in versions:
                        p = version["parameters"]
                        rows_versions.append({
                            "Version": version["version_no"],
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
                    "💾 Sauver l'analyse courante comme nouvelle version",
                    key=f"save_analysis_version_{audio_hash[:12]}",
                ):
                    version_no = save_analysis_version(
                        audio_hash=audio_hash,
                        analysis_key=analysis_key,
                        parameters=analysis_parameters,
                        musique=musique,
                        resultat=resultat,
                    )
                    st.success(f"Version {version_no} enregistrée.")
                    st.rerun()

        # ----------------------------------------------------
        # MODE JOUER — présentation volontairement différée
        # ----------------------------------------------------
        if song_mode == "Jouer":
            if song_view == "Grille":
                st.info(
                    "▶ Player Grille synchronisé : emplacement réservé. "
                    "Présentation à définir."
                )
            elif song_view == "Paroles + accords":
                st.info(
                    "▶ Player Paroles + accords synchronisé : emplacement réservé. "
                    "Présentation à définir."
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

                    _preview_lines = construire_lignes_paroles_intervalle(
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

                    lines_print = construire_lignes_paroles_intervalle(
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

            df = creer_dataframe_timeline(beats)

            if df.empty:
                st.info("Aucune donnée harmonique disponible pour cette analyse.")
            else:
                origine = pd.Timestamp("1970-01-01")
                df["Début_dt"] = origine + pd.to_timedelta(
                    df["Début"],
                    unit="s",
                )
                df["Fin_dt"] = origine + pd.to_timedelta(
                    df["Fin"],
                    unit="s",
                )
                df["Morceau"] = "Audio"

                fig = px.timeline(
                    df,
                    x_start="Début_dt",
                    x_end="Fin_dt",
                    y="Morceau",
                    color="Accord",
                    text="Accord",
                    hover_data={
                        "Début": ":.2f",
                        "Fin": ":.2f",
                    },
                )

                for section in sections_structurelles:
                    section_start = origine + pd.to_timedelta(
                        float(section["time_start"]),
                        unit="s",
                    )
                    section_end = origine + pd.to_timedelta(
                        float(section["time_end"]),
                        unit="s",
                    )
                    fig.add_vrect(
                        x0=section_start,
                        x1=section_end,
                        opacity=0.08,
                        line_width=1,
                        annotation_text=libelle_bloc_affiche(section),
                        annotation_position="top left",
                    )

                fig.update_layout(
                    xaxis=dict(
                        title="Temps",
                        tickformat="%M:%S",
                        fixedrange=False,
                        rangeslider=dict(visible=True),
                    ),
                    yaxis=dict(
                        title="",
                        showticklabels=False,
                        fixedrange=True,
                    ),
                    dragmode="zoom",
                    height=430,
                    uirevision=(
                        f"analyse-{audio_hash[:12]}-"
                        f"{_version_no if _version_no is not None else 'current'}"
                    ),
                    margin=dict(l=10, r=10, t=35, b=25),
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
                    "Zoom : molette sur le graphe, sélection rectangulaire, "
                    "barre inférieure ou outils Plotly. Double-clic pour revenir "
                    "à l'ensemble du morceau."
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
                st.write("Source accords : **Demucs no_vocals + moteur V9**")

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
