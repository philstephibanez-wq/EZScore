# EZScore_v1 — R41.0G Server status stability + CI

Base GitHub exacte : `2ce7da1213788bb8d37c14073001aa872fb024c9` (`EZScore_v1_R41_0F_FULL_LAUNCHER_CI_SEEKER`).

## Correctif état serveurs

R41.0F sondait les endpoints HTTP toutes les 2 secondes avec des timeouts courts.
Un simple retard HTTP pouvait donc faire clignoter l'UI entre `ONLINE/ACTIF`,
`ARRÊTÉ` et `PROTÉGÉ` sans action utilisateur.

R41.0G sépare désormais strictement :

- **processus vivant** = PID/processus Windows ;
- **santé HTTP** = endpoint momentanément joignable.

Contrat UI :
- `ARRÊTÉ` uniquement si le processus correspondant n'existe réellement plus ;
- LOCAL reste `ACTIF` si son PID vit, même lors d'un retard HTTP ;
- 3 échecs HTTP consécutifs avant affichage d'un état dégradé ;
- 2 succès HTTP consécutifs avant retour à l'état sain ;
- aucune action automatique start/stop n'est ajoutée au monitoring ;
- le monitoring reste toutes les 2 secondes.

## CI

Le correctif `.env` de R41.0F fonctionne : le dernier CI passe maintenant la création
du fichier `.env`, mais `composer install` échoue ensuite sur `DEFAULT_URI` absent.

R41.0G ajoute au `.env` CI :
- `DEFAULT_URI=http://localhost`
- `EZ_ANALYSIS_URL=http://127.0.0.1:8502`
- placeholders Turnstile.

## Hors périmètre

Aucune modification :
- analyse accords HQ ;
- tonalité générale ;
- seeker ChordsLab ;
- stems mixer ;
- launcher/splash R41.0F.

## Installation

```powershell
cd H:\EZScore_v1

git status --short
git rev-parse HEAD
```

Attendu : dépôt propre et HEAD `2ce7da1213788bb8d37c14073001aa872fb024c9`.

Puis :

```powershell
tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R41_0G_SERVER_STATUS_STABILITY_CI.zip" -C H:\EZScore_v1

H:\EZScore_v1\.venv-py313\Scripts\python.exe .\_r41_0g_full\scripts\apply_r41_0g.py H:\EZScore_v1
```

Attendu :

`R41_0G_SERVER_STATUS_STABILITY_CI_INSTALL_OK`

Sinon : **STOP**.

Puis seulement :

```powershell
H:\EZScore_v1\.venv-py313\Scripts\python.exe .\_r41_0g_full\tests\r41_0g_contract.py H:\EZScore_v1

git diff --check
git status --short
```

Attendu :

`R41_0G_SERVER_STATUS_STABILITY_CI_CONTRACT_OK`

## Test fonctionnel

Laisser le Worker ouvert au moins 30–60 secondes sans toucher aux boutons.
Les cartes ONLINE/LOCAL ne doivent plus basculer `ARRÊTÉ/ACTIF` sur un simple
timeout HTTP. Un véritable arrêt de processus doit, lui, être reflété immédiatement.
