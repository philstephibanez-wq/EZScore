# EZScore_v1 — R34.2 affichage accords / diagrammes enrichis

Ce livrable affine ChordsLab sur trois points :

1. **Lisibilité des accords riches**
   - `Gmaj7` s’affiche maintenant avec **G** à taille normale ;
   - seule la portion `maj` est réduite ;
   - le suffixe reste lisible dans le prompteur et au-dessus du diagramme.

2. **Diagrammes enrichis**
   - ajout d’accords enrichis fréquemment rencontrés :
     `maj7`, `add9`, `m7`, `sus2`, `sus4`, `6` pour plusieurs fondamentales ;
   - cela couvre notamment les cas signalés comme `Gmaj7` et `Fadd9`.

3. **Libellé “Afficher les accords guitare” plus propre**
   - présentation en ligne plus compacte ;
   - suppression de l’aspect “empilé / pas propre” du libellé.

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R34_2_CHORD_DISPLAY_POLISH.zip" -C H:\EZScore_v1

H:\EZScore_v1\.venv-py313\Scripts\python.exe .\scripts\apply_r34_2_chord_display_polish.py
php .\tests\r34_2_contract.php
php bin\console cache:clear
```

Attendu :

```text
7 R34.2 checks passed.
```

Puis faire `Ctrl+F5` sur ChordsLab.

## Remarques

- aucun recalcul d’analyse nécessaire ;
- aucune migration ;
- aucun traitement spécifique à **Aline** ;
- ce livrable agit uniquement sur l’affichage / diagrammes de ChordsLab.
