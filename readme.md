# EZScore_v1 — R34.6 tempo unique + typographie accords

Corrections ciblées sur les deux dernières captures.

## 1. Tempo affiché une seule fois

Le doublon venait de deux renderers JavaScript successifs :

- ancien renderer R34.4 dans `public/assets/js/chordslab.js` ;
- renderer R34.5 dans `public/assets/js/chordslab-r33-1.js`.

R34.6 supprime le renderer R34.4 et garde un seul propriétaire du tempo.

Affichage attendu :

```text
TEMPO
Tempo = 117
```

une seule fois dans le cartouche.

## 2. Accords un peu plus gros

La fondamentale passe à 17 px.

Exemple :

```text
Eadd9
^
E plus gros
add9 plus petit
```

## 3. Petites lettres alignées en bas

Les suffixes `maj`, `add9`, `sus2`, `m7`, etc. sont maintenant alignés sur la même ligne de base que la fondamentale.

`maj` reste plus petit, mais n'est plus en exposant.

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R34_6_TEMPO_TYPOGRAPHY.zip" -C H:\EZScore_v1

H:\EZScore_v1\.venv-py313\Scripts\python.exe .\scripts\apply_r34_6_tempo_typography.py

node --check .\public\assets\js\chordslab.js
node --check .\public\assets\js\chordslab-r33-1.js
php .\tests\r34_6_contract.php
php bin\console lint:twig templates
php bin\console cache:clear
```

Attendu :

```text
9 R34.6 checks passed.
```

Puis `Ctrl+F5`.

Aucune migration et aucune réanalyse harmonique.
