# EZScore_AUTH_DIAG_REMOVE_NAV_SPAN_R1

Objectifs :

1. retirer le diagnostic temporaire d'authentification maintenant que la
   persistance online est validée ;
2. corriger l'affichage littéral :

```html
<span class="eznav-item active">Répertoire</span>
```

## Modifications

- `ezscore/auth/__init__.py`
  - retour au `render_account_page` normal ;
  - aucun appel au diagnostic temporaire.

- `ezscore/ui/responsive.py`
  - intercepte uniquement les spans internes `eznav-item`;
  - force leur rendu HTML au lieu de les afficher comme texte brut ;
  - aucun changement du reste des appels `st.markdown`.

## Nettoyage diagnostic

Le fichier diagnostic temporaire n'est plus importé. Pour le retirer
physiquement du dépôt local :

```powershell
Remove-Item .\ezscore\auth\diagnostics.py -Force -ErrorAction SilentlyContinue
Remove-Item .\scripts\test_auth_diagnostic_contract.py -Force -ErrorAction SilentlyContinue
Remove-Item .\scripts\test_auth_native_streamlit_diag.py -Force -ErrorAction SilentlyContinue
```

## Application

```powershell
cd H:\EZScore

tar -xf "$env:USERPROFILE\Downloads\EZScore_AUTH_DIAG_REMOVE_NAV_SPAN_R1.zip" -C H:\EZScore

Remove-Item .\ezscore\auth\diagnostics.py -Force -ErrorAction SilentlyContinue
Remove-Item .\scripts\test_auth_diagnostic_contract.py -Force -ErrorAction SilentlyContinue
Remove-Item .\scripts\test_auth_native_streamlit_diag.py -Force -ErrorAction SilentlyContinue

.\.venv-py313\Scripts\python.exe -m py_compile `
  .\ezscore\auth\__init__.py `
  .\ezscore\ui\responsive.py `
  .\scripts\test_auth_diag_remove_nav_span.py

.\.venv-py313\Scripts\python.exe .\scripts\test_auth_diag_remove_nav_span.py
```

Attendu :

```text
AUTH DIAGNOSTIC REMOVAL OK
NAV SPAN RENDER CONTRACT OK
scope: eznav-item span only
```

Puis relancer Streamlit.

Vérifications visuelles :

- aucun bloc `Diagnostic session / persistance` dans Compte ;
- plus de chaîne HTML brute `<span ...>Répertoire</span>` ;
- `Répertoire` est rendu normalement.
