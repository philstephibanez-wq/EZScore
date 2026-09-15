# EZScore — STEM pipeline R4 / lecteur WebAudio complet

Branche cible :

```text
feature/stem-analysis-pipeline
```

R4 corrige le manque principal de R3 : le lecteur est désormais le même
workflow WebAudio que dans `EZScore_STEM_LAB`.

## Lecteur

Le bloc **Lecteur synchronisé** contient :

```text
▶ Lecture
⏸ Pause
⏹ Stop
seek

Original   [✓ Actif] [volume]
Chant      [✓ Actif] [volume]
Batterie   [  Actif] [volume]
Basse      [  Actif] [volume]
Other      [  Actif] [volume]

Paroles synchronisées
```

Un seul `AudioContext` pilote toutes les pistes.

Les stems démarrent au même `when` WebAudio et au même offset. Il n'y a pas de
micro-seek permanent pendant la lecture.

Les pistes sont activables/désactivables en temps réel et chaque piste a son
propre `GainNode`.

## Préviews navigateur

Les WAV Demucs restent intacts.

Pour éviter de transférer plusieurs centaines de Mo au navigateur, le player
fabrique/cache des copies MP3 96 kb/s dans :

```text
data/analysis/stem_lab/<audio_hash>/browser_preview/
```

L'original MP3 est copié sans transcodage lorsqu'il est déjà en MP3.

## Paroles dans le lecteur

Si Whisper `small` a déjà été lancé sur l'audio original, les mots horodatés
sont affichés/surlignés dans le lecteur.

Le player est reconstruit après transcription grâce à une clé contenant le
nombre de mots.

## Workflow inchangé

```text
Original → Whisper small → paroles
vocals   → mélodie / F0
drums    → tempo / beats / mesures
bass     → fondamentale auxiliaire
other    → harmonie / accords
```

Audio original = horloge maître.

## Installation

Dézipper directement dans `H:\EZScore`, sans dossier intermédiaire.

```powershell
cd H:\EZScore
python -m py_compile .\ezscore\analysis\stems.py
python -m py_compile .\ezscore\ui\app_shell.py
python -m py_compile .\ezscore\ui\stem_lab_analysis.py
python -m py_compile .\ezscore\player\stem_webaudio.py
git status --short
```

Ne pas ajouter au commit :

```text
data/EZScore.sqlite3
data/logs/ezscore_perf.log
data/analysis/
```

L'utilisateur effectue lui-même commit et push.
