# R37.0h — correctif installateur Analyze Lyrics

R37.0g a échoué uniquement dans son script d'installation (`re.PatternError: bad escape \\A`).

R37.0h applique le même correctif fonctionnel sans ce défaut :
- **Analyser les paroles** utilise un POST HTML natif ;
- la textarea est envoyée comme `lyrics_source` ;
- le contrôleur persiste le texte ;
- il crée explicitement un job `lyrics` avec `mode=align` ;
- l'intercepteur submit JavaScript est supprimé.

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R37_0H_ANALYZE_INSTALLER_FIX.zip" -C H:\EZScore_v1

python .\scripts\apply_r37_0h.py H:\EZScore_v1

php -l .\src\Controller\SongLabController.php
php bin\console cache:clear
php bin\console lint:twig templates
php .\tests\r37_0h_contract.php H:\EZScore_v1

git diff --check
git status --short
```

Attendu : `R37_0H_APPLIED_OK` puis `R37_0H_CONTRACT_OK`.

Après `Ctrl+F5`, cliquer **Analyser les paroles** puis vérifier :

```powershell
php bin\console doctrine:query:sql --force-fetch "
SELECT id,kind,status,progress,request_data
FROM analysis_jobs
WHERE song_id=9
ORDER BY id DESC
LIMIT 5
"
```

La première ligne doit contenir `"mode":"align"`.
