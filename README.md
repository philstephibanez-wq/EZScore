# EZScore_PLAYER_SYNC_VOCALISES_PY313

Base :
- branche `restore/full-reanalysis-r1`
- commit `dd65359738a0b8bc9449f197cb885edbd33693c6`
- `EZScore_CHOIR_V4_2_FULL`

## Contenu

- `ezscore/player/lyrics_layout.py`
  - correction du glissement visuel Chant/Choeurs apres seek ;
  - translation globale des lanes sur la meme horloge
    `timelineVisualXForTime(time)`.

- `ezscore/player/choir_vocalises.py`
  - nouveau module ;
  - segmente les vocalises longues type `Ooooooooo` en evenements `Ho`
    uniquement lorsqu'il existe plusieurs onsets acoustiques credibles dans
    `backing_vocals.wav` ;
  - non destructif : si la segmentation n'est pas sure, le token original
    est conserve ;
  - ne modifie pas l'analyse CHOIR V4.2.

- `requirements-analysis-hq.txt`
  - environnement Python 3.13 ;
  - Torch 2.6.0+cu124 ;
  - torchvision 0.21.0+cu124 ;
  - torchaudio 2.6.0+cu124 ;
  - triton-windows 3.2.0.post21 ;
  - Streamlit, Plotly, librosa, soundfile, OpenAI Whisper ;
  - BS-RoFormer, MelBand RoFormer, LV-Chordia, madmom.

- `scripts/install_analysis_hq.ps1`
  - utilise explicitement `.venv-py313`.

## Installation

```powershell
cd H:\EZScore
tar -xf "$env:USERPROFILE\Downloads\EZScore_PLAYER_SYNC_VOCALISES_PY313.zip" -C H:\EZScore

.\.venv-py313\Scripts\python.exe -m py_compile `
  .\ezscore\player\choir_vocalises.py `
  .\ezscore\player\lyrics_layout.py

powershell -ExecutionPolicy Bypass -File .\scripts\install_analysis_hq.ps1
```

Puis :

```powershell
cd H:\EZScore
.\.venv-py313\Scripts\python.exe -m streamlit run EZScore.py
```

## Test cible

1. Charger Aline.
2. Seeker plusieurs fois.
3. Verifier l'absence de glissement relatif Chant / Choeurs / Accords.
4. Verifier que les longues vocalises redeviennent des `Ho  Ho  Ho...`
   lorsque le stem backing presente des attaques distinctes.
