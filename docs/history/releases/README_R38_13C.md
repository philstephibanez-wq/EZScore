# EZScore_v1 — R38.13c HOTFIX restauration accords

Correctif local, non poussé.

## Régression corrigée

R38.13b a introduit une erreur JavaScript runtime dans `buildChords()` :

```js
left=xBeat(i)
```

alors que le fichier est en `'use strict'`.

Résultat :
- `chordLane.innerHTML=''` était exécuté ;
- puis `ReferenceError: left is not defined` ;
- la ligne d'accords restait vide ;
- les paroles et le diagramme continuaient à fonctionner, ce qui correspond exactement aux vidéos Aline et La Bohème.

R38.13c restaure :

```js
const left=xBeat(i)
```

Aucune modification de l'analyse, des paroles, du Worker ou de la projection continue R38.13b.

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_13C_RESTORE_CHORDS_HOTFIX.zip" -C H:\EZScore_v1

python .\scripts\install_r38_13c_restore_chords.py H:\EZScore_v1

php .\tests\r38_13c_contract.php H:\EZScore_v1
node .\tests\test_r38_13c_runtime.js H:\EZScore_v1
node --check .\public\assets\js\lyricslab-r37.js

php bin\console cache:clear
php bin\console cache:warmup
```

Attendu :

```text
R38_13C_JS_OK
R38_13C_TWIG_OK
R38_13C_INSTALL_OK
R38_13C_RESTORE_CHORDS_CONTRACT_OK
R38_13C_CHORD_RUNTIME_DECLARATION_OK
```

Puis `Ctrl+F5`.

Aucune réanalyse n'est nécessaire.
