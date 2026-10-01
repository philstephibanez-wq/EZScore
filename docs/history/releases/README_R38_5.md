# EZScore_v1 R38.5 — première syllabe audible + mail admin

Priorité : paroles + mail d'erreur admin.

## Paroles

Aucun traitement spécifique à une chanson.

Règle générique :
1. parcourir les mots reconnus dans l'audio strictement dans l'ordre chronologique ;
2. refuser un mot isolé comme ancre ;
3. accepter le premier petit groupe vocal cohérent ;
4. copier directement ses timestamps absolus ;
5. n'autoriser l'alignement global qu'après ce point ;
6. poursuivre ensuite vers l'avant.

Le script d'installation sait réparer le fichier `lyrics_timeline_analysis.py` déjà cassé par R38.4/A.

## Mail admin

Deux commandes :

```powershell
php bin\console ezscore:admin-mail-sync
php bin\console ezscore:admin-mail-audit
```

La synchronisation utilise `AdminRecipientResolver`, donc le premier `ROLE_ADMIN` créé.
L'audit affiche uniquement les adresses et masque DSN/secrets.

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_5_LYRICS_ONSET_ADMIN_MAIL.zip" -C H:\EZScore_v1

python .\scripts\install_r38_5.py H:\EZScore_v1
python -m py_compile .\analysis\lyrics_timeline_analysis.py
python -m py_compile .\worker_app\lyrics_worker_r37.py

php -l .\src\Command\AdminMailSyncCommand.php
php -l .\src\Command\AdminMailAuditCommand.php
php .\tests\r38_5_contract.php H:\EZScore_v1

php bin\console cache:clear
php bin\console ezscore:admin-mail-sync
php bin\console ezscore:admin-mail-audit

git diff --check
git status --short
```

Attendu :

```text
R38_5_INSTALL_OK
R38_5_CONTRACT_OK
ADMIN_MAIL_SYNC_OK
Admin first-run: ... <ADRESSE ADMIN ATTENDUE>
ADMIN_MAIL_AUDIT_OK
```

Ensuite redémarrer le worker desktop et relancer `Analyser les paroles`.
