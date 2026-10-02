# EZScore ROLE_DISPLAY R1A — persistence hotfix

Corrige la persistance du rôle `ROLE_DISPLAY`.

Le premier contrat vérifiait seulement la présence textuelle de `ROLE_DISPLAY`. Ce hotfix vérifie maintenant le comportement réel :

- `User::setRoles(['ROLE_DISPLAY'])`
- `User::getPrimaryRole() === 'ROLE_DISPLAY'`
- `UserManager::ROLES` accepte `ROLE_DISPLAY`
- filtre rôle Admin accepte `ROLE_DISPLAY`

Aucune migration DB n'est requise : les rôles sont stockés en JSON.
