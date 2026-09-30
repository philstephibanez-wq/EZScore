# EZScore_v1 — R40.0K FULL UTF-8 BOM SPLASH

Base GitHub exacte : `50d20748f151c5f047f2b7c6ad09122bc5c2b92d` (`EZScore_v1_R40_0J_FULL_NO_AUTO_BROWSER_UTF8_SPLASH`).

## Correction

Le problème restant n'était plus la lecture JSON : le HTA R40.0J lit déjà le statut avec
`ADODB.Stream` en UTF-8. Le problème est l'interprétation des **sources elles-mêmes**
par Windows PowerShell 5.1 / MSHTML.

Ce FULL écrit explicitement avec BOM UTF-8 :

- `scripts/launch_ezscore_backend.ps1`
- `EZScore-Launcher.hta`

Les contrats R40.0J restent inchangés :

- aucune page web ouverte automatiquement ;
- boutons **Ouvrir** uniquement ;
- lecture JSON du splash en UTF-8 ;
- gestion ONLINE/LOCAL intacte.

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R40_0K_FULL_UTF8_BOM_SPLASH.zip" -C H:\EZScore_v1

H:\EZScore\.venv-py313\Scripts\python.exe .\_r40_0k_full\scripts\apply_r40_0k_full.py H:\EZScore_v1
```

Attendu :

`R40_0K_FULL_UTF8_BOM_SPLASH_INSTALL_OK`

Si cette ligne n'apparaît pas : STOP.

Puis seulement :

```powershell
H:\EZScore\.venv-py313\Scripts\python.exe .\_r40_0k_full\tests\r40_0k_full_contract.py H:\EZScore_v1

git diff --check
git status --short
```

Attendu :

`R40_0K_FULL_UTF8_BOM_SPLASH_CONTRACT_OK`

Le test contrôle les octets `EF BB BF` au début des deux fichiers et plusieurs chaînes
accentuées représentatives (`Vérification`, `persistés`, `nécessaires`, `état`, `prêt`, `Échec`).
