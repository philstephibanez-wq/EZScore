"""Lyrics alignment, phonetics and structural section detection."""

from __future__ import annotations

import re
from difflib import SequenceMatcher

import numpy as np
from ezscore.analysis.timelines import build_lyrics_timeline
from ezscore.analysis.structure import detect_visual_blocks

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


def _fr_phonetic_word(word):
    """
    Approximation phonétique française lisible (type IPA simplifié).

    Cette première couche R12 est dérivée du texte Whisper et sert à
    préparer l'alignement phonétique. Ce n'est pas encore un détecteur
    acoustique de phonèmes.
    """
    w = str(word or "").lower().strip()
    w = re.sub(r"[^a-zàâäéèêëîïôöùûüÿçœæ'-]", "", w)

    if not w:
        return ""

    replacements = [
        ("eaux", "o"),
        ("eau", "o"),
        ("aux", "o"),
        ("au", "o"),
        ("oin", "wɛ̃"),
        ("ain", "ɛ̃"),
        ("ein", "ɛ̃"),
        ("aim", "ɛ̃"),
        ("in", "ɛ̃"),
        ("im", "ɛ̃"),
        ("un", "œ̃"),
        ("um", "œ̃"),
        ("an", "ɑ̃"),
        ("am", "ɑ̃"),
        ("en", "ɑ̃"),
        ("em", "ɑ̃"),
        ("on", "ɔ̃"),
        ("om", "ɔ̃"),
        ("ou", "u"),
        ("oi", "wa"),
        ("gn", "ɲ"),
        ("ill", "j"),
        ("ph", "f"),
        ("ch", "ʃ"),
        ("th", "t"),
        ("qu", "k"),
        ("gu", "g"),
    ]

    for src, dst in replacements:
        w = w.replace(src, dst)

    # Quelques valeurs graphème -> son très usuelles.
    w = re.sub(r"c(?=[eéièêëiy])", "s", w)
    w = w.replace("c", "k")
    w = re.sub(r"g(?=[eéièêëiy])", "ʒ", w)
    w = w.replace("j", "ʒ")
    w = w.replace("r", "ʁ")
    w = w.replace("u", "y")
    w = w.replace("é", "e")
    w = w.replace("er", "e")
    w = w.replace("ez", "e")
    w = w.replace("è", "ɛ")
    w = w.replace("ê", "ɛ")
    w = w.replace("ai", "ɛ")
    w = w.replace("ais", "ɛ")
    w = w.replace("ait", "ɛ")
    w = w.replace("ç", "s")
    w = w.replace("y", "j")
    w = w.replace("œ", "œ")
    w = w.replace("â", "ɑ")
    w = w.replace("ô", "o")

    # Consonnes finales souvent muettes : règle volontairement prudente.
    w = re.sub(r"[tdspx]$", "", w)
    w = re.sub(r"e$", "", w)

    return w


def construire_timeline_phonetique(resultat):
    """
    Timeline phonétique estimée à partir des mots horodatés Whisper.

    Les liaisons françaises probables sont signalées par `‿z` ou `‿t`.
    L'objectif est de rendre visible le flux lié du français avant
    l'introduction future d'un véritable modèle acoustique phonème/CTC.
    """
    words = extraire_mots(resultat)
    language = str(resultat.get("language", "") or "").lower()

    if not language.startswith("fr"):
        return []

    vowels = "aàâäeéèêëiîïoôöuùûüœæy"
    timeline = []

    for i, word in enumerate(words):
        text_word = str(word.get("text", "") or "").strip()
        phonetic = _fr_phonetic_word(text_word)
        liaison = ""

        if i + 1 < len(words):
            next_word = str(words[i + 1].get("text", "") or "").strip().lower()
            current = re.sub(r"[^a-zàâäéèêëîïôöùûüÿçœæ]", "", text_word.lower())

            if next_word and next_word[0] in vowels:
                if current.endswith(("s", "x", "z")):
                    liaison = "‿z"
                elif current.endswith(("d", "t")):
                    liaison = "‿t"
                elif current.endswith("n"):
                    liaison = "‿n"

        if liaison:
            phonetic = f"{phonetic}{liaison}"

        timeline.append({
            "Mot": text_word,
            "Phonétique": phonetic,
            "Début": float(word.get("start", 0.0)),
            "Fin": float(word.get("end", word.get("start", 0.0))),
            "Liaison": bool(liaison),
        })

    return timeline


def construire_groupes_phonetiques(timeline, max_words=8):
    groups = []
    current = []

    for item in timeline:
        current.append(item)
        if len(current) >= max_words or not item.get("Liaison", False):
            groups.append(current)
            current = []

    if current:
        groups.append(current)

    result = []
    for group in groups:
        if not group:
            continue
        result.append({
            "debut": float(group[0]["Début"]),
            "fin": float(group[-1]["Fin"]),
            "texte": " ".join(str(x["Mot"]) for x in group),
            "phonetique": " ".join(str(x["Phonétique"]) for x in group),
        })

    return result



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
    """Compatibility adapter.

    Structure is now secondary and visual-only. The canonical timestamps live
    in the independent chord/phoneme/lyrics timelines.

    `block_measures` is intentionally ignored: the internal observation window
    belongs to the structure engine and is not an editorial block size.
    """
    lyrics_timeline = build_lyrics_timeline(resultat)

    sections = detect_visual_blocks(
        mesures=mesures,
        lyrics_timeline=lyrics_timeline,
        similarity_threshold=similarity_threshold,
    )

    # R30 callers still expect lyrics/type/cluster fields.
    for section in sections:
        t0 = float(section["time_start"])
        t1 = float(section["time_end"])
        words = [
            item["text"]
            for item in lyrics_timeline
            if float(item["end"]) >= t0 and float(item["start"]) <= t1
        ]
        section["lyrics"] = " ".join(words)
        section["lyrics_norm"] = _normaliser_texte_structure(section["lyrics"])
        section["cluster_repeats"] = 1
        section["lyric_repeat"] = 0.0
        section["harmonic_repeat"] = 0.0

    return sections

