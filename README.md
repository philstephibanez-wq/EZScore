# EZScore R18

## Correction
Le template racine d'impression est désormais rangé avec les autres templates :

```text
templates/EZScore.score
```

EZScore.py appelle maintenant :

```python
SCORE.render("templates/EZScore.score", ...)
```

Le renderer reste inchangé :

```python
SCORE = ScoreTemplateRenderer(Path(__file__).resolve().parent)
```

Il n'y a aucun retour à une architecture Python monolithique.

## Fichiers modifiés / ajoutés
- EZScore.py
- templates/EZScore.score
- readme.md

## Structure
```text
EZScore/
├─ EZScore.py
├─ EZScoreTemplate.py
├─ templates/
│  ├─ EZScore.score
│  ├─ header.score
│  ├─ left-panel.score
│  └─ views/
└─ data/
```

## Mise à jour locale
```bat
cd /d H:\EZScore
git pull
python -m py_compile EZScore.py
streamlit run EZScore.py
```
