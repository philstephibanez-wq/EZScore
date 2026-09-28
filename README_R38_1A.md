# R38.1a — hotfix JS

R38.1 contenait une regex JavaScript sur-échappée :
`/^\\[([^\\]]+)\\]$/`

Le navigateur levait une SyntaxError au chargement du fichier JS, donc plus rien n'était rendu.

R38.1a :
- corrige la regex ;
- conserve le ruban accords `Em - - -` ;
- conserve les paroles avec prélecture ;
- conserve le diagramme optionnel ;
- conserve la navigation sections ;
- force un nouveau cache-buster `r38_1a`.

Le JS a été validé avec `node --check` avant packaging.

Installation :

```powershell
cd H:\EZScore_v1
tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_1A_JS_REGEX_HOTFIX.zip" -C H:\EZScore_v1
python .\scripts\install_r38_1a.py H:\EZScore_v1
php .\tests\r38_1a_contract.php H:\EZScore_v1
php bin\console cache:clear
git diff --check
git status --short
```

Attendu :
`R38_1A_INSTALL_OK`
`R38_1A_CONTRACT_OK`

Puis `Ctrl+F5`.
