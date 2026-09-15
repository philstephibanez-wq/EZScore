# EZScore — STEM pipeline R7 / MIDI chant + accords + batterie

Branche cible : `feature/stem-analysis-pipeline`

R7 ajoute les premières pistes MIDI dérivées du pipeline STEM.

## Contrat temporel

L'audio original reste l'horloge maître.

```text
vocals.wav       -> MIDI Chant
other+bass       -> timeline accords -> MIDI Accords
drums.wav        -> beats -> MIDI Batterie
```

Tous les événements MIDI utilisent les timestamps en secondes de l'audio
original. La génération MIDI ne déplace aucun timestamp de parole, accord,
beat, mesure ou bloc.

## Fichiers produits

```text
data/analysis/stem_lab/<audio_hash>/midi/
  vocal.mid
  chords.mid
  drums.mid
  stem_mix.mid
  stem_midi.json
```

`stem_mix.mid` est un MIDI format 1 multitrack :
- Vocal
- Chords
- Drums

## Chant

Analyse directe de `vocals.wav` avec pYIN, sans relancer Demucs.

## Accords

Le MIDI reprend les accords déjà produits dans `structure_analysis.json`.
Les temps de début/fin des mesures restent ceux de l'analyse structurelle.

## Batterie

`drums.wav` fournit la grille de beats. Le MIDI de contrôle utilise le canal
GM batterie 10 :
- kick 36
- snare 38
- closed hi-hat 42

Il s'agit d'une piste de vérification rythmique, pas encore d'une
transcription complète de chaque élément de batterie.

## Interface

Nouvelle section `MIDI dérivé des stems` avec :
- Générer / régénérer les MIDI
- téléchargement Chant
- téléchargement Accords
- téléchargement Batterie
- téléchargement MIDI combiné
- export `stem_midi.json`

## Installation

Dézipper directement dans `H:\EZScore`.

```powershell
cd H:\EZScore
python -m py_compile .\ezscore\analysis\stems.py
python -m py_compile .\ezscore\analysis\stem_midi.py
python -m py_compile .\ezscore\player\stem_webaudio.py
python -m py_compile .\ezscore\ui\app_shell.py
python -m py_compile .\ezscore\ui\stem_lab_analysis.py
git status --short
```

Ne pas ajouter :
- `data/EZScore.sqlite3`
- `data/logs/ezscore_perf.log`
- `data/analysis/`

L'utilisateur effectue lui-même commit/push.
