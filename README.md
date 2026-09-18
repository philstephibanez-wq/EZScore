# EZScore — restauration Analyse > Paroles R5.10

## Cause identifiée

La gestion R5.10 n'avait pas été supprimée : ses fichiers et templates sont
toujours présents.

Le problème est le routage :

- R5.10 est branché sur `render_stem_lab_fresh_analysis()`;
- cette surface était injectée lorsqu'un morceau était encore considéré comme
  "fresh song";
- après réouverture depuis le Répertoire, EZScore retombait sur la branche
  Analyse historique de `EZScore.py`;
- on voyait alors les anciennes vues Analyse / Édition / Player au lieu de
  l'onglet Paroles validé.

## Correction

Le correctif est volontairement limité à :

```text
ezscore/ui/__init__.py
```

Quand un morceau persisté est ouvert avec la vue `Analyse`, le hook attend le
point exact où la branche Analyse historique commence (`ez-view-analytic-heading`).

À cet instant :

1. les contrôles latéraux du morceau sont déjà rendus ;
2. la surface validée `STEM / Paroles / Blocs / MIDI` est affichée ;
3. l'éditeur Paroles R5.10 déjà installé est utilisé ;
4. la branche Analyse historique est arrêtée pour ce rerun.

Aucun fichier du player, aucune timeline technique, aucun template Paroles et
aucune donnée éditoriale ne sont modifiés.

## R5.10 préservé

La vue `Analyse > Paroles` doit retrouver :

- quatre lanes synchronisées Sections / Accords / Chant / Chœurs ;
- édition mot au double-clic ;
- accords éditables beat par beat ;
- ancres éditoriales ;
- `↵` par clic long puis déplacement/suppression ;
- scrollbar horizontale commune persistante ;
- accords regroupés selon la signature choisie dans le player Analyse ;
- aucune signature affichée dans Paroles ;
- aucune modification des timestamps techniques.

## Installation

```powershell
cd H:\EZScore
Expand-Archive -Path "$env:USERPROFILE\Downloads\EZScore_RESTORE_LYRICS_R5_10_R1.zip" -DestinationPath . -Force
python -m py_compile .\ezscore\ui\__init__.py
git diff --check
git status --short
```

Puis relancer Streamlit.

## Test ciblé

1. Ouvrir une chanson déjà persistée depuis le Répertoire.
2. Choisir `Analyse`.
3. Vérifier les onglets `1 · STEM`, `2 · Paroles`, `3 · Blocs / structure`,
   `4 · MIDI`.
4. Dans `2 · Paroles`, vérifier l'éditeur timeline R5.10.
5. Vérifier qu'un mot peut encore être modifié au double-clic.
6. Vérifier `↵`, ancres, scrollbar et édition d'accord.
7. Changer la signature dans le player Analyse et vérifier que seule la
   représentation des accords change dans Paroles.

## Portée

Ce lot ne modifie pas :

- `EZScore.py`;
- le player R12c;
- les templates `lyrics-editor.*`;
- `editorial_timeline.py`;
- la base SQLite;
- le Répertoire social R2;
- i18n.
