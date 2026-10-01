# R38.4B — récupération de l'analyseur LyricsLab

Cause exacte de l'échec R38.4A : `re.sub()` traitait le code Python injecté comme une chaîne de remplacement regex. Les séquences `\\r` et `\\n` du motif de section ont donc été transformées en vrais retours de ligne, ce qui produisait :

```text
SyntaxError: unterminated string literal
```

R38.4B utilise une fonction `lambda` comme remplacement. Les backslashes restent littéraux et le fichier complet est compilé avant écriture.

## Commandes

```powershell
cd H:\\EZScore_v1

tar -xf "$env:USERPROFILE\\Downloads\\EZScore_v1_R38_4B_CORRUPTED_ANALYZER_RECOVERY.zip" -C H:\\EZScore_v1

python .\\scripts\\install_r38_4b.py H:\\EZScore_v1
python -m py_compile .\\analysis\\lyrics_timeline_analysis.py
python -m py_compile .\\worker_app\\lyrics_worker_r37.py
php -l .\\src\\Command\\AdminMailSyncCommand.php
php .\\tests\\r38_4b_contract.php H:\\EZScore_v1
php bin\\console cache:clear
php bin\\console ezscore:admin-mail-sync
git diff --check
git status --short
```

Attendu :

```text
R38_4B_INSTALL_OK
R38_4B_CONTRACT_OK
ADMIN_MAIL_SYNC_OK
Admin first-run: ... <ADRESSE ADMIN ATTENDUE>
```

Vérifier impérativement la ligne `Admin first-run:`. Si elle affiche le Gmail incorrect, ne pas considérer le routage mail comme corrigé : cela indique que le résolveur admin renvoie le mauvais compte en base.

Ensuite redémarrer le worker permanent et relancer `Analyser les paroles`.
