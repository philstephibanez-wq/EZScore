# EZScore_v1 — R34.5 hard fix

R34.4 n'était pas un livrable source correct : le ZIP ne contenait que le script/test/readme alors que j'avais annoncé trois fichiers source. C'est la raison pour laquelle les captures ne montraient pratiquement aucun changement.

R34.5 corrige ce point.

## Fichiers réellement livrés

Le ZIP contient directement :

```text
public/assets/js/chordslab-r33-1.js
translations/stems.fr.yaml
```

Puis le script modifie réellement :

```text
public/assets/css/chordslab.css
templates/song/chordslab.html.twig
```

Le template passe les versions d'assets à `r34_5`, afin d'éliminer l'ancien JS/CSS mis en cache.

## Corrections

- fondamentale des accords riches : taille fixe ;
- seul `maj` est très petit ;
- `Afficher les accords guitare` sur une ligne sur PC ;
- auto-scroll uniquement pendant Play ;
- Pause / Stop : scroll manuel libre ;
- affichage du tempo sous la forme `Tempo = 60` ;
- correction de la traduction manquante `stems.mixer.reset`.

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R34_5_HARD_FIX.zip" -C H:\EZScore_v1

H:\EZScore_v1\.venv-py313\Scripts\python.exe .\scripts\apply_r34_5_hard_fix.py

node --check .\public\assets\js\chordslab-r33-1.js
php .\tests\r34_5_contract.php
php bin\console lint:yaml translations
php bin\console lint:twig templates
php bin\console cache:clear

git status --short -- public\assets\css\chordslab.css public\assets\js\chordslab-r33-1.js templates\song\chordslab.html.twig translations\stems.fr.yaml
```

Attendu :

```text
11 R34.5 checks passed.
```

et Git doit montrer les quatre fichiers source modifiés.

Ensuite `Ctrl+F5`.

Aucune migration et aucune réanalyse harmonique.
