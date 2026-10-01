# EZScore_v1 — R38.14 Public development mode

Patch léger pour l'exposition internet actuelle.

## Changements
- Bandeau **Site en développement** sur la page publique.
- Boutons/liens d'inscription neutralisés : **Inscriptions prochainement**.
- `/register` bloqué côté serveur quand l'installation possède déjà un utilisateur.
- Le first-run d'une installation vierge reste intact.
- Google reste réservé aux comptes existants : l'authenticator actuel refuse déjà les comptes inconnus.
- Formulaire **Contacter LogAndPlay** directement sur la page d'accueil/catalogue public.
- Formulaire protégé par CSRF + honeypot + délai de 60 s par session.
- Envoi à l'administrateur via `AdminRecipientResolver`.
- Création d'utilisateurs par l'admin inchangée.

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_14_PUBLIC_DEVELOPMENT_MODE.zip" -C H:\EZScore_v1

python .\scripts\install_r38_14_public_dev_mode.py H:\EZScore_v1

php .\tests\r38_14_contract.php H:\EZScore_v1
php -l .\src\Controller\RegistrationController.php
php -l .\src\Controller\ContactController.php

php bin\console cache:clear
php bin\console cache:warmup
php bin\console debug:router | Select-String "register|contact-public|contact-admin"
```

Puis `Ctrl+F5`.
