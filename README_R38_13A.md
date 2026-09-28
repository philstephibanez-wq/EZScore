# EZScore_v1 R38.13a — cache Python Lyrics du Worker

Correctif strictement limité à `worker_app/lyrics_worker_r37.py`.

Il conserve les modifications locales R38.13 déjà installées. Il ne touche ni à l'analyse syllabique, ni à LyricsLab, ni à ChordsLab, ni au player, ni à la base.

## Correction

Le Worker avait déjà validé :

`H:\EZScore\.venv-py313\Scripts\python.exe · NVIDIA GeForce RTX 2060`

puis relançait un probe lourd `import torch, whisper` avant chaque job avec un timeout de 20 s.

R38.13a :
- met en cache l'interpréteur Lyrics validé pendant toute la vie du Worker ;
- réutilise ce cache pour les jobs suivants ;
- porte le probe initial de 20 s à 60 s ;
- invalide le cache uniquement si l'interpréteur ne peut plus être lancé ;
- ne fait aucun fallback CPU.

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_13A_WORKER_LYRICS_PYTHON_CACHE.zip" -C H:\EZScore_v1

python .\scripts\install_r38_13a_worker_python_cache.py H:\EZScore_v1

php .\tests\r38_13a_worker_cache_contract.php H:\EZScore_v1

python -m py_compile .\worker_app\lyrics_worker_r37.py
```

Attendu :

```text
R38_13A_WORKER_CACHE_OK
R38_13A_INSTALL_OK
R38_13A_WORKER_CACHE_CONTRACT_OK
```

Puis fermer complètement et redémarrer le Worker desktop.

Premier job Lyrics de la session :

```text
Python Lyrics: H:\EZScore\.venv-py313\Scripts\python.exe · NVIDIA GeForce RTX 2060
```

Jobs suivants de la même session :

```text
Python Lyrics (cache): H:\EZScore\.venv-py313\Scripts\python.exe · NVIDIA GeForce RTX 2060
```

Ne pousse pas encore.
