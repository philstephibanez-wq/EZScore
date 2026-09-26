# EZScore_v1 — R34.3 lisibilité accords + scroll pause + checkbox

Ce correctif remplace directement :

```text
public/assets/js/chordslab-r33-1.js
```

Il ne s'agit pas d'un patcher : après extraction, `git status` doit donc montrer ce fichier modifié.

## Corrections

### 1. Accords riches

Les anciennes règles `.is-long` / `.is-very-long` réduisaient tout le bouton, donc également la fondamentale.

R34.3 neutralise cette réduction globale.

Résultat attendu :

```text
Gmaj7
^
G = même taille que G simple
maj = petit
7 = suffixe lisible
```

Même principe pour `Fadd9`, `Esus2`, etc. : la fondamentale reste visuellement dominante.

### 2. "Afficher les accords guitare"

Le contrôle est forcé sur une ligne propre sur PC :

```text
☑ Afficher les accords guitare
```

Il occupe une ligne complète de la grille de réglages, ce qui évite les trois lignes vues dans R34.2.

Sur petit écran uniquement, le libellé peut revenir à la ligne si la largeur l'impose réellement.

### 3. Scroll du prompteur en pause

Le centrage automatique du beat courant ne fonctionne maintenant que lorsque la lecture est active.

```text
Play  -> suivi automatique sous le diagramme
Pause -> aucun recentrage automatique
Stop  -> aucun recentrage automatique
```

En pause, la barre horizontale peut donc être déplacée manuellement sans revenir à la position courante.

## Diagrammes riches

Les diagrammes enrichis ajoutés en R34.2 restent dans `public/assets/js/chordslab.js` et ne sont pas supprimés par ce correctif.

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R34_3_SCROLL_UI_FIX.zip" -C H:\EZScore_v1

node --check .\public\assets\js\chordslab-r33-1.js
php bin\console cache:clear

git status --short -- public\assets\js\chordslab-r33-1.js
```

La dernière commande doit montrer le fichier comme modifié.

Ensuite :

```text
Ctrl+F5
```

Aucune migration et aucune nouvelle analyse harmonique ne sont nécessaires.
