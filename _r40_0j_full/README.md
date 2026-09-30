# EZScore_v1 — R40.0J FULL NO AUTO BROWSER + UTF-8 SPLASH

Base GitHub exacte: `e786dc41269460fda2270ae87c677937484fd429` (`EZScore_v1_R40_0I_FULL_SERVER_CONTROL_SPLASH`).

- aucune page web ouverte automatiquement au lancement ;
- ouverture uniquement via les boutons **Ouvrir** du Worker ;
- correction des caractères du splash via lecture UTF-8 explicite.

```powershell
cd H:\EZScore_v1
tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R40_0J_FULL_NO_AUTO_BROWSER_UTF8_SPLASH.zip" -C H:\EZScore_v1
H:\EZScore\.venv-py313\Scripts\python.exe .\_r40_0j_full\scripts\apply_r40_0j_full.py H:\EZScore_v1
```

Attendu:
`R40_0J_FULL_NO_AUTO_BROWSER_UTF8_SPLASH_INSTALL_OK`

Puis seulement:

```powershell
H:\EZScore\.venv-py313\Scripts\python.exe .\_r40_0j_full\tests\r40_0j_full_contract.py H:\EZScore_v1
git diff --check
git status --short
```

Attendu:
`R40_0J_FULL_NO_AUTO_BROWSER_UTF8_SPLASH_CONTRACT_OK`
