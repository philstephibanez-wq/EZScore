# R37.0d — Worker Lyrics dispatch

Le backend crée bien les jobs `lyrics`, mais le Worker stable les ignorait encore :

```text
Job #55 ignoré: kind=lyrics
```

Ce correctif ajoute uniquement le dispatch Lyrics dans `_run_job()`.

Il ne remplace pas `_run_chord_job()` et ne modifie pas `_read_progress()`.

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R37_0D_WORKER_LYRICS_DISPATCH_FIX.zip" -C H:\EZScore_v1

python .\scripts\apply_r37_0d.py H:\EZScore_v1

python -m py_compile .\worker_app\ezscore_analysis_worker.pyw
python -m py_compile .\worker_app\lyrics_worker_r37.py

php .\tests\r37_0d_contract.php H:\EZScore_v1

Select-String -Path .\worker_app\ezscore_analysis_worker.pyw `
  -Pattern 'kind"\) == "lyrics"|lyrics_worker_r37|def _read_progress'

git diff --check
git status --short
```

Attendu :

```text
R37_0D_APPLIED_OK
R37_0D_CONTRACT_OK
```

Puis relancer le Worker et cliquer de nouveau sur **Extraire les paroles**.
