# EZScore_STREAMLIT_WATCHER_OFF_R1

Base GitHub vérifiée avant livraison :

```text
master = 11c96a732092a931abca45199535f8cddca0293c
```

## Objet

Désactivation permanente du file watcher Streamlit afin d'éviter les warnings
répétés produits par l'introspection de Torchaudio :

```text
streamlit\watcher\local_sources_watcher.py
Torchaudio's I/O functions now support per-call backend dispatch...
```

Configuration ajoutée :

```toml
[server]
fileWatcherType = "none"
```

## Effet

Cette option désactive uniquement la surveillance automatique des fichiers Python.

Elle ne désactive pas :
- les `st.rerun()`,
- les boutons/widgets Streamlit,
- l'analyse audio,
- Torch/Torchaudio,
- le player.

Conséquence : si un fichier Python est modifié pendant qu'EZScore tourne,
l'application ne se recharge plus automatiquement. Un redémarrage manuel est requis.

## Application

```powershell
cd H:\EZScore

tar -xf "$env:USERPROFILE\Downloads\EZScore_STREAMLIT_WATCHER_OFF_R1.zip" -C H:\EZScore

Get-Content .\.streamlit\config.toml

.\.venv-py313\Scripts\python.exe -m streamlit run EZScore.py `
  --server.address 127.0.0.1 `
  --server.port 8501 `
  --server.headless true
```

La ligne de commande n'a plus besoin de :

```text
--server.fileWatcherType none
```

car la valeur est désormais persistée dans `.streamlit/config.toml`.
