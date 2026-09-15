# EZScore — STEM pipeline R8.2 / workflow séquentiel + instruments MIDI

## Workflow

La page STEM est désormais strictement séquentielle :

```text
1. Séparation STEM
2. Paroles Whisper small
3. Structure musicale
4. MIDI Chant + Accords + Batterie
5. Lecteur de contrôle
6. Prévisualisation des blocs
```

Chaque étape bloque explicitement la suivante tant qu'elle n'est pas terminée.

Le lecteur MP3+MIDI n'est plus affiché avec une piste Chant désactivée/pending.
Il apparaît uniquement lorsque les trois pistes MIDI sont complètes.

## Instruments

Le lecteur MP3+MIDI permet désormais de changer en temps réel :

- instrument du Chant ;
- instrument des Accords ;
- kit de Batterie GM.

Exemples chant/accords :
Piano, guitares nylon/steel/clean/muted, strings, choir, Voice Oohs,
saxophones, flute, synth leads.

Kits batterie :
Standard, Room, Power, Electronic, TR-808, Jazz, Brush, Orchestra.

Les sélecteurs du player sont autoritaires : les événements `program` du
bundle MIDI ne réécrasent plus un choix utilisateur.

## Contrat

- audio original = horloge maître ;
- aucun glissement temporel ;
- aucune erreur masquée ;
- aucun fallback silencieux ;
- HTTP media R8 conservé, pas de base64 audio dans Bidi.

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
