# EZScore_v1 — R35.4 RECOVERY + COLLAB + CONTACT

Base stricte : `fff8806c6e603e78779790d7c80019c45c54ff95`.

Livré : récupération automatique des jobs `running` orphelins après 120 s ; propriété éditoriale conservée dans `Song.editor` ; collaborateurs multiples ; seul le propriétaire ou l’admin modifie la délégation ; détection de doublon exact SHA-256 puis probable titre+artiste ; formulaire authentifié de contact admin, journalisé en base, Symfony Mailer, anti-spam 60 s ; destination via `EZSCORE_ADMIN_CONTACT_EMAIL` (par défaut `xpertdev@hotmail.com`).

La future review détaillée des modifications d’un collaborateur (diff + accepter/refuser) n’est pas simulée : R35.4 pose le modèle de délégation correct sur lequel elle s’appuiera.

## Installation PowerShell

```powershell
cd H:\EZScore_v1
git rev-parse HEAD
# attendu fff8806c6e603e78779790d7c80019c45c54ff95

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R35_4_RECOVERY_COLLAB_CONTACT.zip" -C H:\EZScore_v1
python .\EZScore_v1_R35_4_RECOVERY_COLLAB_CONTACT\scripts\apply_r35_4.py H:\EZScore_v1

php bin\console doctrine:migrations:migrate --no-interaction
php bin\console cache:clear
php bin\console lint:container
php bin\console lint:twig templates
php bin\console debug:router | findstr /I "contact collaborators desktop_job_queue"
php .\EZScore_v1_R35_4_RECOVERY_COLLAB_CONTACT\tests\r35_4_contract.php H:\EZScore_v1
python -m py_compile .\worker_app\ezscore_analysis_worker.pyw
git diff --check
git status --short
```

Attendu : `R35_4_APPLIED_OK` et `R35_4_CONTRACT_OK`.

Vérifiez `MAILER_DSN` dans `.env.local` avant de tester l’envoi réel. Le script ne committe ni ne pousse rien.
