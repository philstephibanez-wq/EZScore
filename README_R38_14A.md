# EZScore_v1 — R38.14a Contact LogAndPlay

Correctif UX léger après R38.14.

## Modification
- Le gros formulaire n'est plus inséré dans le Répertoire.
- Ajout d'un lien discret **Contacter LogAndPlay** dans l'entête public.
- Le lien ouvre une page de contact dédiée, cohérente avec la page de connexion.
- Le formulaire garde CSRF, honeypot, délai 60 s et envoi vers l'administrateur.
- Le bandeau **Site en développement** et le verrouillage des inscriptions restent inchangés.

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_14A_CONTACT_HEADER.zip" -C H:\EZScore_v1

python .\scripts\install_r38_14a_contact_header.py H:\EZScore_v1

php .\tests\r38_14a_contract.php H:\EZScore_v1
php -l .\src\Controller\ContactController.php

php bin\console cache:clear
php bin\console cache:warmup
php bin\console debug:router | Select-String "contact-public"
```

Puis `Ctrl+F5`.
