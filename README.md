# EZScore — Player Seek + Lyrics R1

Base GitHub constatée avant ce correctif :

```text
240ad1f396e9405a2073a2752674c847c046c4ab
EZScore_ANALYSIS_TIMELINE_R1
```

## 1. Déplacement dans le player STEM sans lecture préalable

Le slider pouvait être réellement utilisé seulement après initialisation audio,
car `duration` restait à zéro jusqu'au premier clic Lecture.

Le composant charge désormais uniquement les métadonnées de la preview
`original` au montage :

```text
Audio(preload=metadata)
→ duration
→ seek.max
→ time label
```

Cela ne crée pas d'AudioContext et ne démarre aucun son.

On peut donc :
1. ouvrir Analyse > STEM ;
2. déplacer immédiatement le slider à 1:30 ;
3. inspecter accords/paroles à cette position ;
4. appuyer Lecture seulement si on veut écouter.

La future lecture démarre à la position choisie.

## 2. Faux « Chœurs » issus de la seconde transcription Whisper

Le code historique faisait :

```text
mot absent du Whisper mix
+ présent dans Whisper vocals
= Chœurs
```

Cette conclusion est sémantiquement fausse. Une omission du premier Whisper ne
prouve pas la présence d'un choriste.

Désormais :

```text
Whisper mix
+ récupération Whisper stem voix
= Chant principal complété
```

La lane Chœurs n'est plus alimentée artificiellement par les simples omissions
Whisper.

La détection de vrais chœurs devra reposer sur une source explicite permettant
de distinguer plusieurs voix simultanées.

Aucune règle par chanson, chanteur, titre ou hash.

## 3. Mots qui se chevauchent dans Analyse > Paroles

Le template commun :

```text
templates/views/lyrics-editor.js
```

applique maintenant un layout anti-collision aux lanes Chant et Chœurs.

Les timestamps restent inchangés. Seule la position visuelle est décalée quand
la boîte du mot précédent empiète sur la suivante.

Les sauts de ligne utilisent également la position visuelle réelle du mot.

## Fichiers

Modifiés :

```text
ezscore/player/karaoke_word_layout.py
templates/views/lyrics-editor.js
```

Nouveau :

```text
readme.md
```

Non modifiés :

```text
karaoke_stem_webaudio_r12c.py
karaoke_stem_webaudio.py
stem_lab_analysis.py
editorial_timeline.py
lyrics_inline_editor.py
rhythm_intro_fusion.py
analysis_rhythm_patch.py
```

## Installation

```powershell
cd H:\EZScore

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\EZScore_PLAYER_SEEK_LYRICS_R1.zip" `
  -DestinationPath . `
  -Force

python -m py_compile .\ezscore\player\karaoke_word_layout.py

node --check .\templates\views\lyrics-editor.js

git diff --check
git status --short
```

## Test

1. Redémarrer Streamlit.
2. Ouvrir Jolene > Analyse > STEM.
3. Sans cliquer Lecture, déplacer le slider directement vers 0:45 / 1:30.
4. Vérifier que le conducteur se positionne immédiatement.
5. Cliquer Lecture : le son doit démarrer depuis la position choisie.
6. Vérifier que les mots récupérés sur le stem voix restent dans Chant et ne
   passent plus automatiquement dans Chœurs.
7. Analyse > Paroles : vérifier `I'm begging...` et les mots suivants sans
   chevauchement.
8. Vérifier édition inline et saut de ligne ↵.
9. Recontrôler Play/Pause/Stop/seek/vitesse/EQ.
