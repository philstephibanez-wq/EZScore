# EZScore — R5.5 interactions souris + scrollbar persistante

Patch limité aux templates de l'éditeur silencieux.

## 1. Déplacement sans clic droit

Le navigateur interceptait le clic droit.

R5.5 utilise désormais le bouton gauche :

- clic gauche court sur une ancre : sélection normale ;
- double-clic sur une ancre : renommage ;
- clic gauche maintenu + déplacement > 5 px : drag de l'ancre ;
- même logique pour le marqueur `↵`.

Le seuil de 5 px évite qu'un simple clic soit interprété comme un déplacement.

## 2. Insertion explicite d'un saut de ligne

La création n'est plus cachée dans un clic sur une zone vide.

- cliquer sur `+ ↵` dans le label `Chant` ;
- la lane passe en mode insertion ;
- cliquer près du mot cible ;
- le `↵` est créé après le mot le plus proche ;
- le mode insertion se désactive automatiquement.

Suppression :
- clic sur `↵` ;
- touche `Suppr`.

Déplacement :
- clic gauche maintenu + glisser ;
- snap après le mot le plus proche.

## 3. Scrollbar toujours visible

La timeline utilise maintenant `overflow-x: scroll` et réserve en permanence
l'espace de la scrollbar.

Pour Chrome/Edge :
- track visible en permanence ;
- thumb visible en permanence ;
- contraste renforcé ;
- hauteur 22 px ;
- poignée minimale 90 px.

Pour Firefox :
- `scrollbar-color` est défini.

## Portée

Uniquement :

- `templates/views/lyrics-editor.html`
- `templates/views/lyrics-editor.css`
- `templates/views/lyrics-editor.js`

Aucun Python.
Aucune donnée/persistance.
Aucun player.
Aucun template `.score`.

## Installation

```powershell
cd H:\EZScore

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\EZScore_INLINE_TIMELINE_R5_5.zip" `
  -DestinationPath . `
  -Force

node --check .\templates\views\lyrics-editor.js
git diff --check
git status --short
```

## Test ciblé

1. Ouvrir `Analyse > Paroles`.
2. Vérifier que la scrollbar reste visible sans survol.
3. Cliquer `+ ↵`.
4. Cliquer après/près de `dove`.
5. Vérifier qu'un `↵` apparaît après `dove`.
6. Clic gauche maintenu sur `↵`, déplacer de plus de 5 px, relâcher.
7. Vérifier le snap après le nouveau mot.
8. Clic sur `↵`, touche `Suppr`.
9. Clic gauche maintenu sur une ancre, déplacer, relâcher.
10. Double-clic sur une ancre : renommage.
11. Enregistrer, changer d'onglet, revenir : persistance.
