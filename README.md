# EZScore — Analysis Timeline R1

Base GitHub vérifiée : `12f8a99ccdd2c3c4fd11873651d500a1e2e8d428` (`Jolene`).

## Correctif 1 — mots superposés dans le player STEM

Correction d'affichage uniquement. Les timestamps Whisper, l'audio, les beats,
les accords et le transport ne sont pas modifiés.

Le player R12c conserve le même HTML/CSS et les mêmes données. La géométrie des
labels devient anti-collision et l'interpolation visuelle continue à utiliser
les timestamps originaux.

Aucune réanalyse nécessaire pour ce correctif.

## Correctif 2 — accords / beats d'intro

Batterie = source primaire.

Le mix original ne complète que le préfixe absent, et uniquement si :
- les stems montrent une présence instrumentale réelle ;
- au moins 3 beats mix forment une séquence régulière ;
- le tempo est compatible avec la batterie ;
- la séquence rejoint naturellement le premier beat batterie.

Aucun beat n'est extrapolé ou inventé.

Si le morceau commence par chant solo, les paroles restent horodatées mais la
zone reste non métrique jusqu'à la première pulsation instrumentale fiable.

Une réanalyse de structure est nécessaire pour corriger une ancienne
`structure_analysis.json`.

## Fichiers

Nouveaux :
- `ezscore/player/karaoke_word_layout.py`
- `ezscore/analysis/rhythm_intro_fusion.py`
- `ezscore/ui/analysis_rhythm_patch.py`

Modifié :
- `ezscore/ui/__init__.py`

Non modifiés :
- `ezscore/ui/stem_lab_analysis.py`
- `ezscore/player/karaoke_stem_webaudio_r12c.py`
- `ezscore/ui/editorial_timeline.py`
- `ezscore/ui/lyrics_inline_editor.py`
- `ezscore/analysis/rhythm_quality.py`
- `templates/views/lyrics-editor.*`

## Installation

```powershell
cd H:\EZScore

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\EZScore_ANALYSIS_TIMELINE_R1.zip" `
  -DestinationPath . `
  -Force

python -m py_compile `
  .\ezscore\player\karaoke_word_layout.py `
  .\ezscore\analysis\rhythm_intro_fusion.py `
  .\ezscore\ui\analysis_rhythm_patch.py `
  .\ezscore\ui\__init__.py

git diff --check
git status --short
```

## Test

1. Redémarrer Streamlit.
2. Jolene > Analyse > STEM : vérifier que les mots ne se chevauchent plus.
3. Vérifier Play/Pause/Stop/seek/vitesse/EQ.
4. Pour l'intro : refaire la structure ou utiliser Réanalyse complète.
5. Vérifier accords d'intro si une pulsation instrumentale fiable existe.
6. Tester un début chant solo : pas de fausse grille avant l'accompagnement.
7. Recontrôler Aline / Dance Me.
