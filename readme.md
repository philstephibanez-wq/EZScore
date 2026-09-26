# EZScore_v1 — R34.4 correction réelle CSS + scroll pause + tempo

R34.4 corrige les régressions visibles dans les captures.

## Pourquoi R34.3 n'a pas corrigé l'affichage

La typographie et la grille de réglages sont définies dans `public/assets/css/chordslab.css`. Modifier uniquement le JS secondaire n'était pas suffisant / fiable.

R34.4 modifie donc réellement trois fichiers suivis par Git :

```text
public/assets/css/chordslab.css
public/assets/js/chordslab.js
public/assets/js/chordslab-r33-1.js
```

## Corrections

- fondamentale (`G`, `F`, `E`...) à taille fixe identique, même dans `Gmaj7`, `Fadd9`, `Esus2` ;
- `maj` seul est petit dans `Gmaj7` ;
- fin de la réduction globale `.is-long/.is-very-long` qui réduisait également la fondamentale ;
- `Afficher les accords guitare` occupe une ligne complète et reste sur une seule ligne sur PC ;
- en pause et à l'arrêt, aucun recentrage automatique du prompteur ;
- en lecture, le beat courant reste centré sous le diagramme ;
- ajout du tempo dans le cartouche sous la forme `Tempo = 60` (sans `BPM`).

Le tempo est calculé à partir de la timeline canonique des beats déjà enregistrée. Aucune réanalyse n'est nécessaire.

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R34_4_VISUAL_TEMPO_SCROLL.zip" -C H:\EZScore_v1

H:\EZScore_v1\.venv-py313\Scripts\python.exe .\scripts\apply_r34_4_visual_tempo_scroll.py

node --check .\public\assets\js\chordslab.js
node --check .\public\assets\js\chordslab-r33-1.js
php .\tests\r34_4_contract.php
php bin\console cache:clear

git status --short -- public\assets\css\chordslab.css public\assets\js\chordslab.js public\assets\js\chordslab-r33-1.js
```

Attendu :

```text
8 R34.4 checks passed.
 M public/assets/css/chordslab.css
 M public/assets/js/chordslab.js
 M public/assets/js/chordslab-r33-1.js
```

Puis `Ctrl+F5`.

Aucune migration. Aucune réanalyse.
