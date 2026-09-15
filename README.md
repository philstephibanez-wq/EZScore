# EZScore — STEM pipeline R8.1 / player MIDI progressif

## Règle contractuelle

Aucune erreur masquée. Aucun fallback silencieux.

## Problème corrigé

En R8, le player MP3+MIDI n'apparaissait qu'après la fin complète du worker.
La raison : `stem_midi.json` n'était écrit qu'après l'analyse vocale pYIN,
qui est l'étape la plus longue.

La capture montrait donc correctement :

```text
Analyse chant + batterie + accords en cours…
```

mais aucun bundle exploitable n'existait encore pour le player.

## R8.1

Le worker est maintenant explicitement découpé en deux étapes.

### Étape 1
- batterie analysée ;
- MIDI accords écrit ;
- MIDI batterie écrit ;
- `stem_midi.json` partiel écrit ;
- player MP3+MIDI immédiatement disponible avec Accords + Batterie.

### Étape 2
- analyse pYIN du chant ;
- MIDI Chant écrit ;
- MIDI combiné écrit ;
- `stem_midi.json` remplacé atomiquement par la version complète.

Ce n'est pas un fallback : l'interface indique clairement que Chant est
`en cours` et désactive cette piste jusqu'à ce qu'elle existe.

## Timeline

Toujours inchangée :

```text
MP3 original = horloge maître
MIDI = dérivé, jamais maître
```

Aucun timestamp n'est déplacé.

## HTTP média

R8 reste conservé :
- aucun audio base64 dans Bidi ;
- audio servi par Streamlit MediaFileManager en HTTP ;
- petits événements MIDI JSON uniquement.

## Compilation

```powershell
cd H:\EZScore
python -m py_compile .\ezscore\player\media_url.py
python -m py_compile .\ezscore\player\stem_webaudio.py
python -m py_compile .\ezscore\midi\stem_sync_player.py
python -m py_compile .\ezscore\analysis\stem_midi.py
python -m py_compile .\ezscore\analysis\stem_midi_worker.py
python -m py_compile .\ezscore\ui\stem_lab_analysis.py
python -m py_compile .\ezscore\ui\app_shell.py
```

Ne pas ajouter :
`data/EZScore.sqlite3`, `data/logs/ezscore_perf.log`, `data/analysis/`.
