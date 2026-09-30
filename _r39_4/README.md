# EZScore_v1 — R39.4 Worker resilience

Base GitHub vérifiée avant génération :

`d40edd0272852717999cfed480398abbf1735661`
`EZScore_v1_R39_3A_MODAL_HIDDEN`

Ce lot ne touche qu'au Worker desktop.

## R39.4

- heartbeat HTTP en erreur => état `RECONNEXION`, pas crash ;
- retry avec backoff 1 s -> 15 s ;
- reconnexion via `/hello` ;
- détection explicite du cache Symfony incohérent ;
- message court au lieu du HTML Symfony brut ;
- timeout de claim protégé : ne tue plus le Worker ;
- lecture de queue : log limité ;
- aucune popup Windows pour ces pannes HTTP transitoires ;
- bouton `Arrêter serveur` refusé pendant un job actif ;
- arrêt serveur : attente de la fin réelle du serveur HTTP ;
- démarrage automatique : attente jusqu'à 20 s avant de démarrer le Worker.

Les erreurs réellement fatales (token absent, CUDA absente, FFmpeg absent, etc.)
conservent la popup existante.

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R39_4_WORKER_RESILIENCE.zip" -C H:\EZScore_v1

H:\EZScore\.venv-py313\Scripts\python.exe .\_r39_4\scripts\apply_r39_4.py H:\EZScore_v1

H:\EZScore\.venv-py313\Scripts\python.exe .\_r39_4\tests\r39_4_worker_resilience_contract.py H:\EZScore_v1

H:\EZScore\.venv-py313\Scripts\python.exe -m py_compile .\worker_app\ezscore_analysis_worker.pyw

git diff --check
git status --short
```

Attendu :

```text
R39_4_WORKER_RESILIENCE_INSTALL_OK
R39_4_WORKER_RESILIENCE_CONTRACT_OK
```

## Test manuel

1. Démarrer EZScore Analysis.
2. Vérifier `Connexion EZScore établie`.
3. Sans job actif, arrêter puis redémarrer le serveur depuis l'UI.
4. Le Worker doit passer par `RECONNEXION` puis revenir à `CONNECTÉ`.
5. Pendant un job, `Arrêter serveur` doit être refusé.
6. Un heartbeat HTTP temporairement en erreur ne doit plus afficher la popup brute ni tuer le thread Worker.
