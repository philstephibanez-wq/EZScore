# R38.4A — priorité MAIL + PAROLES

Ce hotfix ne touche ni au player ni à la barre de progression.

## Paroles

Les jobs #68/#69/#70 sortent immédiatement avec `lyrics_python_exit_1` après R38.4.
R38.4A rend le patch sûr :

- le module complet est compilé avant écriture ;
- si la syntaxe est invalide, le fichier utilisateur n'est pas remplacé ;
- le premier chant est cherché chronologiquement par **groupe de mots**, pas par un mot isolé ;
- un `Je` halluciné à `t=0` ne suffit pas ;
- le premier groupe réel (`Je vous parle...`) reçoit directement les timestamps Whisper ;
- l'alignement global commence ensuite depuis cette ancre, donc un refrain répété plus loin ne peut plus voler le début ;
- `align` reste sur la source/original, exactement la même horloge que le player ;
- le worker conserve les dernières lignes du sous-processus Python : un prochain échec donnera le vrai message au lieu de seulement `lyrics_python_exit_1`.

## Mail admin / erreurs

Le code Symfony commité n'a pas de mailer automatique d'erreur distinct : `Contact admin` utilise déjà `AdminRecipientResolver` et Monolog écrit dans les fichiers de log.

Le Gmail erroné provient donc d'une configuration/runtime legacy ou d'un reporter externe/ancien. R38.4A ajoute :

```text
php bin\console ezscore:admin-mail-sync
```

Cette commande :

- résout l'adresse du premier `ROLE_ADMIN` créé ;
- synchronise les variables legacy `ADMIN/ERROR` dans `.env.local` sur cette adresse ;
- ne modifie jamais `MAILER_FROM`.

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_4A_MAIL_LYRICS_PRIORITY_FIX.zip" -C H:\EZScore_v1

python .\scripts\install_r38_4a.py H:\EZScore_v1

python -m py_compile .\analysis\lyrics_timeline_analysis.py
python -m py_compile .\worker_app\lyrics_worker_r37.py

php -l .\src\Command\AdminMailSyncCommand.php
php .\tests\r38_4a_contract.php H:\EZScore_v1

php bin\console cache:clear
php bin\console ezscore:admin-mail-sync

git diff --check
git status --short
```

Attendu :

```text
R38_4A_INSTALL_OK
R38_4A_CONTRACT_OK
ADMIN_MAIL_SYNC_OK
Admin first-run: ... <ADRESSE_ADMIN_ATTENDUE>
```

**Vérifier cette adresse.** Si la ligne affiche le Gmail indésirable, alors le premier `ROLE_ADMIN` en base n'est pas le compte attendu et il faut corriger la donnée plutôt que masquer le problème.

Ensuite redémarrer le worker permanent et relancer `Analyser les paroles`.
