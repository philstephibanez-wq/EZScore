# EZScore — R5.2 ergonomie ancres + scrollbar

Patch volontairement limité aux templates de l'éditeur visuel.

## Modifications

### Déplacement d'une ancre

- clic droit maintenu sur une ancre ;
- glisser horizontalement ;
- l'ancre suit la souris ;
- au relâchement, elle se recale sur le beat ou la frontière de mots la plus proche ;
- le timestamp technique n'est jamais modifié ;
- l'ancre reste un overlay éditorial ;
- pendant le déplacement, un libellé indique le temps et le type de snap.

Renommage : double-clic inchangé.
Suppression : sélectionner l'ancre puis touche `Suppr`.

### Scrollbar

- hauteur portée à 22 px ;
- poignée plus contrastée ;
- hover plus visible ;
- même scrollbar unique pour Sections / Accords / Chant / Chœurs.

### Sauts de ligne

- le marqueur `|` est plus visible ;
- inactif : discret ;
- actif : jaune ;
- aucun vrai retour de ligne n'est appliqué dans la timeline.

## Portée

Uniquement :

- `templates/views/lyrics-editor.css`
- `templates/views/lyrics-editor.js`

Aucun Python modifié.
Aucun player audio modifié.
Aucune persistance modifiée.
Aucun template `.score` modifié.

## Installation

```powershell
cd H:\EZScore

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\EZScore_INLINE_TIMELINE_R5_2.zip" `
  -DestinationPath . `
  -Force

node --check .\templates\views\lyrics-editor.js
git diff --check
git status --short
```

Puis relancer Streamlit et tester dans `Analyse > Paroles`.

## Test ciblé

1. Vérifier que la scrollbar est plus facile à manipuler.
2. Clic droit maintenu sur `Couplet 1`.
3. Glisser l'ancre à gauche/droite.
4. Vérifier le snap au relâchement.
5. Enregistrer.
6. Changer d'onglet puis revenir : position conservée.
7. Cliquer sur plusieurs marqueurs `|`, enregistrer et vérifier leur persistance.
