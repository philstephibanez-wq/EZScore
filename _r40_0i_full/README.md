# EZScore_v1 — R40.0I FULL SERVER CONTROL + SPLASH

Base GitHub exacte: `f1f226ae8b9a8c19de0deeddc4fc94485c011bc7` (`r40_0b_dual_server_control_contract`).

Infrastructure verrouillée:
- Cloudflare/public -> 8501
- gateway ONLINE -> 8501
- backend Symfony ONLINE interne -> 8511
- LOCAL DEV privé -> 8502

Ce FULL corrige:
- verrous séparés état / ONLINE / LOCAL;
- démarrage PowerShell supervisé par Popen + timeout 15 s;
- état ATTENTE SERVEUR;
- gateway v3 + maintenance observée;
- splash piloté par l'état Worker, sans délai fixe de 2 s;
- ancien argument HTA -Port 8501 supprimé.

Installation:
```powershell
cd H:\EZScore_v1
tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R40_0I_FULL_SERVER_CONTROL_SPLASH.zip" -C H:\EZScore_v1
H:\EZScore\.venv-py313\Scripts\python.exe .\_r40_0i_full\scripts\apply_r40_0i_full.py H:\EZScore_v1
```

Attendu:
`R40_0I_FULL_SERVER_CONTROL_SPLASH_INSTALL_OK`

Puis seulement:
```powershell
H:\EZScore\.venv-py313\Scripts\python.exe .\_r40_0i_full\tests\r40_0i_full_contract.py H:\EZScore_v1
git diff --check
git status --short
```

Attendu:
`R40_0I_FULL_SERVER_CONTROL_SPLASH_CONTRACT_OK`
