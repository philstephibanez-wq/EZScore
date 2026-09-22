# EZScore_LYRICS_VALIDATE_PLAYER_R1

Base distante vérifiée :

```text
master = 21e051ad58f1e0ed890fbd7afdebe973299b0ec5
EZScore_ANALYSIS_PLAYER_R1b
```

## Corrections

1. Bouton explicite `💾 Valider les paroles`.
2. Le bloc validé est persisté (fichier + SQLite) et rechargé à l'ouverture.
3. Migration automatique des anciennes paroles depuis `lyric_block_edits`, puis `analyses.whisper_json`, puis `analysis_versions.whisper_json`.
4. L'alignement est désactivé tant que les modifications du bloc ne sont pas validées.
5. MMS_FA ne supprime plus `structure_analysis.json` : la timeline beats+accords reste disponible pour le lecteur STEM.
6. La timeline musicale est reconstruite dès que les STEM sont prêts, même si les paroles ne sont pas encore alignées.

## Application

```powershell
cd H:\EZScore

tar -xf "$env:USERPROFILE\Downloads\EZScore_LYRICS_VALIDATE_PLAYER_R1.zip" -C H:\EZScore

.\.venv-py313\Scripts\python.exe .\scripts\apply_lyrics_validate_player_r1.py

.\.venv-py313\Scripts\python.exe -m py_compile `
  .\ezscore\analysis\forced_lyrics.py `
  .\ezscore\integration\choir_pipeline.py `
  .\scripts\test_lyrics_validate_player_r1_contract.py

.\.venv-py313\Scripts\python.exe .\scripts\test_lyrics_validate_player_r1_contract.py
```

Attendu :

```text
PATCH OK
LYRICS VALIDATE PLAYER R1 CONTRACT OK
```

Redémarrer Streamlit ensuite. Aucune régénération STEM n'est nécessaire.
