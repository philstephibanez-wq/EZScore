# EZScore_v1 — R40.0B DUAL SERVER CONTROL UI

Base GitHub **obligatoire et vérifiée par l'installateur** :

`ab8714d6acc63f10df2d09baed89ab4aa0a5f23d`
`EZScore_v1_R39_5_FULL_LYRICS_DIAGRAM_AND_CATALOG_FIX`

Ce lot est complet. Il ne dépend d'aucun R40 précédent.

## Contrat R40.0B

### Serveur ONLINE
- exposition publique sur `127.0.0.1:8501` via une passerelle stable ;
- backend Symfony ONLINE sur `127.0.0.1:8511` ;
- environnement `prod` ou `dev` ;
- changement `prod <-> dev` : relance automatique du backend ONLINE ;
- pendant la relance, la passerelle reste active et sert la page de maintenance ;
- maintenance indépendante de l'environnement ;
- démarrage / relance / arrêt indépendants du serveur LOCAL ;
- profiler Symfony disponible en environnement `dev` comme prévu par le projet.

### Serveur LOCAL DEV
- serveur distinct sur `127.0.0.1:8502` ;
- environnement `dev` uniquement ;
- démarrage / relance / arrêt indépendants de ONLINE ;
- ONLINE et LOCAL peuvent tourner simultanément.

### Worker
- cible indépendante : `ONLINE` ou `LOCAL` ;
- changement de cible : redémarrage propre du thread Worker ;
- aucune bascule serveur/cible pendant un job actif ;
- CUDA/FFmpeg et la logique de jobs R39.4 sont conservés.

### Persistance
Les choix sont persistés dans :

`var/runtime/ezscore-server-control.json`

Ils sont restaurés au redémarrage du Worker :
- ONLINE ON/OFF ;
- ONLINE maintenance ON/OFF ;
- ONLINE env prod/dev ;
- LOCAL ON/OFF ;
- LOCAL env dev ;
- cible Worker ONLINE/LOCAL.

## Architecture anti-50x lors d'une relance ONLINE

Le port public `8501` n'est plus directement le processus Symfony. Une passerelle locale stable écoute sur 8501 et proxyfie vers le backend ONLINE 8511.

Lors d'un switch `prod/dev` :
1. la passerelle passe automatiquement en maintenance ;
2. le backend 8511 est arrêté ;
3. il redémarre avec le nouvel `APP_ENV` ;
4. le health check `/fr/login` doit répondre ;
5. la passerelle rétablit l'état maintenance choisi avant la relance.

Si le backend tombe, la passerelle renvoie la page de maintenance au public au lieu d'une erreur de proxy. Les endpoints internes du Worker ne sont pas masqués par le mode maintenance.

## Isolation Symfony

`Kernel.php` isole cache et logs pour éviter les collisions entre deux instances simultanées :

- ONLINE : `var/cache/online/<env>` et `var/log/online`
- LOCAL : `var/cache/local/dev` et `var/log/local`
- CLI normal : comportement Symfony historique conservé.

## Installation

Le dépôt doit être revenu au master propre R39.5 FULL.

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R40_0B_DUAL_SERVER_CONTROL_UI.zip" -C H:\EZScore_v1

H:\EZScore\.venv-py313\Scripts\python.exe .\_r40_0b\scripts\apply_r40_0b.py H:\EZScore_v1
```

Attendu :

```text
R40_0B_DUAL_SERVER_CONTROL_INSTALL_OK
```

**Si cette ligne n'apparaît pas : STOP. Ne lancer aucune autre commande.**

Si l'installation est OK :

```powershell
H:\EZScore\.venv-py313\Scripts\python.exe .\_r40_0b\tests\r40_0b_dual_server_control_contract.py H:\EZScore_v1

git diff --check
git status --short
```

Attendu :

```text
R40_0B_DUAL_SERVER_CONTROL_CONTRACT_OK
```

L'installateur exécute déjà :
- `py_compile` sur le Worker et les modules R40 ;
- `php -l src/Kernel.php` ;
- `php bin\console lint:container`.

Aucune route Symfony artificielle n'est ajoutée par ce lot : les health checks utilisent `/fr/login`, déjà existant. Il n'y a donc plus de dépendance au faux contrat `internal_runtime_health` des essais R40 supprimés.

## Premier démarrage

Au premier lancement du Worker R40.0B, s'il trouve l'ancien PID R39 `var/runtime/ezscore-web.pid`, il arrête proprement cette ancienne instance avant de prendre le port 8501 avec la passerelle ONLINE.

## Fichiers applicatifs touchés

Modifiés :
- `worker_app/ezscore_analysis_worker.pyw`
- `scripts/start_ezscore_web.ps1`
- `scripts/launch_ezscore_backend.ps1`
- `src/Kernel.php`

Ajoutés :
- `worker_app/server_control.py`
- `worker_app/online_gateway.py`

Aucune modification des algorithmes d'analyse, des timelines, des players, de Lyrics/Chords ou du catalogue.
