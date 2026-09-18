# EZScore — Lyrics Reflow R1.1

Correctif immédiat de `EZScore_LYRICS_REFLOW_R1`.

## Erreur corrigée

```text
BidiComponentError:
Failed to execute 'observe' on 'ResizeObserver':
parameter 1 is not of type 'Element'
```

Cause :

Dans un composant Streamlit Bidi, `root` peut être un `ShadowRoot` ou un
`DocumentFragment`. Ce n'est donc pas obligatoirement un `Element`, alors que
`ResizeObserver.observe()` exige strictement un `Element`.

Le code R1 faisait :

```javascript
observer.observe(root);
observer.observe(viewport);
```

R1.1 fait désormais :

```javascript
observer.observe(viewport);

if (root?.host instanceof Element) {
    observer.observe(root.host);
}
```

`viewport` est l'élément concret dont la taille pilote le reflow. Si `root` est
un `ShadowRoot`, son `host` est observé en complément.

Aucune analyse, donnée éditoriale, timeline ou timestamp n'est modifié.

## Fichiers

```text
templates/views/lyrics-editor.js
readme.md
```

## Installation

```powershell
cd H:\EZScore

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\EZScore_LYRICS_REFLOW_R1_1.zip" `
  -DestinationPath . `
  -Force

node --check .\templates\views\lyrics-editor.js

git diff --check
git status --short
```

Redémarrer ensuite Streamlit et rouvrir `Analyse > Paroles`.
