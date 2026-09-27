# EZScore_v1 — R35.4a HOTFIX

Ce hotfix s’applique **après R35.4**.

Il corrige quatre points :
1. les routes `ContactController` et `SongCollaborationController` manquantes ;
2. le lien **Contacter l’admin** passe dans l’entête globale pour tout utilisateur connecté ;
3. le lease d’un job `running` est rafraîchi par le heartbeat du Worker même si son pourcentage n’évolue pas ;
4. la file du Worker affiche `EN COURS` pour le job réellement possédé localement.

Le point 3 est important : sans ce heartbeat de lease, une étape longue restant au même pourcentage plus de 120 s pouvait être requeue alors que Python travaillait encore.

## Installation PowerShell

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R35_4a_HOTFIX.zip" -C H:\EZScore_v1

python .\EZScore_v1_R35_4a_HOTFIX\scripts\apply_r35_4a.py H:\EZScore_v1

php bin\console cache:clear
php bin\console lint:container
php bin\console lint:twig templates

php bin\console debug:router | findstr /I "contact collaborator"

php .\EZScore_v1_R35_4a_HOTFIX\tests\r35_4a_contract.php H:\EZScore_v1
python -m py_compile .\worker_app\ezscore_analysis_worker.pyw

git diff --check
git status --short
```

Attendu :
- `R35_4A_APPLIED_OK`
- `R35_4A_CONTRACT_OK`
- routes `app_contact_admin`, `app_song_collaborators`, `app_song_collaborator_add`, `app_song_collaborator_remove`.

Aucun commit/push n’est effectué par le script.
