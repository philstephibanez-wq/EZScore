# EZScore_ANALYSIS_PLAYER_R1b

R1a s'est arrêté atomiquement avant toute écriture.

## Cause exacte

`stem_analysis_conductor.py` ne contient pas littéralement :

```javascript
let duration = 0;
```

Cette ligne appartient à `base._PLAYER_JS` et n'existe qu'à l'exécution de
Python après :

```python
_JS = base._PLAYER_JS
```

R1a cherchait donc le texte au mauvais niveau.

R1b injecte maintenant un `_replace_once()` sur `_JS` juste après
`_JS = base._PLAYER_JS`.

L'application reste atomique : aucun des trois fichiers originaux n'est
remplacé tant que tous les patchs et la validation syntaxique ne sont pas OK.

## Application

```powershell
cd H:\EZScore

tar -xf "$env:USERPROFILE\Downloads\EZScore_ANALYSIS_PLAYER_R1b.zip" -C H:\EZScore

.\.venv-py313\Scripts\python.exe .\scripts\apply_analysis_player_r1b.py

.\.venv-py313\Scripts\python.exe -m py_compile `
  .\ezscore\analysis\forced_lyrics.py `
  .\ezscore\integration\choir_pipeline.py `
  .\ezscore\player\stem_analysis_conductor.py `
  .\scripts\test_analysis_player_r1b_contract.py

.\.venv-py313\Scripts\python.exe .\scripts\test_analysis_player_r1b_contract.py
```

Attendu :

```text
PATCH OK
 - application atomique validée
 ...
ANALYSIS PLAYER R1b CONTRACT OK
```

Ne pas faire de `git pull`, `reset` ou `restore`.
