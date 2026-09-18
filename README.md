# EZScore — Lyrics Reflow R1

Base GitHub vérifiée :

```text
dc842bd1bb15147f26c726360ec932c3035c8cde
EZScore_EDITORIAL_FINGERPRINT_RECOVERY_R1
```

Le fichier de départ `templates/views/lyrics-editor.js` correspond exactement
au blob GitHub :

```text
9ead98d9b0c93377ff47ddca221c203af3133436
```

## Problème

L'analyse et les timestamps sont corrects, mais certains mots restent
visuellement superposés dans `Analyse > Paroles`.

La cause est le moment de la mesure de largeur :

```text
onglet Streamlit monté mais caché
→ getBoundingClientRect().width incorrect / trop faible
→ anti-collision calculé une seule fois
→ l'onglet devient visible
→ police et vraie largeur apparaissent
→ les mots se recouvrent
```

## Correction

Aucune donnée d'analyse n'est modifiée.

Le layout des mots est maintenant recalculable :

```text
timestamp
→ X temporel brut
→ mesure de largeur réelle après rendu
→ X visuel = max(X temporel, fin mot précédent + 10 px)
```

Le reflow est déclenché :

```text
- après le premier paint ;
- après le chargement des polices ;
- quand le composant / viewport change de taille ;
- quand l'onglet caché devient effectivement mesurable ;
- après une modification inline d'un mot ;
- au retour de visibilité du document.
```

Les timestamps, beats, accords, anchors et données éditoriales ne changent pas.

Les marqueurs `↵` sont repositionnés après chaque reflow pour rester attachés
au bon mot.

## Fichier modifié

```text
templates/views/lyrics-editor.js
```

Aucun Python n'est modifié.

## Installation

```powershell
cd H:\EZScore

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\EZScore_LYRICS_REFLOW_R1.zip" `
  -DestinationPath . `
  -Force

node --check .\templates\views\lyrics-editor.js

git diff --check
git status --short
```

## Test

1. Redémarrer Streamlit.
2. Ouvrir directement un autre onglet puis revenir sur `Analyse > Paroles`.
3. Vérifier la zone dense autour de `Jolene / I'm begging...`.
4. Modifier un mot en double-clic : le layout doit se recalculer.
5. Vérifier les marqueurs `↵`.
6. Aucun besoin de réanalyse.
