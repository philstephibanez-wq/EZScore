# EZScore — vitesse + lecteur MP3/MIDI + cleanup

Base vérifiée avant livraison :

```text
GitHub master = 007c9399178e913c16e1da2ac28f97b64eb37deb
EZScore_R30_PERF_PROBES
```

## 1. Correction de la lenteur

Le log transmis montre que la cause principale est :

```text
detecter_sections_structurelles ≈ 55,6 secondes
```

Le moteur R33 était relancé à chaque rerun Streamlit, y compris lors d'un simple
changement de vue.

Nouveau comportement :

```text
structure_blocks déjà persistés
    -> réutilisation immédiate
    -> PAS de recalcul R33

structure_blocks absents
    -> calcul R33
    -> ensure_structure_blocks() persiste la proposition
```

Le bouton existant `Réinitialiser depuis l'analyse` continue donc à fonctionner :
il supprime la structure persistée, et le rerun suivant autorise exactement un
nouveau calcul R33.

La trace fichier attendue devient :

```text
structure.persisted.reuse
```

au lieu d'un appel coûteux à :

```text
structure.r33.compute
```

Le pré-roll et le post-roll vocal sont conservés.

## 2. Lecteur MP3 + MIDI restauré dans Analyse

Le lecteur n'avait pas disparu des modules :

```text
ezscore/backoffice/player.py
ezscore/midi/web_player.py
```

mais `EZScore.py` ne l'appelait plus dans `Analyse`.

Cette livraison restaure le lecteur directement au moment où la vue Analyse
construit son MIDI.

Le lecteur contient de nouveau :

```text
audio MP3 maître
volume chanson
volume MIDI
bouton Charger le synthé MIDI
lecture MIDI synchronisée au MP3
```

Le téléchargement `.mid` existant reste affiché ensuite.

Le MP3 archivé est lu via un cache Streamlit afin d'éviter de relire plusieurs
mégaoctets à chaque rerun.

Les événements supplémentaires dans :

```text
H:\EZScore\data\logs\ezscore_perf.log
```

sont :

```text
analysis.player.build_events
analysis.player.render
midi.build_midi_file.bridge
structure.persisted.reuse
structure.r33.compute
```

## 3. Cleanup

Le ZIP contient un `.gitignore` renforcé pour ne plus ajouter :

```text
data/EZScore.sqlite3
data/audio/
data/covers/
data/logs/
EZScore_R30_*/
EZScore_*_FIX*/
```

Les anciens dossiers déjà trackés par Git doivent être retirés une seule fois.

Après installation et recette correcte :

```powershell
cd H:\EZScore

git rm -r --ignore-unmatch `
  EZScore_R30_LYRICS_PREROLL_FIX `
  EZScore_R30_MIDI_FIX `
  EZScore_R30_MIDI_FIX2_FAST

git rm -r --cached --ignore-unmatch `
  data\EZScore.sqlite3 `
  data\audio `
  data\covers `
  data\logs

git rm -r --cached --ignore-unmatch `
  ezscore\auth\__pycache__ `
  ezscore\backoffice\__pycache__ `
  ezscore\guitar\__pycache__ `
  ezscore\midi\__pycache__ `
  ezscore\player\__pycache__ `
  ezscore\ui\__pycache__

git status --porcelain=v1 -uall
```

`--cached` conserve DB/audio/covers/logs sur le disque local.

## Fichiers livrés

```text
.gitignore
ezscore/ui/app_shell.py
readme.md
```

Aucun dossier racine parasite dans le ZIP.
Aucune DB.
Aucun MP3.
Aucun cover.
Aucun patch/apply script.

## Installation

```powershell
cd H:\EZScore

tar -xf "$env:USERPROFILE\Downloads\EZScore_R30_SPEED_PLAYER_CLEANUP.zip" -C H:\EZScore

python -m py_compile .\ezscore\ui\app_shell.py
python -m py_compile .\EZScore.py
python -m compileall -q .\ezscore

python -m streamlit run .\EZScore.py
```

## Recette

1. Ouvrir `Grille`, puis `Paroles + accords`, puis `Blocs`.
   Les changements de vue ne doivent plus déclencher 55 secondes de R33.

2. Ouvrir `Analyse`.
   Sous `Comparaison audio / accords`, le lecteur doit afficher :
   - contrôleur MP3,
   - Volume chanson,
   - Volume MIDI,
   - Charger le synthé MIDI.

3. Vérifier dans `data\logs\ezscore_perf.log` :
   - `structure.persisted.reuse`
   - `analysis.player.render`
   - absence d'un `structure.r33.compute` sur un simple changement de vue.
