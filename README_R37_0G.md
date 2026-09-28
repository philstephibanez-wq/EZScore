# R37.0g — Analyze Lyrics native POST

Le diagnostic SQL montre qu'aucun job `mode=align` n'est créé. Le problème est donc avant le Worker.

Ce correctif supprime le submit JavaScript asynchrone pour **Analyser les paroles**.

Le bouton fait désormais un POST HTML natif :
- la textarea est envoyée comme `lyrics_source`;
- le contrôleur persiste ce texte;
- puis appelle explicitement `queue(..., 'align')`.

L'auto-save de la box reste disponible, mais n'est plus une dépendance pour lancer l'analyse.

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R37_0G_ANALYZE_NATIVE_POST_FIX.zip" -C H:\EZScore_v1

python .\scripts\apply_r37_0g.py H:\EZScore_v1

php -l .\src\Controller\SongLabController.php
php bin\console cache:clear
php bin\console lint:twig templates

php .\tests\r37_0g_contract.php H:\EZScore_v1

git diff --check
git status --short
```

Attendu :
`R37_0G_APPLIED_OK`
`R37_0G_CONTRACT_OK`

Puis `Ctrl+F5`, cliquer **Analyser les paroles**, et contrôler :

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
