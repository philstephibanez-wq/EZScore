# EZScore — R5.6 insertion de saut par clic long

Patch limité aux templates de l'éditeur silencieux.

## Comportement retenu

Le bouton `+ ↵` est supprimé.

Dans la lane `Chant` :

- clic court sur un mot : comportement normal ;
- double-clic : édition du texte ;
- clic long (~475 ms) sans déplacement notable :
  insertion d'un saut `↵` après ce mot ;
- déplacement > 4 px avant le délai :
  annule l'insertion ;
- si un saut existe déjà après ce mot :
  aucun doublon n'est créé.

Pour un `↵` existant :

- clic court : sélection ;
- clic gauche maintenu + glisser :
  déplacement avec snap après le mot le plus proche ;
- `Suppr` :
  suppression.

Pour les ancres :

- clic gauche maintenu + glisser :
  déplacement ;
- double-clic :
  renommage.

La scrollbar R5.5 reste visible en permanence.

## Portée

Uniquement :

- `templates/views/lyrics-editor.html`
- `templates/views/lyrics-editor.css`
- `templates/views/lyrics-editor.js`

Aucun Python.
Aucune donnée/persistance.
Aucun player.
Aucun template `.score`.
Aucun changement des timestamps techniques.

## Installation

```powershell
cd H:\EZScore

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\EZScore_INLINE_TIMELINE_R5_6.zip" `
  -DestinationPath . `
  -Force

node --check .\templates\views\lyrics-editor.js
git diff --check
git status --short
```

## Test ciblé

1. Ouvrir `Analyse > Paroles`.
2. Vérifier qu'il n'y a plus de bouton `+ ↵`.
3. Maintenir le clic gauche ~0,5 s sur un mot.
4. Vérifier l'apparition de `↵` après ce mot.
5. Refaire un clic long sur le même mot : aucun doublon.
6. Déplacer `↵` au clic gauche maintenu.
7. Sélectionner `↵`, puis `Suppr`.
8. Double-cliquer un mot : édition toujours fonctionnelle.
9. Déplacer une ancre : fonctionnement R5.5 conservé.
10. Vérifier que la scrollbar reste visible.
11. Enregistrer, changer d'onglet, revenir : persistance.
