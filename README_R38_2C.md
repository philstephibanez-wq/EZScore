# R38.2C — premier mot + destinataire admin centralisé

## Premier mot
- suppression totale des ancres `replace` de `SequenceMatcher`;
- seuls les blocs exacts >= 2 mots créent normalement une ancre;
- avant la première ancre acoustique fiable, `start_ms` reste `null`;
- les mots non ancrés ne sont plus sérialisés comme `start_ms=0`;
- donc une intro instrumentale reste vide au lieu d'afficher `Je` au premier beat.

Il faut relancer **Analyser les paroles** après installation.

## Tous les mails adressés à l'admin
Un service central `AdminRecipientResolver` devient la source de vérité :
- il prend le premier utilisateur créé ayant `ROLE_ADMIN`;
- c'est l'admin créé lors du first-run;
- `MAILER_FROM` reste uniquement l'expéditeur;
- plus de destinataire admin provenant d'une variable `EZSCORE_ADMIN_CONTACT_EMAIL`.

Audit du code actuel :
- `RegistrationMailer`: destinataire = utilisateur en cours d'inscription, donc inchangé;
- `EventMailer`: destinataire = invité, donc inchangé;
- `SongPublicationMailer`: destinataires = utilisateurs abonnés, donc inchangé;
- `Contact admin` (y compris catégories/rapports d'erreurs envoyés à l'admin) passe par `AdminRecipientResolver`;
- Monolog actuel écrit les erreurs dans les fichiers de logs et n'a aucun handler email.

Le test `admin_mail_audit.php` échoue s'il reste une ancienne variable/adresse admin dans `src`.

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_2C_ADMIN_RECIPIENT_FIRST_WORD.zip" -C H:\EZScore_v1

python .\scripts\install_r38_2c.py H:\EZScore_v1

python -m py_compile .\analysis\lyrics_timeline_analysis.py

php -l .\src\Service\AdminRecipientResolver.php
php -l .\src\Controller\ContactController.php
php -l .\src\Domain\User\UserRepository.php

php .\tests\r38_2c_contract.php H:\EZScore_v1
php .\tests\admin_mail_audit.php H:\EZScore_v1

php bin\console cache:clear

git diff --check
git status --short
```

Attendu :
```text
R38_2C_INSTALL_OK
R38_2C_CONTRACT_OK
ADMIN_MAIL_AUDIT_OK
```

Puis :
1. `Ctrl+F5`
2. relancer **Analyser les paroles**
3. tester un mail/rapport adressé à l'admin
