# EZScore — CONCERT SYNC R1 32-bit HOTFIX

Correction ciblée du `HTTP 500` de `POST /api/concert/session` sur PHP Windows 32 bits (`PHP_INT_SIZE=4`).

Cause confirmée : les timestamps Unix en millisecondes (~1.79e12) dépassent `PHP_INT_MAX=2147483647`.

## Installation

Depuis `H:\EZScore` :

```powershell
tar -xf "$env:USERPROFILE\Downloads\EZScore_CONCERT_SYNC_R1_32BIT_HOTFIX.zip" -C H:\EZScore
```

## Test

```powershell
php .\tests\concert_sync_r1_32bit_hotfix_contract.php
```

Résultat attendu :

```text
CONCERT_SYNC_R1_32BIT_HOTFIX_OK
```

Puis validation fonctionnelle sur `http://127.0.0.1:8501/concert/control` : cliquer sur `Créer une session`. Le `HTTP_500` doit disparaître et l'URL d'invitation doit être créée.

## Fichiers modifiés/ajoutés

- `src/Service/ConcertSessionStore.php`
- `tests/concert_sync_r1_32bit_hotfix_contract.php`
- `README_CONCERT_SYNC_R1_32BIT_HOTFIX.md`

Aucun autre fichier n'est modifié.
