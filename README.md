# EZScore — Analysis HQ R14

Ce livrable ne touche **que la chaîne d'analyse**. Aucun fichier MIDI n'est
modifié.

## Objectif

Qualité maximale avant vitesse :

- STEM : BS-RoFormer-SW, six stems bruts ;
- rythme : madmom-infer RNN + DBN ;
- accords : lv-chordia, ensemble de 5 réseaux + HMM ;
- paroles : Whisper SMALL existant, inchangé ;
- MP3 original : horloge maître unique.

## Principe fondamental

L'analyse harmonique est maintenant indépendante de la métrique.

`lv-chordia` produit d'abord une timeline absolue :

`[t0, t1, accord]`

sur le MP3 original. EZScore projette ensuite ces segments sur la timeline
rythmique. Changer 4/4, 6/8, 9/8, 5/4, etc. ne relance donc pas le moteur
d'accords et ne déplace aucun timestamp.

## STEM

Le modèle par défaut est :

`roformer-model-bs-roformer-sw-by-jarredou`

Il produit :

- vocals
- drums
- bass
- guitar
- piano
- other

EZScore conserve les 6 stems bruts et construit ses 4 stems canoniques :

- vocals = vocals
- drums = drums
- bass = bass
- other = guitar + piano + other

Les poids ne sont jamais commités dans Git.

## Installation Windows

Depuis la racine `H:\EZScore` après dézip du livrable :

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install_analysis_hq.ps1
```

Optionnel, pour placer les modèles sur un autre disque :

```powershell
$env:BS_ROFORMER_MODELS_PATH="H:\EZScoreModels\bs-roformer"
```

Pour rendre cette variable permanente pour l'utilisateur :

```powershell
[Environment]::SetEnvironmentVariable(
    "BS_ROFORMER_MODELS_PATH",
    "H:\EZScoreModels\bs-roformer",
    "User"
)
```

## Comportement en cas d'absence d'un moteur

Aucun fallback silencieux :

- BS-RoFormer absent -> erreur explicite ;
- madmom-infer absent -> erreur explicite ;
- lv-chordia absent -> erreur explicite.

EZScore ne revient pas automatiquement au vieux Demucs/librosa/chroma.

## Réanalyse nécessaire

Après installation de R14, il faut relancer l'analyse STEM d'un morceau une
fois afin de produire les nouveaux stems RoFormer. Whisper SMALL n'a pas besoin
d'être relancé s'il est déjà présent.

L'analyse harmonique HQ est calculée sur le MP3 original et mise en cache dans :

`data/analysis/stem_lab/<audio_hash>/chord_analysis_lv_chordia.json`

La métrique peut ensuite être modifiée sans recalcul de cette timeline
harmonique.

## Fichiers modifiés / ajoutés

- `ezscore/analysis/stems.py`
- `ezscore/analysis/chords_quality.py`
- `ezscore/analysis/rhythm_quality.py`
- `ezscore/ui/stem_lab_analysis.py`
- `models/manifests/analysis_hq.json`
- `requirements-analysis-hq.txt`
- `scripts/install_analysis_hq.ps1`
- `readme.md`

Aucun fichier `ezscore/analysis/stem_midi.py`, MIDI player ou génération MIDI
n'est inclus dans ce livrable.
