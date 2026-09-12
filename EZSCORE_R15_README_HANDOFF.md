# EZScore R15 — visibilité du commentaire éditorial

## Base exacte

R15 repart du master poussé le 12/09/2026 :

```text
baa047740c2ae944891d9545730e237a55c78381
EZSCORE_R14_FROM_R13
```

Le moteur d'analyse reste :

```text
V29_R14_BALANCED_MIDI_EDITORIAL
```

Aucune modification de l'analyse harmonique, Whisper, MIDI ou du schéma SQLite.

## Problème corrigé

Le commentaire éditorial existait déjà dans le workflow R14 mais son UX prêtait à confusion :
- le champ restait éditable en mode Voir ;
- le commentaire n'était pas visible dans le Répertoire ;
- la distinction Voir / Éditer n'était donc pas nette.

## R15

### Répertoire

Le commentaire courant est affiché sous l'état du morceau :

```text
● Modification en cours
💬 Couplet 2 non terminé
```

Pour une version validée ou publiée, la note attachée à cette version est affichée.

### Voir

La zone Version de la chanson conserve :
- état ;
- V ;
- R ;
- date.

Le commentaire est visible en lecture seule.

Aucun champ de saisie ni bouton « Enregistrer la note » n'est présenté en mode Voir.

### Éditer

Le commentaire redevient un champ « Note de l’éditeur ».

Il peut être enregistré puis repris lors de la validation de la prochaine version.

Exemple :

```text
Couplet 2 non terminé
```

### Workflow conservé

```text
Modification en cours
→ validation Vn
→ version validée
→ publication Rn
→ reprise des modifications
```

Le bouton Publier reste disponible sur une version validée.

## Livrable

```text
EZScore_R15_EDITORIAL_NOTE_VISIBILITY.py
```

## Mise à jour locale

Depuis la racine du dépôt local :

```bat
cd /d H:\EZScore
git pull
copy /Y EZScore_R15_EDITORIAL_NOTE_VISIBILITY.py EZScore.py
python -m py_compile EZScore.py
```

Adapter uniquement le chemin local si EZScore n'est pas installé dans `H:\EZScore`.

## Base de reprise suivante

```text
EZScore_R15_EDITORIAL_NOTE_VISIBILITY.py
```
