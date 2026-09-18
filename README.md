# EZScore — R5.4 sauts de ligne manipulables

Patch ergonomique limité aux templates de l'éditeur silencieux.

## Nouveau comportement des sauts de ligne

Les anciens petits traits/potentiels marqueurs après chaque mot disparaissent.

Désormais :

- aucun marqueur n'est affiché s'il n'existe pas réellement ;
- clic dans la lane `Chant` à l'endroit souhaité :
  création d'un saut de ligne `↵` ;
- le saut se cale après le mot le plus proche ;
- clic droit maintenu + glisser sur `↵` :
  déplacement du saut ;
- au relâchement :
  snap après le mot valide le plus proche ;
- pendant le déplacement :
  affichage `↵ après <mot>` ;
- clic simple sur `↵` :
  sélection ;
- touche `Suppr` :
  suppression du saut.

Le saut reste stocké uniquement comme :

```text
line_break_after_lead = [index_mot, ...]
```

Aucun timestamp n'est modifié.

## Cohérence avec les ancres

Même convention :
- édition directe dans la timeline ;
- clic droit + glisser = déplacement ;
- snap à une cible valide ;
- persistance uniquement après `Enregistrer`.

## Portée

Uniquement :

- `templates/views/lyrics-editor.html`
- `templates/views/lyrics-editor.css`
- `templates/views/lyrics-editor.js`

Aucun Python.
Aucune persistance modifiée.
Aucun player audio.
Aucun template `.score`.

## Contrôles

`node --check templates/views/lyrics-editor.js` : requis avant test.

## Installation

```powershell
cd H:\EZScore

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\EZScore_INLINE_TIMELINE_R5_4.zip" `
  -DestinationPath . `
  -Force

node --check .\templates\views\lyrics-editor.js
git diff --check
git status --short
```

## Test ciblé

1. Ouvrir `Analyse > Paroles`.
2. Vérifier qu'il n'y a plus de `|` gris après chaque mot.
3. Cliquer dans la lane Chant entre deux zones de texte.
4. Vérifier l'apparition d'un `↵` jaune après le mot le plus proche.
5. Clic droit maintenu + glisser sur `↵`.
6. Vérifier le changement de cible pendant le drag.
7. Relâcher : le `↵` doit rester après le nouveau mot.
8. Sélectionner `↵`, touche `Suppr` : disparition.
9. Créer plusieurs sauts.
10. `Enregistrer`.
11. Changer d'onglet / revenir : persistance.
12. Revalider le déplacement des ancres et la scrollbar R5.2.
