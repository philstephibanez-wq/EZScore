# EZScore_v1

EZScore_v1 est l'application Symfony/jQuery d'édition et de publication de partitions synchronisées, pilotée par un Worker Python local pour les analyses audio.

## Architecture active

- Symfony + jQuery : interface, backoffice, catalogue et workflow.
- Worker Python local : stems, accords HQ, tonalité, paroles et traitements asynchrones.
- ONLINE public : façade `8501`, backend Symfony interne `8511`.
- LOCAL DEV privé : `8502`.
- Worker : cible ONLINE ou LOCAL indépendamment.
- Environnement Python projet : `.venv-py313`.
- Accélération GPU requise pour les traitements prévus en CUDA ; pas de fallback CPU silencieux.

## Workflow fonctionnel

`IMPORT -> STEMS -> CHORDS -> LYRICS -> KARAOKE`

Les composants de lecture, timeline, seek, vitesse, mixer stems, accords et paroles doivent rester synchronisés sur la timeline canonique.

## Répertoires principaux

- `analysis/` : traitements audio Python.
- `worker_app/` : Worker desktop et contrôle des serveurs.
- `src/` : code Symfony.
- `templates/` : vues Twig.
- `public/` : assets et point d'entrée public.
- `migrations/` : migrations Doctrine.
- `tests/` : tests permanents du projet.
- `docs/` : documentation consolidée et contrats.
- `scripts/` : uniquement scripts encore utiles au projet ; les installateurs de livraison ne doivent plus y être déposés.

## Documentation

Voir `docs/README.md`.

## Règle de livraison

Les futurs ZIP, installateurs, tests de livraison et fichiers de travail doivent être extraits/exécutés depuis `H:\temp`, jamais dans `H:\EZScore_v1`.

À chaque livraison, les caches Symfony `dev` et `prod` doivent être vidés explicitement.

## Données locales

Les fichiers de runtime, caches, uploads, bases SQLite locales et environnement Python ne sont pas des sources Git et ne doivent pas être supprimés par un nettoyage documentaire.
