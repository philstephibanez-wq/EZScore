# EZScore — Stem pipeline R1

Branche cible :

```text
feature/stem-analysis-pipeline
```

Ce livrable ajoute uniquement le module de séparation/cache des stems :

```text
ezscore/analysis/stems.py
```

Aucun remplacement de l'analyse musicale EZScore n'est effectué dans ce
checkpoint.

## Invariants

```text
audio original = horloge maître
```

Rôles prévus :

```text
Original → Whisper small → paroles
Vocals   → mélodie / F0
Drums    → tempo / beats / mesures
Bass     → fondamentale auxiliaire
Other    → harmonie / accords
```

Le module ne modifie ni la base SQLite, ni les logs, ni les timelines
existantes.

## Cache

Les stems sont persistés par hash audio et modèle :

```text
data/
└── analysis/
    └── stems/
        └── <audio_hash>/
            └── htdemucs/
                ├── vocals.wav
                ├── drums.wav
                ├── bass.wav
                ├── other.wav
                └── manifest.json
```

Une séparation réussie n'est donc calculée qu'une fois pour le même hash.

Le cache n'est considéré valide que lorsque les quatre WAV sont présents et
non vides. Une séparation incomplète n'est jamais publiée comme cache valide.

## API

```python
from ezscore.analysis.stems import (
    cached_stem_paths,
    ensure_stems,
    stem_path,
    stems_cache_complete,
)
```

Exemple :

```python
result = ensure_stems(
    audio_bytes=audio_bytes,
    extension=extension,
    audio_hash=audio_hash,
)

drums = result["paths"]["drums"]
other = result["paths"]["other"]
```

## Installation locale

Dézipper le livrable à la racine de `H:\EZScore` en conservant les chemins.

Puis :

```powershell
cd H:\EZScore
python -m py_compile .\ezscore\analysis\stems.py
git status --short
```

Le résultat Git attendu pour ce checkpoint est uniquement :

```text
?? ezscore/analysis/stems.py
```

Les modifications locales déjà présentes dans :

```text
data/EZScore.sqlite3
data/logs/ezscore_perf.log
```

ne doivent pas être ajoutées au commit.

## Commit utilisateur

Après test :

```powershell
git add .\ezscore\analysis\stems.py
git commit -m "Add cached four-stem analysis module"
git push
```

## Étape suivante

Après validation de ce cache, connecter progressivement les consommateurs :

1. `drums.wav` au moteur rythme ;
2. `other.wav` à l'harmonie principale ;
3. `bass.wav` comme évidence auxiliaire de fondamentale ;
4. `vocals.wav` au moteur F0/mélodie.

La transcription des paroles restera sur l'audio original.
