# EZScore R35 — Import → Analyse

## Correctif

Un import neuf ne doit pas ouvrir la chanson en mode édition.

Le flux attendu devient :

```text
Import du fichier
    ↓
Chanson
    ↓
Vue = Analyse
Mode = Vue
    ↓
Paramètres d'analyse visibles
    ↓
Appliquer les paramètres
    ↓
Analyse
```

Le correctif est limité à :

```text
ezscore/ui/app_shell.py
```

Aucune modification SQLite.
Aucune modification des données du répertoire.
Aucune modification de `EZScore.py`.

## Traces ajoutées

PowerShell affiche maintenant des lignes telles que :

```text
[EZTRACE][IMPORT] hash=... source=Import target_view=Analyse target_mode=Vue
[EZTRACE][ANALYSIS_UI] section=Chanson hash=... view=Analyse mode=Vue active=True
```

Ces traces servent à la recette et permettent de vérifier le workflow exact.

## Installation PowerShell

Depuis le dossier où le ZIP est décompressé, copier le fichier :

```powershell
cd H:\EZScore
Copy-Item -Force "<DOSSIER_DEZIP>\EZScore_R35_IMPORT_ANALYSE\ezscore\ui\app_shell.py" ".\ezscore\ui\app_shell.py"
```

Puis compiler :

```powershell
python -m py_compile .\ezscore\ui\app_shell.py
python -m py_compile .\EZScore.py
python -m compileall -q .\ezscore
```

Puis lancer :

```powershell
python -m streamlit run .\EZScore.py --server.address 127.0.0.1 --server.port 8501 --server.headless true
```

## Recette — étape suivante

Importer une nouvelle chanson.

Résultat attendu immédiatement après import :

- vue `Analyse` sélectionnée ;
- mode `Vue` ;
- paramètres avancés visibles dans la barre latérale ;
- aucune analyse lancée automatiquement ;
- trace `[EZTRACE][IMPORT] ... target_view=Analyse target_mode=Vue`.
