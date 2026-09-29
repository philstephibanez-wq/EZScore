# CDC CONTRACTUEL — Timeline musicale canonique EZScore
Version R39.0 — 29/09/2026

Ce document est contractuel. Une violation est une régression.

## Modèle de référence
EZScore suit une partition musicale et un DAW/MIDI studio : une seule portée/timeline, plusieurs pistes. Toutes les pistes partagent exactement la même horloge. Le nombre d'événements d'une piste ne modifie jamais le temps ni la géométrie d'une autre piste.

Pistes : beats/mesures/tempo, accords, voix/syllabes, mélodie, guitare, piano, basse, batterie, MIDI, stems audio et futures pistes.

## ChordsLab
ChordsLab est la référence fonctionnelle validée : audition synchronisée, défilement continu et smooth, current beat, accords synchronisés, édition des accords. La mutualisation ne doit **pas remettre en cause ChordsLab**.

ChordsLab et LyricsLab utilisent le même moteur pour la projection des beats, mesures, `time_ms -> X`, current beat, accords et édition des accords.

## Aucune déformation temporelle par piste
Aucun warp de texte, aucun offset LyricsLab et aucun espacement dépendant de la longueur des mots. Une collision graphique se résout par taille, hauteur ou disposition verticale, jamais par déformation de la timeline.

## Syllabe = unité temporelle
Le mot reste éditorial/graphique. La syllabe est temporelle. Chaque syllabe possède `start_ms`, `nucleus_ms`, `end_ms`, `word_index`, `syllable_index`.

La syllabe appartient au beat courant mais conserve sa phase intra-beat :
`beat = dernier beat tel que beat.start_ms <= nucleus_ms`
`phase = (nucleus_ms - beat.start_ms) / (nextBeat.start_ms - beat.start_ms)`

## Rendu
LyricsLab affiche sous forme syllabée, comme sur une partition : `J'a-vais  des-si-né  sur  le  sa-ble`.
Tiret uniquement entre syllabes du même mot ; pas entre mots ; ponctuation/apostrophes conservées autant que possible ; monosyllabe intact.

## Pipeline vocal contractuel
`lead_vocals.wav`
→ `Whisper : reconnaissance texte / mots / langue`
→ `texte éditorial validé`
→ `forced aligner phonétique`
→ `phonèmes horodatés`
→ `regroupement phonèmes -> syllabes`
→ `start_ms / nucleus_ms / end_ms`
→ `projection sur timeline canonique ChordsLab`
→ `LyricsLab / karaoké / impression`.

Whisper reste la source de proposition de texte, mais ses timestamps mots ne sont pas la référence fine définitive du karaoké.

Tant qu'un forced aligner phonétique n'est pas installé, les syllabes intermédiaires doivent rester identifiables comme non phonétiques ; un centre d'intervalle synthétique ne doit jamais être présenté comme un vrai nucleus phonétique.

## Vocalisations
`hé`, `oh`, `ah`, cris, humming, etc. peuvent exister comme `vocalization` ou `non_lexical` sans obligation d'être ajoutés au texte éditorial principal.

## Accords dans LyricsLab
Même endpoint, même source de vérité, même beat override et même profil que ChordsLab. Une correction faite dans LyricsLab doit être visible dans ChordsLab après rechargement et inversement.

## Non-régression ChordsLab
Aucun timestamp beat/chord ne change. Aucune analyse harmonique, aucun endpoint ChordsLab, aucun smooth scroll, profil, grille ou diagramme ne doit être régressé.

## Recette
1. Même timestamp => même beat dans ChordsLab/LyricsLab.
2. Même timestamp => même accord courant.
3. `nucleus_ms` projette une syllabe sur le même axe X que tout événement au même temps.
4. Aucun texte ne déforme le temps.
5. Édition accord LyricsLab = même donnée ChordsLab.
6. Nombre de syllabes sans effet sur la vitesse.
7. Beats/accords inchangés.
8. ChordsLab reste identique fonctionnellement.
