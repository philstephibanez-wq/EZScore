# EZScore_AUTH_NATIVE_DIAG_R1

Diagnostic natif Streamlit/OIDC. Aucun F12 nécessaire.

Ce livrable ne change pas la logique d'authentification, la création des
sessions ni le logout.

## Ajouts dans `Compte EZScore`

Le panneau `Diagnostic session / persistance` affiche désormais :

- `_streamlit_user` : PRESENT / ABSENT
- `_streamlit_user_tokens` : PRESENT / ABSENT
- `st.user` : connecté / non connecté
- `redirect_uri`
- présence du `cookie_secret`
- empreinte SHA-256 courte du `cookie_secret`
- noms des cookies liés à Streamlit/user/token

Aucune valeur de cookie, aucun token brut et aucun secret OAuth n'est affiché.

## Installation

```powershell
cd H:\EZScore

tar -xf "$env:USERPROFILE\Downloads\EZScore_AUTH_NATIVE_DIAG_R1.zip" -C H:\EZScore

.\.venv-py313\Scripts\python.exe -m py_compile `
  .\ezscore\auth\diagnostics.py `
  .\scripts\test_auth_native_streamlit_diag.py

.\.venv-py313\Scripts\python.exe .\scripts\test_auth_native_streamlit_diag.py
```

Attendu :

```text
AUTH NATIVE STREAMLIT DIAGNOSTIC OK
mode: read-only
native cookies: names only
cookie_secret: SHA-256 fingerprint only
authentication logic: unchanged
```

## Test

1. relancer EZScore ;
2. ouvrir `Connexion / inscription` ;
3. capturer le bloc `OIDC natif Streamlit`.

Interprétation :

- `_streamlit_user` ABSENT :
  le navigateur/Streamlit ne conserve pas le cookie natif OIDC.
- `_streamlit_user` PRESENT + `st.user` non connecté :
  le cookie est présent mais n'est pas accepté/restauré.
- `_streamlit_user` PRESENT + `st.user` connecté :
  Streamlit restaure correctement l'OIDC ; le défaut est dans EZScore.

L'empreinte `cookie_secret` permet aussi de vérifier qu'elle reste identique
entre deux relances, sans exposer le secret.
