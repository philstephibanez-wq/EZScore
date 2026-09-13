# EZScore R20_FIX4

Correction du player d'édition MP3 + MIDI.

## Correctifs

- suppression de `AudioContext.createMediaElementSource(audio)` pour le MP3 : le composant Streamlit v2 peut réutiliser le même élément `<audio>` et Chromium interdit de le rattacher une seconde fois à un autre `MediaElementSourceNode` ;
- le MP3 reste l'horloge maître via `audio.currentTime` et sort directement par le lecteur HTML natif ;
- le volume chanson est piloté directement par `audio.volume` ;
- nouvelle URL SoundFont principale via `raw.githubusercontent.com` ;
- fallback SoundFont automatique ;
- cache navigateur des octets SoundFont pour éviter un nouveau téléchargement à chaque rerender ;
- initialisation du synthé rendue idempotente ;
- un clic direct sur Lecture charge désormais automatiquement FluidSynth + SoundFont puis reprend la lecture ;
- le bouton `Charger le synthé MIDI` reste disponible pour précharger explicitement le synthé.

## Livrable

Le ZIP contient uniquement les fichiers modifiés :

- `readme.md`
- `ezscore/midi/web_player.py`

Dézipper dans `H:\EZScore` en conservant l'arborescence.
