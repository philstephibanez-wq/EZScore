# EZScore_v1 — R38.14b Secure Public Contact

Ce patch complète R38.14/R38.14a.

- `Contacter LogAndPlay` devient réellement public dans `security.yaml`.
- Google reste strictement réservé aux comptes existants : aucun auto-enregistrement.
- Honeypot conservé.
- Cloudflare Turnstile ajouté et validé côté serveur.
- Limitation serveur persistante :
  - IP : 3 / 15 min, 10 / jour ;
  - e-mail : 3 / 15 min, 5 / jour ;
  - global : 20 / heure, 50 / jour.
- Fail closed : sans Turnstile valide ou sans stockage du limiteur, aucun e-mail n'est envoyé.

Le limiteur écrit dans `var/security/public-contact-rate.json`.

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_14B_SECURE_PUBLIC_CONTACT.zip" -C H:\EZScore_v1

python .\scripts\install_r38_14b_secure_public_contact.py H:\EZScore_v1

php .\tests\r38_14b_contract.php H:\EZScore_v1
php -l .\src\Controller\ContactController.php
php -l .\src\Service\TurnstileVerifier.php
php -l .\src\Service\PublicContactRateLimiter.php

php bin\console cache:clear
php bin\console cache:warmup
php bin\console debug:router | Select-String "contact-public|connect/google"
```

## Cloudflare Turnstile

Créer un widget Turnstile pour le domaine EZScore puis ajouter dans `.env.local` :

```dotenv
TURNSTILE_SITE_KEY=VOTRE_SITE_KEY
TURNSTILE_SECRET_KEY=VOTRE_SECRET_KEY
```

Ne jamais pousser `.env.local`.

Pour localhost uniquement, Cloudflare fournit les clés de test officielles :

```dotenv
TURNSTILE_SITE_KEY=1x00000000000000000000AA
TURNSTILE_SECRET_KEY=1x0000000000000000000000000000000AA
```

Puis :

```powershell
php bin\console cache:clear
php bin\console cache:warmup
```

et `Ctrl+F5`.
