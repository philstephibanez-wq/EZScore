# EZScore_v1 R41.0K6E — Media auth fix

Base GitHub vérifiée avant génération :

- repository : `philstephibanez-wq/EZScore_v1`
- branch : `master`
- commit : `c6156dc82222ff5f58f154b9a3ebae6668e37b81`
- message : `Mise en place de Caddy`

## Correction

Le `forward_auth` Caddy appelle `/internal/media/auth` après normalisation de l'URI.
Dans la requête Symfony observée, `X-Forwarded-Uri` vaut :

`/song-<id>/<sha256>/playback/run-.../<track>.opus`

et non :

`/media/song-<id>/<sha256>/playback/run-.../<track>.opus`

Le contrôleur rejetait donc toutes les pistes avec HTTP 403.

Ce correctif modifie uniquement :

`src/Controller/InternalMediaAuthController.php`

- regex : suppression du préfixe `/media`
- comparaison du chemin : `ltrim($path, '/')`

`config/routes.yaml` et `config/caddy/Caddyfile` ne sont pas inclus : les corrections précédentes sont déjà présentes dans le commit de base.

## Application

Depuis `H:\EZScore` :

```powershell
tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R41_0K6E_MEDIA_AUTH_FIX.zip" -C H:\EZScore
```

Puis vérifier :

```powershell
php -l .\src\Controller\InternalMediaAuthController.php
php bin\console debug:router | Select-String "app_internal_media_auth|internal/media"
```

Résultat attendu pour la route :

`app_internal_media_auth  GET  /internal/media/auth`

Ensuite recharger la page Stems en DEV puis ONLINE et vérifier que les `.opus` ne répondent plus `403`.
