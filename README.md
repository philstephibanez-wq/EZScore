# EZScore_VOCALISES_PY313_FIX2

Base GitHub :
- branche `restore/full-reanalysis-r1`
- commit `ac3bc844ad9ff534f2af363b7972d1cd16691164`
- commit utilisateur : `EZScore_PLAYER_SYNC_VOCALISES_PY313`

## Correctifs

1. Python 3.13 / audioop
   - ajout de `audioop-lts>=0.2.2; python_version >= "3.13"`
   - le script d'installation s'arrete maintenant reellement si une commande
     Python ou un import echoue.

2. Vocalises longues
   - le premier correctif utilisait surtout les onsets Librosa principaux ;
   - cette version combine trois indices acoustiques :
     - onset_detect principal,
     - pics de flux spectral plus faibles,
     - attaques positives de l'enveloppe RMS ;
   - seuils adaptes aux syllabes repetees plus douces du stem Choeurs ;
   - aucun decoupage temporel arbitraire : il faut toujours au moins deux
     attaques acoustiques plausibles ;
   - si les indices ne sont pas suffisants, le token Whisper original reste
     intact.

3. Seek
   - aucune nouvelle modification : le correctif deja pousse est conserve,
     puisque le glissement relatif n'est plus observe.

## Installation

```powershell
cd H:\EZScore
tar -xf "$env:USERPROFILE\Downloads\EZScore_VOCALISES_PY313_FIX2.zip" -C H:\EZScore

.\.venv-py313\Scripts\python.exe -m py_compile `
  .\ezscore\player\choir_vocalises.py

powershell -ExecutionPolicy Bypass -File .\scripts\install_analysis_hq.ps1
```

Puis :

```powershell
.\.venv-py313\Scripts\python.exe -m streamlit run EZScore.py
```

Test cible : Aline, meme passage que sur la capture.
