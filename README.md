# EZScore_MUSIC_TIMELINE_R1

Base GitHub vérifiée :

```text
master = 050ae11e5fd610af26266183a3cb8a45b78a0bf2
```

## Objet

Corriger l'ordre du workflow sans recréer l'architecture qui vient d'être
revertée.

Il n'y a **pas** de `technical_timeline.json`, pas de nouveau routeur Analyse,
pas de nouveau patch de cycle de vie Streamlit et pas de Madmom.

La timeline musicale est désormais produite plus tôt dans le cache EZScore
déjà existant :

```text
structure_analysis.json
```

## Pipeline

```text
STEM prêts
    ↓
Paroles forcées prêtes
    ↓
Batterie -> beat tracker librosa déjà utilisé par EZScore
Original -> lv-chordia déjà utilisé par EZScore
    ↓
structure_analysis.json["beat_timeline"]
    ├── Lecteur STEM
    ├── Paroles + accords
    └── Étape 3 Blocs / structure
          ↓
       mesures + motifs + blocs
```

L'étape 3 ne relance plus le calcul beats + accords. Elle consomme les mêmes
timestamps déjà calculés.

## Cache / recalcul

Si `structure_analysis.json` possède déjà au moins deux beats, aucun calcul
n'est relancé.

`lv-chordia` garde son cache existant via `_chord_cache_path(audio_hash)`.

Aucun fichier de cache supplémentaire n'est créé.

## Moteur rythmique

Le précédent essai Madmom a été entièrement abandonné avec les reverts.

R1 utilise le beat tracker librosa déjà présent et éprouvé dans `EZScore.py`,
appliqué directement au STEM Batterie. Il ne s'agit pas d'une nouvelle
dépendance.

## Affichage pendant le premier calcul

Après STEM + paroles alignées, si la timeline n'existe pas encore :

```text
Analyse musicale · beats + accords…
1/2 · Détection des beats sur le STEM Batterie…
2/2 · Raccord des accords lv-chordia sur les beats…
Timeline beats + accords prête.
```

Les ouvertures suivantes réutilisent le cache.

## Player STEM

Le player conserve :
- une seule ligne Accords ;
- une seule ligne Paroles ;
- la notation `Am---` ;
- `_` pour prolongation vocale ;
- la même timeline absolue pour les deux.

La case `Diagrammes guitare` n'est plus poussée à l'extrémité droite : elle
reste près du titre du conducteur.

## Fichiers

```text
ezscore/analysis/music_timeline.py              nouveau
ezscore/integration/choir_pipeline.py           modifié
ezscore/player/stem_analysis_conductor.py       modifié
scripts/test_music_timeline_contract.py         nouveau
readme.md
```

## Application

```powershell
cd H:\EZScore

tar -xf "$env:USERPROFILE\Downloads\EZScore_MUSIC_TIMELINE_R1.zip" -C H:\EZScore

.\.venv-py313\Scripts\python.exe -m py_compile `
  .\ezscore\analysis\music_timeline.py `
  .\ezscore\integration\choir_pipeline.py `
  .\ezscore\player\stem_analysis_conductor.py `
  .\scripts\test_music_timeline_contract.py

.\.venv-py313\Scripts\python.exe .\scripts\test_music_timeline_contract.py
```

Attendu :

```text
MUSIC TIMELINE CONTRACT OK
cache: existing structure_analysis.json
new parallel timeline cache: NONE
rhythm: existing EZScore librosa tracker
harmony: existing lv-chordia cache/engine
Step 2 editor: receives beat_timeline
STEM conductor: receives same beat_timeline
Step 3: reuses timeline, segments only
diagram checkbox: LEFT/INLINE
```

Puis redémarrer Streamlit.

## Git

Cette livraison est basée exactement sur `050ae11`.

Après test seulement :

```powershell
git status --short
git add ezscore/analysis/music_timeline.py `
        ezscore/integration/choir_pipeline.py `
        ezscore/player/stem_analysis_conductor.py `
        scripts/test_music_timeline_contract.py `
        readme.md
git commit -m "EZScore_MUSIC_TIMELINE_R1"
git push origin master
```

Ne faites pas de `git pull` si `git status` indique que `master` est déjà à
jour avec `origin/master`.
