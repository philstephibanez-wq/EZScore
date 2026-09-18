# EZScore — CANONICAL_RUNTIME_R3

Ce lot traite la cause racine des comportements différents entre chansons.

## Diagnostic confirmé dans le code

EZScore possédait simultanément :

```text
ez_work_mode_<audio_hash>
```

Donc le mode de travail était mémorisé par chanson.

Ensuite `load_latest_persisted_analysis()` faisait :

```text
ancienne analyse persistée en premier
STEM_LAB seulement si aucune ancienne analyse
```

Enfin deux surfaces Analyse coexistaient :

```text
ancien Analyse monolithique EZScore.py
nouvel Analyse STEM_LAB
```

Le résultat était exactement celui observé :

```text
La Bohème -> ancien affichage Analyse
Jolene    -> autre chemin / player sans accords
```

Ce n'est pas la chanson qui doit choisir l'architecture.

## R3

```text
UN EZScore
UN MODE DE TRAVAIL DE SESSION
UNE SOURCE TECHNIQUE : STEM_LAB
UNE SURFACE ANALYSE : stem_lab_analysis
```

### Mode de travail

Source canonique :

```text
ez_work_mode
```

Les anciennes clés :

```text
ez_work_mode_<audio_hash>
```

ne sont plus que des miroirs de compatibilité.

### Analyse

Le vieux bloc Analyse ne peut plus reprendre la main.

Quand le mode vaut Analyse :

```text
stem_lab_analysis.render_stem_lab_fresh_analysis(audio_hash)
```

est toujours rendu, puis l'ancien bloc est stoppé.

### Édition / Player

Ils consomment STEM_LAB. Une ancienne analyse SQLite ne remplace plus
silencieusement la vérité STEM_LAB parce qu'un morceau est ancien.

### Accords Jolene

Le player reste read-only.

Il lit :

```text
structure_analysis.json / beat_timeline
```

et, pour les caches STEM_LAB plus anciens dont les beats n'avaient pas encore
le champ chord exploitable, il projette EN LECTURE SEULE :

```text
chord_analysis_lv_chordia.json / segments
```

sur les timestamps de beats déjà persistés.

Aucun moteur d'accord n'est lancé par le player.

## Fichiers

Nouveau :

```text
ezscore/ui/canonical_runtime.py
```

Cumul R2 inclus et modifié :

```text
ezscore/analysis/technical_snapshot.py
ezscore/player/analysis_truth_player.py
ezscore/ui/analysis_reanalysis_controls.py
ezscore/ui/architecture_contract.py
ezscore/ui/__init__.py
```

Aucun code spécifique à La Bohème, Jolene ou à un hash audio.

## Installation

```powershell
cd H:\EZScore

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\EZScore_CANONICAL_RUNTIME_R3.zip" `
  -DestinationPath . `
  -Force

python -m py_compile `
  .\ezscore\analysis\technical_snapshot.py `
  .\ezscore\player\analysis_truth_player.py `
  .\ezscore\ui\analysis_reanalysis_controls.py `
  .\ezscore\ui\architecture_contract.py `
  .\ezscore\ui\canonical_runtime.py `
  .\ezscore\ui\__init__.py

python -c "from pathlib import Path; from ezscore.ui.architecture_contract import assert_repository_contract; assert_repository_contract(Path('.')); print('ARCH CONTRACT OK')"

git diff --check
git status --short
```

## Test avant tout push

1. Redémarrer Streamlit.
2. Ouvrir La Bohème.
3. Choisir Analyse.
4. Vérifier : même écran STEM / Paroles / Blocs-structure / MIDI.
5. Ouvrir Jolene.
6. Vérifier : exactement la même architecture.
7. Player Jolene : accords visibles si les segments lv-chordia sont déjà persistés.
8. Si aucun cache d'accord n'existe réellement, utiliser Ré-analyser accords dans Analyse.
9. Passer d'une chanson à l'autre : le choix Analyse / Édition / Player ne doit plus muter par chanson.

Si La Bohème revient encore sur le vieux "Déroulé harmonique", R3 est KO et le rollback est justifié.
