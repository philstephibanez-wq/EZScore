# EZScore — STEM pipeline R7.1 / MIDI non bloquant

Constat validé : en R7 les fichiers MIDI finissaient bien par apparaître,
mais la génération pYIN tournait dans le thread Streamlit et pouvait figer
l'interface jusqu'à la fin du calcul. Le `WinError 10054` était alors une
conséquence possible de la rupture du WebSocket.

R7.1 exécute la génération MIDI dans un processus Python séparé.

Le bouton revient immédiatement et EZScore reste utilisable.

Fichiers de suivi :

```text
data/analysis/stem_lab/<hash>/midi/
  job_status.json
  job.log
  vocal.mid
  chords.mid
  drums.mid
  stem_mix.mid
  stem_midi.json
```

Bouton d'actualisation manuel :
`↻ Actualiser l'état MIDI`

Installation :

```powershell
cd H:\EZScore
python -m py_compile .\ezscore\analysis\stems.py
python -m py_compile .\ezscore\analysis\stem_midi.py
python -m py_compile .\ezscore\analysis\stem_midi_worker.py
python -m py_compile .\ezscore\player\stem_webaudio.py
python -m py_compile .\ezscore\ui\app_shell.py
python -m py_compile .\ezscore\ui\stem_lab_analysis.py
```

Ne pas ajouter au commit :
`data/EZScore.sqlite3`, `data/logs/ezscore_perf.log`, `data/analysis/`.
