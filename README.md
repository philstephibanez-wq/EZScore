# EZScore — STEM pipeline R9 / workflow 4 étapes + watchdog MIDI chant

## Contrat

Comme MAESTRO :

- aucune erreur masquée ;
- aucun fallback silencieux ;
- si une étape bloque, on identifie le point exact et on l'arrête explicitement ;
- l'audio original reste l'horloge maître ;
- aucun glissement temporel.

## Workflow Analyse

```text
1 — STEM
    séparation Demucs
    → lecteur STEM immédiatement

2 — Paroles
    Whisper small sur audio original
    → même lecteur STEM + paroles synchronisées

3 — Blocs / structure
    mesures + accords + répétitions + paroles
    → segmentation visuelle en blocs

4 — MIDI
    Chant + Accords + Batterie
    → lecteur Audio original + MIDI uniquement quand les 3 pistes sont terminées
```

Le lecteur STEM n'est plus déplacé à la fin du workflow : il apparaît dès que
les stems sont prêts. Après les paroles, ce même lecteur reçoit les mots
horodatés et affiche leur défilement synchronisé.

## Blocage MIDI chant : correction

Le problème venait de l'appel monolithique `librosa.pyin()` sur toute la piste
vocale : aucune progression observable à l'intérieur de cet appel, donc le
worker pouvait rester indéfiniment sur le même état.

R9 applique deux protections réelles :

### pYIN segmenté

La piste vocale est analysée par segments bornés de 20 secondes.
Après chaque segment :

- progression écrite ;
- index `segment n/N` écrit ;
- timestamps absolus conservés.

### Watchdog externe

L'analyse vocale tourne dans un processus enfant dédié.

Le worker superviseur :

- lit `vocal_progress.json` ;
- publie `job_status.json` ;
- tue le processus vocal si aucun progrès n'est constaté pendant 120 s ;
- tue le processus si la durée totale dépasse 900 s ;
- écrit l'erreur réelle dans `job.log` et `job_status.json`.

Il ne continue jamais avec un MIDI chant absent.

## Diagnostics

```text
data/analysis/stem_lab/<hash>/midi/
  job_status.json
  job.log
  vocal_progress.json
  vocal_analysis.json
  vocal.mid
  chords.mid
  drums.mid
  stem_mix.mid
  stem_midi.json
```

## Player MIDI

Instruments modifiables en temps réel :

- Chant : Piano, Voice Oohs, Choir, Strings, Sax, Flute, Synth...
- Accords : Piano, guitares, Strings...
- Batterie : Standard, Room, Power, Electronic, TR-808, Jazz, Brush, Orchestra.

## Validation locale

```powershell
cd H:\EZScore

python -m py_compile .\ezscore\analysis\stem_midi.py
python -m py_compile .\ezscore\analysis\stem_vocal_worker.py
python -m py_compile .\ezscore\analysis\stem_midi_worker.py
python -m py_compile .\ezscore\midi\stem_sync_player.py
python -m py_compile .\ezscore\player\stem_webaudio.py
python -m py_compile .\ezscore\player\media_url.py
python -m py_compile .\ezscore\ui\stem_lab_analysis.py
python -m py_compile .\ezscore\ui\app_shell.py
```

Ne pas ajouter au commit :

- `data/EZScore.sqlite3`
- `data/logs/ezscore_perf.log`
- `data/analysis/`

L'utilisateur effectue commit/push lui-même.


## Job bloqué / worker mort

`load_stem_midi_job()` vérifie maintenant que le PID déclaré `running`
existe réellement. Si le worker a disparu sans mettre à jour le statut,
le job passe explicitement en erreur `worker_dead`.

Aucun état `running` fantôme n'est conservé indéfiniment.


## R9.1 — ergonomie lecteurs et blocs

- Sélecteurs MIDI : thème sombre explicite, texte clair, numéro GM.
- Lecteur STEM : hauteur adaptée pour éviter le scroll interne.
- Blocs : minimum structurel de 4 mesures, sans découpage fixe en groupes de 4.
- Anciennes structures avec blocs de 1–3 mesures normalisées à l'ouverture.
- Aucun timestamp canonique de beat, mesure, accord ou parole n'est déplacé.
