# EZScore_FIX_AUTH_CHOIRS_R1

Base vérifiée :

```text
Repo    : philstephibanez-wq/EZScore
Branche : restore/full-reanalysis-r1
HEAD    : e3262b88b2de5c61dcb9a58b3b804541d325ca7e
```

## Périmètre strict

Cette livraison corrige uniquement les deux régressions signalées :

1. **BDD neuve : création du premier administrateur**
2. **Analyse fraîche : disparition totale des Chœurs**

Elle ne touche pas aux blocs, au Player sync, à `visualDelay`, au MIDI, à SQLite existante ni à l'algorithme validé `VOCAL_OVERLAP_MATCH`.

## AUTH

Une BDD de comptes vide passe maintenant obligatoirement par l'écran de création du premier administrateur avant toute résolution OIDC/session.

Le bootstrap automatique via `EZSCORE_ADMIN_*` n'est plus exécuté au démarrage. La fonction serveur reste disponible dans `storage.py` pour une récupération explicite.

Après création de l'admin et déconnexion, l'onglet **Créer un compte** reste disponible pour l'inscription d'un nouvel utilisateur `reader`.

## Chœurs

Le moteur Chant/Chœurs de la référence stable `0d86dd13` est toujours présent dans le code actuel.

Cette livraison garantit que, sur une analyse fraîche, le second Whisper du stem vocal produit `whisper_vocals_small.json` dès que les STEM et la transcription originale sont disponibles. Le Player et l'éditeur réutilisent ensuite ce cache avec le moteur existant `VOCAL_OVERLAP_MATCH`.

## Installation

```powershell
Remove-Item H:\temp\EZScore_FIX_AUTH_CHOIRS_R1 -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force H:\temp\EZScore_FIX_AUTH_CHOIRS_R1 | Out-Null
Expand-Archive -Path "$env:USERPROFILE\Downloads\EZScore_FIX_AUTH_CHOIRS_R1.zip" -DestinationPath H:\temp\EZScore_FIX_AUTH_CHOIRS_R1 -Force
python "H:\temp\EZScore_FIX_AUTH_CHOIRS_R1\apply.py" --repo H:\EZScore
```

## Contrôle

```powershell
cd H:\EZScore
git diff --check
git status --short
git diff -- ezscore/auth/ui.py ezscore/auth/session.py ezscore/ui/stem_lab_analysis.py
python -m streamlit run .\EZScore.py
```

Le script ne pousse rien sur GitHub.
