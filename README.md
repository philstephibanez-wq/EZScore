# EZScore — player correction

Correctifs inclus :
- restauration défensive de la ligne `Chœurs` / vocalises (`la la la`) depuis
  `whisper_vocals_small.json` si le payload courant arrive vide ;
- suppression de la génération FFmpeg de toutes les vitesses pendant le rendu
  Streamlit ;
- changement de vitesse côté navigateur via `HTMLMediaElement.playbackRate`
  avec `preservesPitch = true` ;
- EQ 3 bandes et volumes restent dans WebAudio ;
- même horloge média pour Accord / Accords / Chant / Chœurs ;
- correction de dérive STEM uniquement au-delà de 80 ms ;
- retard visuel du conducteur conservé à 350 ms.

## Installation

```powershell
cd H:\EZScore

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\EZScore_PLAYER_FIX_choeurs_pitch.zip" `
  -DestinationPath . `
  -Force

python -m py_compile .\ezscore\player\karaoke_stem_webaudio_r12c.py
python -m py_compile .\ezscore\ui\__init__.py

git diff --check
git status
```

Redémarrer Streamlit.

## Test
1. vérifier `Chœurs` et les `la la la` ;
2. tester 1.00x / 0.75x / 1.25x : tonalité inchangée ;
3. tester Original puis Mix STEM ;
4. tester Pause / Lecture / Seek ;
5. vérifier EQ/volumes ;
6. surveiller l'absence du retour de WinError 10054.
