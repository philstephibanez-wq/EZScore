# EZScore — sondes de performance dans un fichier

Base GitHub réanalysée avant livraison :

```text
master = 15518e2e7e50a3d78835d70574457ec3528ad930
commit = EZScore_R30_MIDI_FIX2_FAST
```

## Où est passé le lecteur MP3 + MIDI ?

Le code GitHub courant contient toujours le lecteur synchronisé :

```python
render_editor_comparison_player(...)
```

mais il n'est appelé que pour :

```text
Vue = Grille ou Paroles + accords
Mode = Édition
```

La vue `Analyse` n'affiche actuellement que le téléchargement du MIDI et contient
même un texte obsolète indiquant « Grille > Jouer », alors qu'il n'existe plus de
vue `Jouer`.

C'est une régression d'orchestration/UI, pas une suppression du moteur du
lecteur. Le lecteur lui-même existe encore dans :

```text
ezscore/backoffice/player.py
ezscore/midi/web_player.py
```

Avant de le replacer dans `Analyse`, cette livraison instrumente d'abord les
lenteurs globales, comme demandé.

## Log fichier

Les sondes n'écrivent pas dans PowerShell.

Fichier principal :

```text
H:\EZScore\data\logs\ezscore_perf.log
```

Rotation automatique :

```text
ezscore_perf.log
ezscore_perf.log.1
...
ezscore_perf.log.5
```

Format : JSON Lines (une mesure par ligne).

## Accès UI

Pour un administrateur, un panneau apparaît dans la sidebar :

```text
🧪 Diagnostic performances
```

avec :

```text
⬇ Télécharger le log
🧹 Vider le log
```

## Sondes installées

### Cycle Streamlit

```text
rerun.start
```

### Persistence / DB

```text
persistence.load_latest_persisted_analysis
persistence.load_persisted_analysis
persistence.load_structure_blocks
persistence.materialiser_structure_blocks
persistence.effective_lyrics_words_for_sections
persistence.load_measure_edits
persistence.load_lyric_block_edits
persistence.list_song_catalog
```

### Analyse audio / Plotly

```text
timeline.waveform_preview_cache
timeline.create_harmonic_timeline
timeline.chord_regions
timeline.render.summary
ui.plotly_chart
```

### MIDI

```text
midi.build_chord_midi_events
midi.build_midi_file
midi.symbol.exported
```

### Phonèmes / structure

```text
transcription.construire_timeline_phonetique
transcription.construire_groupes_phonetiques
transcription.detecter_sections_structurelles
transcription.extraire_mots
```

### UI

```text
ui.dataframe
ui.download_button
ui.image
ui.analysis_sidebar.load_latest
ui.analysis_sidebar.state
```

Chaque entrée comporte notamment :

```text
timestamp UTC
event
duration_ms
section
audio_hash
view
mode
status
```

quand ces informations sont disponibles.

## Important

Le coût des sondes est volontairement faible :

- pas de log pour chaque `markdown`;
- pas de log pour chaque `write`;
- pas de log pour chaque widget;
- fichiers rotatifs;
- aucune dépendance supplémentaire.

## Correctifs conservés

Cette livraison conserve :

- pré-roll / post-roll vocal validé;
- moteur de structure R33;
- pont MIDI `build_midi_file`;
- timeline Analyse optimisée (nombre de traces Plotly quasi constant).

Les traces de diagnostic ajoutées précédemment avec `print(...)` dans les
fichiers livrés sont redirigées vers le fichier de performance.

## Fichiers livrés

```text
ezscore/diagnostics/__init__.py
ezscore/diagnostics/perf.py
ezscore/ui/app_shell.py
ezscore/timeline.py
readme.md
```

Aucune DB.
Aucun audio.
Aucun fichier auth/SSO.
Aucun `apply_*.py`.

## Installation

```powershell
cd H:\EZScore

tar -xf "$env:USERPROFILE\Downloads\EZScore_R30_PERF_PROBES.zip" -C H:\EZScore

python -m py_compile .\ezscore\diagnostics\__init__.py
python -m py_compile .\ezscore\diagnostics\perf.py
python -m py_compile .\ezscore\ui\app_shell.py
python -m py_compile .\ezscore\timeline.py
python -m py_compile .\EZScore.py
python -m compileall -q .\ezscore

python -m streamlit run .\EZScore.py
```

## Recette demandée

1. Vider le log via `🧪 Diagnostic performances`.
2. Ouvrir successivement :
   - Répertoire;
   - Grille;
   - Paroles + accords;
   - Blocs;
   - Analyse.
3. Attendre l'affichage complet de chaque vue.
4. Télécharger `ezscore_perf.log` depuis le panneau diagnostics.
5. Me transmettre le fichier.

À partir de ce log, on pourra identifier précisément si les minutes sont
perdues dans :

```text
DB
reconstruction des timelines
Plotly
MIDI
phonèmes
structure
ou rendu Streamlit
```

sans se fier à des suppositions.
