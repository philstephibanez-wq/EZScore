# EZScore R29 FIX2 — blocs, sidebar et diagrammes

Correctif cumulatif de la R29.

## 1. Panneau gauche conservé en Vue / Édition

Le profil et la navigation restent visibles dans toutes les vues.

- Répertoire : profil + navigation
- Chanson / Vue : profil + navigation
- Chanson / Édition : profil + navigation + outils techniques
- Import : profil + navigation + outils techniques
- Compte : profil + navigation

Les réglages techniques ne remplacent plus le panneau profil.

## 2. Gestion des blocs restaurée

Dans `Blocs > Édition`, la colonne droite redevient une édition des **paroles seules**, sans accords.

Chaque bloc affiche :
- son nom ;
- sa plage de mesures ;
- un champ de paroles éditable ;
- les corrections persistées si elles existent.

Le bouton `Valider les paroles des blocs` enregistre les corrections sans déplacer les accords ni la timeline.

La structure du morceau reste éditée à gauche et validée séparément.

## 3. Diagrammes guitare déterministes

Le catalogue explicite reste prioritaire.

Pour un accord majeur ou mineur absent du catalogue, EZScore génère désormais automatiquement une position barrée E-shape. Cela couvre notamment les accords fréquents auparavant absents :

`A#`, `Bb`, `B`, `Bm`, `C#`, `Cm`, `D#`, `Eb`, `F#`, `Fm`, `G#`, etc.

Ainsi un accord majeur/mineur supporté ne doit plus voir son diagramme disparaître/revenir au gré de la lecture.

Les accords enrichis (7, maj7, m7, dim...) seront ajoutés progressivement au catalogue dédié.

## Fichiers du livrable

- `EZScore.py`
- `readme.md`
- `ezscore/ui/app_shell.py`
- `ezscore/guitar/voicings.py`
