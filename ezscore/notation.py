"""Chord-grid notation and capo display helpers."""

from __future__ import annotations

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
