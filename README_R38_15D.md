# R38.15d — Force asset refresh

Le texte exact de la capture (`Restaurer cette version complète des paroles ?`) prouve que l'ancien JavaScript R38.15 est encore exécuté.

R38.15c modifiait le fichier JS mais ne changeait pas son URL dans le template. Un cache navigateur, serveur ou CDN peut donc continuer à servir l'ancienne version.

R38.15d force une nouvelle URL :

- `lyrics-history-r38-15.js?v=20260929r38_15d`
- `lyrics-history-r38-15.css?v=20260929r38_15d`

Le test vérifie aussi qu'aucun `confirm()`, `alert()` ou `prompt()` natif ne subsiste dans ce module.

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_15D_FORCE_ASSET_REFRESH.zip" -C H:\EZScore_v1

python .\scripts\install_r38_15d_force_asset_refresh.py H:\EZScore_v1

php .\tests\r38_15d_force_asset_refresh_contract.php H:\EZScore_v1

php bin\console cache:clear
php bin\console cache:warmup

git status --short
```

Ensuite recharge simplement LyricsLab. Le nouveau `?v=...r38_15d` suffit à contourner le cache.
