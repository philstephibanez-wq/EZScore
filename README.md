# EZScore_FIRST_RUN_WEB_R2_1

Correction du test Windows de `EZScore_FIRST_RUN_WEB_R2`.

## Pourquoi le test affichait FIRST RUN OK puis plantait

Le scénario fonctionnel était déjà validé.

Le `WinError 32` venait du nettoyage du fichier SQLite temporaire. Plusieurs
fonctions EZScore ouvrent leurs propres connexions SQLite ; sous Windows,
certains handles peuvent rester vivants jusqu'à la fin du processus Python.

Fermer uniquement la connexion créée directement par le test ne garantit donc
pas que tous les handles internes sont déjà libérés.

## Correction

Le test utilise maintenant deux processus :

1. le processus enfant crée/teste la BDD temporaire ;
2. il se termine ;
3. Windows libère tous les handles SQLite du processus enfant ;
4. le processus parent supprime le dossier temporaire.

Aucune modification applicative supplémentaire.

## Installation

```powershell
cd H:\EZScore

tar -xf "$env:USERPROFILE\Downloads\EZScore_FIRST_RUN_WEB_R2_1.zip" -C H:\EZScore

.\.venv-py313\Scripts\python.exe -m py_compile `
  .\scripts\test_first_run_db.py
```

Puis :

```powershell
.\.venv-py313\Scripts\python.exe .\scripts\test_first_run_db.py
```

Résultat attendu :

```text
FIRST RUN OK
...
temporary DB cleanup: OK
```
