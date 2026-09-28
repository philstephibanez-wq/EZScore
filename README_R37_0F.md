# R37.0f — bouton « Analyser les paroles »

Symptôme :
- la box est remplie ;
- cliquer « Analyser les paroles » ne crée aucun job.

Cause :
le JS interceptait le `submit`, attendait la sauvegarde asynchrone de la box, puis appelait :

```js
e.currentTarget.submit()
```

Après `await`, `Event.currentTarget` n'est plus garanti. Le formulaire n'était donc jamais soumis.

Correction :
le formulaire est mémorisé avant l'`await` :

```js
const form=e.currentTarget;
if(await saveSource()){
    form.submit();
}
```

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R37_0F_ANALYZE_SUBMIT_FIX.zip" -C H:\EZScore_v1

python .\scripts\apply_r37_0f.py H:\EZScore_v1

php bin\console cache:clear
php .\tests\r37_0f_contract.php H:\EZScore_v1

git diff --check
git status --short
```

Attendu :

```text
R37_0F_APPLIED_OK
R37_0F_CONTRACT_OK
```

Faire ensuite un rechargement forcé du navigateur (`Ctrl+F5`) avant de retester.
