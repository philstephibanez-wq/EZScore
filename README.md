# EZScore_GOOGLE_AUTH_R1

Base :
- `master`
- commit de départ `208caf2ee402a9ba0a78da36831e13066746be5b`

## Diagnostic

La configuration Google est encore reconnue comme valide : dans l'UI, le bouton
Google n'affichait pas `à configurer` ni de message de configuration invalide.

Le bouton était pourtant désactivé à cause de cette condition :

```python
disabled=not ready or importlib.util.find_spec("authlib") is None
```

Dans le nouvel environnement `.venv-py313`, `authlib` n'était pas déclaré dans
`requirements-analysis-hq.txt`.

## Correction

### requirements-analysis-hq.txt

Ajout :

```text
Authlib==1.8.0
```

Authlib 1.8.0 supporte Python >= 3.10, dont Python 3.13.

### scripts/install_analysis_hq.ps1

Le script vérifie désormais explicitement :

```text
import authlib
Authlib=<version>
```

### ezscore/auth/ui.py

Si la configuration OIDC est correcte mais que la bibliothèque Authlib manque,
l'interface affiche maintenant explicitement :

```text
Bibliothèque Authlib absente de l'environnement Python actif.
```

Le bouton n'est donc plus silencieusement désactivé.

## Installation minimale

Il n'est PAS nécessaire de réinstaller toute la pile GPU pour ce correctif :

```powershell
cd H:\EZScore

tar -xf "$env:USERPROFILE\Downloads\EZScore_GOOGLE_AUTH_R1.zip" -C H:\EZScore

.\.venv-py313\Scripts\python.exe -m pip install Authlib==1.8.0

.\.venv-py313\Scripts\python.exe -c "import authlib; print(authlib.__version__)"

.\.venv-py313\Scripts\python.exe -m py_compile `
  .\ezscore\auth\ui.py
```

Puis redémarrer complètement Streamlit :

```powershell
.\.venv-py313\Scripts\python.exe -m streamlit run EZScore.py
```

Le bouton Google doit redevenir actif si `.streamlit/secrets.toml` contient
toujours la configuration Google locale valide.

Aucun secret n'est ajouté au dépôt.
