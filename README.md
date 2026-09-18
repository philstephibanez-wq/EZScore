# EZScore — Architecture Boundaries R2

R2 corrige les deux régressions constatées après R1 sans réintroduire le mélange
de responsabilités.

## Régression R1 constatée

R1 a correctement retiré l'analyse du player, mais a retiré avec elle deux
capacités utilisateur qui devaient être **déplacées**, pas supprimées :

```text
- les commandes Ré-analyser paroles / accords / tout ;
- l'alimentation en accords du player quand le snapshot technique est prêt.
```

## Architecture R2

```text
ANALYSE
  ├─ calcule Whisper
  ├─ calcule beats + accords
  ├─ persiste structure_analysis.json
  └─ expose les commandes de réanalyse

TECHNICAL SNAPSHOT
  └─ lecture seule des artefacts persistés

PLAYER STEM
  └─ lit uniquement le snapshot

PAROLES + ACCORDS
  └─ édition / présentation seulement
```

## Commandes de réanalyse

Les trois commandes sont restaurées, mais **dans Analyse**, hors du player :

```text
↻ Ré-analyser paroles
↻ Ré-analyser accords
↻ Ré-analyser tout
```

`Ré-analyser tout` signifie ici :

```text
paroles + rythme + harmonie
à partir de l'audio/STEMs existants
```

Ce n'est pas la `Réanalyse complète`, qui reste l'action de purge totale.

## Accords du player

Le player lit désormais les accords exclusivement depuis :

```text
structure_analysis.json
  -> beat_timeline[]
  -> chord
```

via :

```text
ezscore/analysis/technical_snapshot.py
```

Aucun `karaoke_conductor.json` n'est utilisé comme source de vérité.

Donc :

```text
Analyse accords terminée
→ structure_analysis.json persiste les accords
→ player les affiche

Structure absente
→ player n'invente rien
→ Ré-analyser accords / tout se fait dans Analyse
```

## Fichiers

Nouveaux :

```text
ezscore/analysis/technical_snapshot.py
ezscore/ui/analysis_reanalysis_controls.py
```

Modifiés :

```text
ezscore/player/analysis_truth_player.py
ezscore/ui/architecture_contract.py
ezscore/ui/__init__.py
```

Non modifiés :

```text
ezscore/ui/stem_lab_analysis.py
ezscore/player/karaoke_stem_webaudio.py
ezscore/player/karaoke_stem_webaudio_r12c.py
ezscore/ui/lyrics_inline_editor.py
ezscore/ui/editorial_timeline.py
templates/views/lyrics-editor.*
```

## Installation

```powershell
cd H:\EZScore

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\EZScore_ARCH_BOUNDARIES_R2.zip" `
  -DestinationPath . `
  -Force

python -m py_compile `
  .\ezscore\analysis\technical_snapshot.py `
  .\ezscore\player\analysis_truth_player.py `
  .\ezscore\ui\analysis_reanalysis_controls.py `
  .\ezscore\ui\architecture_contract.py `
  .\ezscore\ui\__init__.py

python -c "from pathlib import Path; from ezscore.ui.architecture_contract import assert_repository_contract; assert_repository_contract(Path('.')); print('ARCH CONTRACT OK')"

git diff --check
git status --short
```

## Test ciblé La Bohême

1. Redémarrer Streamlit.
2. Ouvrir `Analyse`.
3. Les trois boutons de réanalyse doivent être visibles sur la page Analyse,
   pas dans le player.
4. Cliquer `Ré-analyser tout`.
5. Après rerun :
   - état technique : mots > 0, beats > 0, accords > 0 ;
   - player STEM : paroles + accords présents ;
   - aucun moteur d'analyse ne se déclenche quand on utilise Play / Seek.
6. Ouvrir `Paroles + accords` :
   - aucun Whisper / beat / accord ne doit être lancé.
