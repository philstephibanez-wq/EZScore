# EZScore CAST R1 — fondation protocole-agnostique

Base relue : `b6d2b5c22195626dddf9915854158940c6995efb`

Cette livraison pose **uniquement la fondation côté client** du cast EZScore. Elle ne prétend pas encore implémenter Miracast ou AirPin dans le navigateur.

## Objectif R1

- API unique `window.EZScoreCast`.
- registre de providers.
- provider `native` activé seulement lorsqu'un wrapper/helper expose `window.EZScoreNativeCast`.
- UI `Caster` créée **uniquement si un provider réel est disponible**.
- aucun changement dans AudioEngine, timeline, ChordsLab, LyricsLab, Python ou Symfony métier.
- aucun faux fallback : si aucun provider réel n'est présent, aucun bouton fonctionnel n'est affiché.

## Fichiers livrés

- `public/assets/js/cast/ezscore-cast.js`
- `public/assets/js/cast/ezscore-cast-native-bridge.js`
- `public/assets/js/cast/ezscore-cast-ui.js`
- `public/assets/css/cast/ezscore-cast.css`
- `scripts/install_cast_r1.ps1`
- `tests/cast_r1_contract.php`

Le script d'installation modifie localement `templates/base.html.twig` de manière idempotente pour charger les nouveaux assets.

## Contrat du bridge natif

Un wrapper Android ou helper Windows devra exposer avant le chargement du provider :

```javascript
window.EZScoreNativeCast = {
    available(),
    capabilities(),
    scan(options),
    connect(deviceId, options),
    disconnect(),
    status()
}
```

Les méthodes peuvent retourner une valeur directe ou une Promise. Elles peuvent aussi retourner du JSON sérialisé ; le provider normalise les réponses.

Exemple attendu pour `scan()` :

```json
[
  {
    "id": "receiver-id",
    "name": "Telas T1",
    "transport": "airpin"
  },
  {
    "id": "miracast-id",
    "name": "Projecteur salle",
    "transport": "miracast"
  }
]
```

Aucun transport n'est simulé par JavaScript.

## Installation

Depuis PowerShell :

```powershell
cd H:\EZScore
tar -xf "$env:USERPROFILE\Downloads\EZScore_CAST_R1_FOUNDATION.zip" -C H:\EZScore
```

Puis **une seule commande de mise en place** :

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install_cast_r1.ps1
```

## Premier test

Après installation, exécuter **uniquement** :

```powershell
php .\tests\cast_r1_contract.php
```

Résultat attendu :

```text
CAST_R1_CONTRACT_OK
```

Ne pas enchaîner d'autres tests avant validation de celui-ci.

## Comportement attendu après R1

Dans un navigateur normal, aucun provider natif n'existe encore : **le bouton Caster n'apparaît pas**. C'est volontaire.

Le premier POC fonctionnel suivant est le provider Android ou Windows réel. Il devra fournir l'audio + la vidéo et déclarer explicitement son transport (`airpin`, `miracast`, etc.).

## Non-régression

R1 ne touche pas :

- `public/assets/js/audio/ezscore-audio-engine.js`
- `public/assets/js/audio/ezscore-audio-session.js`
- timeline canonique
- analyse Python
- moteur d'accords
- worker
- Caddy

Le cast est une couche périphérique et ne devient jamais une seconde source de temps ou d'audio EZScore.
