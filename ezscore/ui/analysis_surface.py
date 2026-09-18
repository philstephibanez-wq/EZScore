"""Point d'entrée canonique de la surface Analyse EZScore.

Ce module ne calcule rien et ne modifie aucun artefact.
Il délègue vers l'analyseur Rebirth existant au moment de l'appel afin de
conserver tous les wrappers déjà installés.
"""

from __future__ import annotations


def render_analysis_surface(audio_hash: str) -> None:
    from ezscore.ui import stem_lab_analysis

    stem_lab_analysis.render_stem_lab_fresh_analysis(audio_hash)
