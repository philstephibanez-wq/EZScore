# EZScore_ANALYSIS_LAZY_R1b

R1 s'arrêtait à tort sous Windows parce qu'il comparait le SHA Git aux octets
du worktree, donc CRLF pouvait changer le hash sans aucun `git diff`.

R1b vérifie désormais le blob de l'index Git (`git ls-files -s`) et l'absence
de modification locale (`git diff --quiet`).

Application :

```powershell
cd H:\EZScore
tar -xf "$env:USERPROFILE\Downloads\EZScore_ANALYSIS_LAZY_R1b.zip" -C H:\EZScore

.\.venv-py313\Scripts\python.exe .\scripts\apply_analysis_lazy_r1b.py

.\.venv-py313\Scripts\python.exe -m py_compile `
  .\EZScore.py `
  .\ezscore\ui\stem_lab_analysis.py `
  .\scripts\test_analysis_lazy_r1b_contract.py

.\.venv-py313\Scripts\python.exe .\scripts\test_analysis_lazy_r1b_contract.py
```

Aucun `git pull`, `reset` ou `restore` n'est nécessaire.
