# EZScore_LYRICS_DB_SOURCE_R1

Base GitHub vérifiée :

```text
master = d6f8f57559296b71573fdaf789cfc5828350eaa2
EZScore_LYRICS_VALIDATE_PLAYER_R1
```

## Principe

Le bloc `Texte exact du chant` est maintenant piloté par la BDD.

```text
SQLite user_lyrics_sources
        ↓
textarea
        ↓
💾 Valider les paroles
        ↓
UPDATE/INSERT SQLite
        ↓
relecture SQLite
        ↓
confirmation UI
```

`lyrics_input.txt` reste uniquement un miroir technique.

## Correction du champ vide

Si Streamlit conserve un `session_state` vide alors que SQLite contient le
texte, le textarea est réhydraté depuis la BDD.

Les données déjà diagnostiquées existent :

```text
f7759e... -> 776 caractères en BDD
cd8e46... -> 2105 caractères en BDD
```

Il ne faut donc rien ressaisir.

## Application

```powershell
cd H:\EZScore

tar -xf "$env:USERPROFILE\Downloads\EZScore_LYRICS_DB_SOURCE_R1.zip" -C H:\EZScore

.\.venv-py313\Scripts\python.exe .\scripts\apply_lyrics_db_source_r1.py

.\.venv-py313\Scripts\python.exe -m py_compile `
  .\ezscore\analysis\forced_lyrics.py `
  .\ezscore\integration\choir_pipeline.py `
  .\scripts\test_lyrics_db_source_r1_contract.py

.\.venv-py313\Scripts\python.exe .\scripts\test_lyrics_db_source_r1_contract.py
```

Attendu :

```text
PATCH OK
 - SQLite = source de vérité du bloc de paroles
 - lyrics_input.txt = miroir technique seulement
 - textarea hydraté depuis SQLite
 - session_state vide ne masque plus la BDD
 - validation relit la BDD avant confirmation

LYRICS DB SOURCE R1 CONTRACT OK
```

Puis redémarrer Streamlit.

Cette livraison ne touche pas au conducteur STEM. On le corrige séparément
après validation définitive du chargement BDD du bloc de paroles.
