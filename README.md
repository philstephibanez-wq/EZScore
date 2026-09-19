# EZScore — Full Reanalysis R1

Base GitHub : `a6176525896c76cf73b7614b0755847689c4011f`.

## Sémantique figée

### Réanalyse complète

Une réanalyse complète repart réellement de zéro sur tout le contenu
musical/éditorial :

```text
STEMs
browser previews
Whisper
accords
structure
MIDI
analyses SQLite
versions d'analyse
workflow
préférences d'analyse/capo
blocs et corrections
overlays éditoriaux
```

Les caches `data/analysis/stem_lab/<audio_hash>/` sont supprimés physiquement.

Sont volontairement conservés parce que la chanson garde son identité dans le
catalogue :

```text
audio original
songs (titre/artiste/catalogue)
pochette
affectation éditeur
user_playlist_items (playlist + ordre de setlist)
song_ratings
```

Après purge, EZScore revient sur `Analyse` avec une analyse vierge ; le workflow
STEM -> Paroles -> Structure -> MIDI repart donc comme après un nouvel import.

### Suppression définitive

`Supprimer définitivement la chanson` supprimait déjà :

```text
audio original
pochette
toutes les lignes SQLite possédant audio_hash
songs
```

Il manquait le cache physique d'analyse.

Ce lot enveloppe la suppression existante et supprime aussi :

```text
data/analysis/stem_lab/<audio_hash>/
```

Ainsi une suppression suivie du réimport du même fichier ne peut plus récupérer
un ancien Whisper/STEM/accord/MIDI par le même SHA-256.

## Modularité

Nouveaux modules :

```text
ezscore/analysis_lifecycle.py
ezscore/ui/analysis_lifecycle.py
```

Template :

```text
templates/views/analysis-lifecycle.score
```

Intégration minimale :

```text
ezscore/ui/__init__.py
```

Aucune modification dans :

```text
ezscore/persistence.py
ezscore/ui/stem_lab_analysis.py
ezscore/ui/editorial_timeline.py
ezscore/ui/lyrics_inline_editor.py
players R12c
templates/views/lyrics-editor.*
```

## Sécurité

La purge DB de réanalyse est transactionnelle.

Le cache est supprimé AVANT la DB. Si Windows verrouille un fichier STEM ou
preview, la réanalyse s'arrête avant de toucher aux données SQLite.

La sélection des tables à purger est générique : toute table possédant une
colonne `audio_hash` est purgée sauf la liste blanche catalogue/social explicite.

## Installation

```powershell
cd H:\EZScore

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\EZScore_FULL_REANALYSIS_R1.zip" `
  -DestinationPath . `
  -Force

python -m py_compile `
  .\ezscore\analysis_lifecycle.py `
  .\ezscore\ui\analysis_lifecycle.py `
  .\ezscore\ui\__init__.py

git diff --check
git status --short
```

## Test

1. Prendre une chanson analysée et présente dans une playlist.
2. Noter sa position dans la setlist.
3. Ouvrir Chanson > Analyse.
4. Déplier `Réanalyse complète`.
5. Confirmer puis lancer.
6. Vérifier que l'analyse repart sans STEM/Paroles/Structure/MIDI.
7. Vérifier que la chanson reste dans le Répertoire.
8. Vérifier qu'elle reste dans la playlist à la même position.
9. Vérifier que les anciennes corrections éditoriales ne réapparaissent pas.
10. Tester ensuite une suppression définitive + réimport du même fichier :
    aucun ancien cache ne doit réapparaître.
