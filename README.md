# EZScore — STEM pipeline R5 / EQ 3 bandes

Branche cible : `feature/stem-analysis-pipeline`

R5 ajoute une mini-table de mixage WebAudio par piste :

```text
Piste | ON | Volume | Graves | Médiums | Aigus | Reset EQ
```

Pistes :
- Original
- Chant
- Batterie
- Basse
- Other

EQ WebAudio par piste :

```text
BufferSource
→ lowshelf 180 Hz
→ peaking 1.2 kHz / Q 0.9
→ highshelf 5 kHz
→ Gain piste
→ Master Gain
→ sortie
```

Plage EQ : `-12 dB` à `+12 dB`, neutre à `0 dB`.

Volumes piste : `0 à 125 %`.
Master global : `0 à 125 %`.

R5 corrige aussi l'état ON/OFF avant la première lecture : l'état du mixer est
stocké en JavaScript avant la création de l'AudioContext puis réappliqué après
le décodage. Une piste coupée avant Lecture reste donc réellement muette.

Tous les changements ON/OFF, volume et EQ sont appliqués en temps réel avec
`setTargetAtTime()` sans recréer les sources.

Installation :

```powershell
cd H:\EZScore
python -m py_compile .\ezscore\analysis\stems.py
python -m py_compile .\ezscore\player\stem_webaudio.py
python -m py_compile .\ezscore\ui\app_shell.py
python -m py_compile .\ezscore\ui\stem_lab_analysis.py
git status --short
```

Ne pas ajouter : `data/EZScore.sqlite3`, `data/logs/ezscore_perf.log`,
`data/analysis/`.

L'utilisateur effectue lui-même commit/push.
