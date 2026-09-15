# EZScore — STEM pipeline R6 / crossover 3 bandes coloré

Branche cible : `feature/stem-analysis-pipeline`

R6 remplace l'ancien EQ en série par un vrai découpage fréquentiel parallèle :

```text
                    ┌─ low-pass 250 Hz ─ Gain LOW ─┐
BufferSource ───────┼─ HP 250 → LP 4 kHz ─ Gain MID ├─ somme ─ Gain piste ─ Master
                    └─ high-pass 4 kHz ─ Gain HIGH ─┘
```

Réglages :
- Graves : < 250 Hz
- Médiums : 250 Hz – 4 kHz
- Aigus : > 4 kHz
- Plage EQ : -6 dB à +6 dB
- Compensation statique de niveau après EQ

Couleurs par catégorie :
- Volume / Master : bleu
- Graves : orange
- Médiums : violet
- Aigus : vert

Les états ON/OFF avant et pendant la lecture restent conservés.

Installation :

```powershell
cd H:\EZScore
python -m py_compile .\ezscore\analysis\stems.py
python -m py_compile .\ezscore\player\stem_webaudio.py
python -m py_compile .\ezscore\ui\app_shell.py
python -m py_compile .\ezscore\ui\stem_lab_analysis.py
git status --short
```

Ne pas ajouter :
`data/EZScore.sqlite3`, `data/logs/ezscore_perf.log`, `data/analysis/`.

L'utilisateur effectue lui-même commit/push.
