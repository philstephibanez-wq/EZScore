# R38.0a — correctif installateur regex

Le R38.0 échouait car `re.sub()` interprétait les backslashes du texte de remplacement.
R38.0a utilise une fonction de remplacement (`lambda`) : les `\s`, `\d`, etc. restent littéraux.

Commandes :

```powershell
cd H:\EZScore_v1
tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_0A_INSTALLER_REGEX_FIX.zip" -C H:\EZScore_v1
python .\scripts\install_r38.py H:\EZScore_v1
python -m py_compile .\analysis\lyrics_timeline_analysis.py
php .\tests\r38_0a_contract.php H:\EZScore_v1
php bin\console cache:clear
git diff --check
git status --short
```

Attendu :
`R38_0A_INSTALL_OK`
`R38_0A_CONTRACT_OK`

Ensuite Ctrl+F5 puis relancer Analyser les paroles.
