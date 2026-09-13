# EZScore R28 — page compte, inscription, profil et SSO fiabilisé

R28 remplace la petite barre de connexion R26/R27 par une vraie page Compte inspirée d'un portail musical moderne.

## Interface
- entrée `Compte` dans la navigation ;
- page dédiée Connexion / Créer un compte ;
- boutons Google, Réseaux sociaux et Apple ;
- login e-mail / mot de passe ;
- inscription locale autonome en rôle `reader` ;
- profil utilisateur avec nom affiché, rôle, méthode de connexion, identités liées et changement de mot de passe ;
- Déconnexion toujours visible dans l'en-tête quand un utilisateur est connecté ;
- administration des utilisateurs conservée pour `admin`.

## Régression Google / invalid_client
R28 refuse désormais de lancer le SSO si `secrets.toml` contient encore une valeur d'exemple.
Le bouton est désactivé et indique précisément ce qui manque.

Pour Google, le vrai `client_id` doit venir de Google Auth Platform et l'URI autorisée doit être exactement :

```text
https://ezscore.logandplay.com/oauth2callback
```

## Configuration
Copier :

```powershell
Copy-Item .streamlit\secrets.toml.example .streamlit\secrets.toml
```

Puis remplacer les valeurs d'exemple par les vraies valeurs Google/Auth0/Apple.

Le vrai `.streamlit/secrets.toml` est ignoré par Git.

## Authlib
Le warning de dépréciation `httpx -> httpx2` d'Authlib est filtré côté application afin de ne plus polluer le démarrage EZScore.

## Responsive
La page Compte utilise des colonnes qui s'empilent sur smartphone, des boutons pleine largeur et des cibles tactiles adaptées tablette/mobile.

## Fichiers R28
- `EZScore.py`
- `readme.md`
- `.gitignore`
- `.streamlit/secrets.toml.example`
- `requirements-auth.txt`
- `ezscore/auth/__init__.py`
- `ezscore/auth/storage.py`
- `ezscore/auth/session.py`
- `ezscore/auth/ui.py`
