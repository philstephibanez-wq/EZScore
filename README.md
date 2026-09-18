# EZScore — R5.10 correction ciblée de la représentation des accords

La signature n'est plus affichée dans `Analyse > Paroles`.

Aucun badge, aucun champ, aucun choix.

En revanche, toute la logique d'affichage dépendante de la signature est
conservée.

## Pourquoi R5.9 pouvait rester faux

Le player Analyse et l'éditeur Paroles restent montés en parallèle dans les
onglets Streamlit. Quand la signature change dans le player, Paroles n'est pas
forcément rerendu.

R5.10 relit périodiquement la même valeur utilisée par le player Analyse. Si
elle change, seule la lane Accords est recalculée.

Exemple :

```text
Analyse = 2/4  -> Paroles : Gm-  A-  Cm- ...
Analyse = 4/4  -> Paroles : Gm---  Gm-A. ...
```

## Portée

Uniquement :
- `templates/views/lyrics-editor.html`
- `templates/views/lyrics-editor.css`
- `templates/views/lyrics-editor.js`

Aucun Python.
Aucun player.
Aucune persistance.
Aucun template `.score`.

## Installation

```powershell
cd H:\EZScore

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\EZScore_INLINE_TIMELINE_R5_10.zip" `
  -DestinationPath . `
  -Force

node --check .\templates\views\lyrics-editor.js
git diff --check
git status --short
```

## Test ciblé

1. Dans le player Analyse, choisir `2/4`.
2. Aller dans Paroles.
3. Aucune signature ne doit être visible.
4. Les accords doivent être groupés par 2 beats.
5. Revenir au player, choisir `4/4`.
6. Revenir dans Paroles.
7. Les accords doivent passer à 4 positions.
