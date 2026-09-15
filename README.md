# EZScore — Stem pipeline R2 visible

Branche cible : `feature/stem-analysis-pipeline`

R1 était volontairement backend-only. R2 rend le nouveau pipeline visible
dans **Chanson > Analyse**.

Le panneau **Analyse STEM — nouveau pipeline** affiche et prépare :

```text
Original → Whisper small → paroles
vocals   → mélodie / F0
drums    → tempo / beats / mesures
bass     → fondamentale auxiliaire
other    → harmonie / accords
```

Ce checkpoint reste non destructif :
- l'analyse musicale historique n'est pas encore remplacée ;
- aucune timeline n'est déplacée ;
- aucune écriture SQLite supplémentaire ;
- aucun fichier DB/log n'est livré ;
- si Demucs est indisponible, l'analyse existante continue.

## Installation

Dézipper directement dans `H:\EZScore`, sans dossier intermédiaire.

```powershell
cd H:\EZScore
python -m py_compile .\ezscore\analysis\stems.py
python -m py_compile .\ezscore\ui\app_shell.py
git status --short
```

Ne pas ajouter au commit :
- `data/EZScore.sqlite3`
- `data/logs/ezscore_perf.log`

Après validation visuelle, prochain checkpoint : branchement réel de
`drums.wav` au rythme, `other.wav` à l'harmonie et `bass.wav` à l'évidence
de fondamentale, avec fallback vers le moteur actuel.
