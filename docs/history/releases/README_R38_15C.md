# R38.15c — No browser alerts

Remplace les `confirm()` Chrome de l'historique des paroles par une modale EZScore.

Installation :

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_15C_NO_BROWSER_ALERT.zip" -C H:\EZScore_v1

python .\scripts\install_r38_15c_no_browser_alert.py H:\EZScore_v1

php .\tests\r38_15c_no_browser_alert_contract.php H:\EZScore_v1

php bin\console cache:clear
git status --short
```

Puis `Ctrl+F5`.
