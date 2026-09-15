# EZScore — STEM pipeline R6.1 / correctif lecteur WebAudio

Correctif de R6 :

- corrige l'erreur `BidiComponent Error: Unexpected end of input`;
- conserve le crossover 3 bandes ;
- conserve la compensation de niveau ;
- conserve les couleurs par catégorie :
  - Volume / Master : bleu
  - Graves : orange
  - Médiums : violet
  - Aigus : vert
- conserve ON/OFF, volumes et Master.

Validation effectuée :
- `py_compile` sur tous les fichiers Python ;
- parsing AST Python ;
- **`node --check` sur le JavaScript réel du composant WebAudio**.

Installation :

```powershell
cd H:\EZScore
python -m py_compile .\ezscore\analysis\stems.py
python -m py_compile .\ezscore\player\stem_webaudio.py
python -m py_compile .\ezscore\ui\app_shell.py
python -m py_compile .\ezscore\ui\stem_lab_analysis.py
```

Ne pas ajouter au commit :
`data/EZScore.sqlite3`, `data/logs/ezscore_perf.log`, `data/analysis/`.
