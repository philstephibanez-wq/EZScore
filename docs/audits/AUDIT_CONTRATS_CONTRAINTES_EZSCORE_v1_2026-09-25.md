# EZScore_v1 — Audit complémentaire : respect des contrats et contraintes

Dépôt audité : philstephibanez-wq/EZScore_v1
Branche : master
Révision de référence : 033d1cccf840e36f9154eb5e0792aaeaa6b9d440
Date : 2026-09-25

## Synthèse

CONFORME :
- séparation Symfony / Python ;
- absence de shell_exec/exec pour appeler Python ;
- statuts chanson séparés des statuts d'analyse ;
- audio privé sous var/storage/audio ;
- formats MP3/WAV/FLAC/M4A/OGG/AAC ;
- import sans lancement Python ;
- pré-écoute locale ;
- droits chanson Editor/Admin ;
- visibilité catalogue Public/Lecteur/Éditeur/Admin ;
- ratings 1–5 avec unicité user/chanson ;
- FR/EN et routes localisées ;
- tri Titre/Interprète + alphabet ;
- migrations suivies ;
- modularité correcte.

NON CONFORME / À CORRIGER :
1. .env.dev contient un vrai APP_SECRET dans un dépôt public.
2. La création de groupe est réservée à ROLE_ADMIN alors que tout utilisateur connecté doit pouvoir créer un groupe.
3. Le créateur d'un groupe n'est pas automatiquement créé comme GroupMember role=owner.
4. Le modèle ne garantit pas qu'un groupe conserve au moins un owner.
5. Les playlists ne contiennent aucune relation vers Song : pas de PlaylistItem, pas de position, pas d'ajout/retrait de chanson.
6. Une cover runtime est versionnée sous public/uploads/covers.
7. Aucun test automatisé exploitable.
8. Aucune CI GitHub Actions visible.
9. Le claim des jobs d'analyse n'est pas atomique ; risque de double claim avec plusieurs workers.
10. L'API d'analyse est HTTP/JSON et le payload est versionné, mais les URI /internal/analysis/... ne sont pas versionnées.
11. Le worker Python réel n'est pas encore implémenté : analysis/app/main.py expose seulement /health.
12. Le modèle Playlist owner_type + owner_id n'a pas de FK et reste fragile.

## Contrats techniques à préserver

- Symfony = sécurité, utilisateurs, chansons, groupes, playlists, publication, persistance, orchestration.
- Python = calcul musical uniquement.
- Communication uniquement HTTP/JSON REST.
- Aucun shell_exec/exec PHP -> Python.
- Aucun audio en base64 JSON.
- Pas de résultats musicaux inventés.
- Contrôles de droits côté serveur, pas uniquement Twig.
- CSRF sur toute mutation web.
- Toute modification Doctrine doit avoir une migration.
- Après modification Doctrine :
  php bin/console doctrine:schema:validate
  php bin/console doctrine:schema:update --dump-sql
  Le second ne doit proposer aucun SQL inattendu.
- Logs, cache, audio runtime et médias utilisateur ne doivent pas être versionnés.
- ZIP de livraison avec seulement les fichiers modifiés + readme.md.
- L'utilisateur pousse lui-même sur GitHub.

## Contrats métier audités

### Chansons
CONFORME :
- statuts imported/analyzed/editing/published ;
- Analyzed non sélectionnable à l'import ;
- signatures auto, 2/4, 3/4, 4/4, 5/4, 6/8, 9/8, 12/8 ;
- capo 0..11 ;
- Editor modifie uniquement ses chansons ;
- Admin peut tout modifier et réaffecter l'éditeur ;
- remplacement audio conserve la même entité Song et repasse à Imported.

PARTIEL :
- historique audio stocké en JSONL, pas encore comme vrai modèle de versions relationnel.

### Visibilité
CONFORME :
- Public/Lecteur : publiées uniquement ;
- Éditeur : ses chansons + publiées des autres ;
- Admin : toutes.

NON IMPLÉMENTÉ COMPLÈTEMENT :
- lecteur MP3 complet ;
- karaoké complet ;
- preview karaoké 20 s.
Les droits sont déjà calculés, mais pas encore le player/timeline final.

### Groupes
NON CONFORME :
- tout utilisateur connecté devrait pouvoir créer ;
- créateur devrait devenir owner ;
- invariant “au moins un owner” absent.

CONFORME :
- rôles owner/manager/member ;
- owner/manager peuvent administrer ;
- seul owner/Admin peut supprimer.

### Playlists
CONFORME :
- playlist personnelle ;
- playlist de groupe ;
- visibilité groupe ;
- gestion par owner/manager.

NON CONFORME :
- aucune chanson dans playlist ;
- aucun ordre de playlist ;
- owner_type/owner_id sans FK.

### Rating
CONFORME :
- 1 à 5 ;
- une note par user/chanson ;
- mise à jour et suppression.

## Écarts entre recette.md et code actuel

Ces points de recette échoueront tant que le dépôt n'est pas corrigé :
- Lecteur connecté peut créer un groupe.
- Éditeur peut créer un groupe.
- Créateur devient propriétaire.
- Ajout chanson dans playlist personnelle.
- Retrait chanson dans playlist personnelle.
- Ajout/retrait chanson dans playlist de groupe.
- Délégation fine par capacité, si elle doit aller au-delà de owner/manager/member.

## Nettoyage à valider puis appliquer

Candidats morts / historiques :
- assets/css/app.css
- assets/js/app.js
- public/assets/js/interaction-feedback.js
- translations/messages.r741.fr.yaml
- translations/messages.r741.en.yaml
- src/Controller/.gitignore
- src/Entity/.gitignore
- src/Repository/.gitignore
- translations/.gitignore
- migrations/.gitignore

Runtime à sortir de Git :
- public/uploads/covers/386a4a4b2114af0e503a8fe6fbcfc533.jpg

À ajouter au .gitignore :
/public/uploads/*
!/public/uploads/.gitkeep

## Ordre d'action confirmé

1. Sécurité Git / rotation APP_SECRET.
2. Nettoyage des fichiers morts + runtime Git.
3. Groupes : création tous users + owner automatique + invariant owner.
4. PlaylistItem : vraie relation Playlist ↔ Song + position + droits.
5. Tests + CI.
6. Recette exhaustive.
7. Python REST :
   - routes/versionnement figés ;
   - claim atomique ;
   - lease/heartbeat ;
   - retry/timeout ;
   - cancel ;
   - contrat source audio ;
   - worker réel ;
   - résultats persistés/versionnés.

## Conclusion

Le dépôt respecte déjà la majorité des contraintes structurantes. Les écarts contractuels sérieux sont concentrés sur :
- secret Git ;
- groupes ;
- contenu des playlists ;
- tests/CI ;
- robustesse future du worker d'analyse.

Ces points doivent être corrigés avant de considérer le socle Symfony comme totalement stabilisé.
