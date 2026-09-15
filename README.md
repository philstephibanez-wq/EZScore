# EZScore — STEM pipeline R7.2 / lecteur MP3 + MIDI synchronisés

R7.2 ajoute un lecteur de contrôle synchronisé :

```text
MP3 original = horloge maître

MP3 original [ON] [volume]
MIDI Chant   [ON] [volume]
MIDI Accords [ON] [volume]
MIDI Batterie[ON] [volume]
```

Le synthé MIDI est FluidSynth/WebAssembly dans le navigateur avec SoundFont.
Il n'utilise aucune sortie MIDI système.

Les événements MIDI sont lus directement selon `audio.currentTime`.
Le MIDI ne devient jamais horloge maître et ne déplace aucun timestamp.

Important : les bundles R7/R7.1 déjà présents doivent être régénérés une fois
afin d'ajouter `browser_events` dans `stem_midi.json`.

## Sur le WinError 10054

Ce livrable ne prétend pas masquer cette exception Windows/Streamlit.
Elle provient de la fermeture d'une connexion socket côté navigateur/serveur.
La génération MIDI reste dans un processus séparé, et le nouveau lecteur MIDI
s'exécute entièrement dans le navigateur.

## Installation

```powershell
cd H:\EZScore
python -m py_compile .\ezscore\analysis\stem_midi.py
python -m py_compile .\ezscore\analysis\stem_midi_worker.py
python -m py_compile .\ezscore\midi\stem_sync_player.py
python -m py_compile .\ezscore\ui\stem_lab_analysis.py
python -m py_compile .\ezscore\player\stem_webaudio.py
python -m py_compile .\ezscore\ui\app_shell.py
```

Ne pas ajouter :
`data/EZScore.sqlite3`, `data/logs/ezscore_perf.log`, `data/analysis/`.
