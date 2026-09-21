# EZScore_MANUAL_LYRICS_FORCED_ALIGN_R1

Base GitHub vérifiée avant livraison :

```text
master = c825fc54c3b89f2b9229f576c45d6e8ec8776600
```

## Nouveau principe

Le chemin actif de paroles devient :

```text
texte exact fourni par l'utilisateur
        +
lead_vocals.wav
        ↓
uroman (romanisation multilingue)
        ↓
TorchAudio MMS_FA
        ↓
forced alignment
        ↓
mots + timestamps
        ↓
timeline canonique EZScore
```

Il n'y a plus dans ce chemin :

```text
détection de langue depuis l'audio
transcription libre Whisper
Whisper Chœurs
texte Chœurs
```

Les stems audio restent inchangés. `backing_vocals.wav` reste disponible dans
le mixer mais n'est pas transcrit.

## Multilingue

MMS_FA est un modèle de forced alignment multilingue. Le texte utilisateur est
romanisé par `uroman`, sans imposer une langue globale au morceau.

Un texte du type :

```text
Je voudrais encore
And I know that someday
Je reviendrai
```

est donc aligné comme une seule séquence connue.

Le texte original reste celui affiché. La romanisation n'est qu'une
représentation acoustique interne.

Pour les langues sans séparation explicite des mots (certaines écritures
chinoises/japonaises notamment), R1 suppose que le texte fourni contient déjà
des séparations de mots exploitables.

## Mots qui se superposent

`ezscore/player/lyrics_layout.py` disposait déjà du moteur de collision
`ezLayoutLaneNodes`, mais la géométrie R12c ne l'utilisait pas réellement.

R1 branche ce moteur :

```text
position temporelle brute
→ largeur réelle du mot
→ espacement minimum 12 px
→ courbe visuelle interpolée pour le défilement
```

Les timestamps canoniques ne sont pas déplacés pour résoudre l'affichage.

## GPU / durée

MMS_FA est exécuté par segments acoustiques de 20 secondes puis les émissions
sont concaténées avant le forced alignment global. Cela évite de passer une
chanson entière dans le modèle Wav2Vec2 en une seule fois sur la RTX 2060 6 GB.

Le modèle Torch est stocké hors de C: :

```text
H:\EZScoreModels\torch
```

avec l'arborescence habituelle `H:\EZScore`. La variable
`EZSCORE_MODELS_PATH` peut remplacer cette racine.

## Installation

```powershell
cd H:\EZScore

tar -xf "$env:USERPROFILE\Downloads\EZScore_MANUAL_LYRICS_FORCED_ALIGN_R1.zip" -C H:\EZScore

.\.venv-py313\Scripts\python.exe -m pip install -r .\requirements-forced-alignment.txt

.\.venv-py313\Scripts\python.exe -m py_compile `
  .\ezscore\analysis\forced_lyrics.py `
  .\ezscore\integration\choir_pipeline.py `
  .\ezscore\player\lyrics_layout.py `
  .\scripts\test_manual_forced_alignment_contract.py `
  .\scripts\test_manual_forced_alignment_runtime.py

.\.venv-py313\Scripts\python.exe .\scripts\test_manual_forced_alignment_contract.py
.\.venv-py313\Scripts\python.exe .\scripts\test_manual_forced_alignment_runtime.py
```

Attendu :

```text
MANUAL LYRICS / FORCED ALIGNMENT CONTRACT OK
free transcription: DISABLED
audio language detection: DISABLED
lyrics source: USER TEXT
acoustic source: lead_vocals.wav
forced alignment: MMS_FA
choir lyrics: DISABLED
word collision layout: ENABLED

FORCED ALIGNMENT RUNTIME OK
...
```

Redémarrer ensuite complètement Streamlit.

Dans `Analyse > 2 · Paroles` :
1. coller le texte exact du chant ;
2. cliquer `Aligner le texte sur le Chant` ;
3. après alignement, vérifier les mots horodatés puis le player.

## Premier alignement

Le premier alignement télécharge les poids MMS_FA dans
`H:\EZScoreModels\torch`. Les tests fournis ne téléchargent pas le modèle.

## Licence du modèle

La documentation TorchAudio indique que les poids MMS_FA sont publiés sous
licence CC-BY-NC 4.0. Ce R1 convient à notre validation technique actuelle.
Avant une exploitation commerciale d'EZScore, il faudra valider la
compatibilité de cette licence ou remplacer le moteur par un aligneur dont la
licence convient.

L'ancien code de détection de langue audio n'est pas supprimé par ce
livrable : il devient simplement inactif dans le chemin canonique Paroles.
