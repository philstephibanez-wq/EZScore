# EZScore R20

R20 :
- player d'édition MP3 + MIDI SoundFont dans le navigateur ;
- MP3 horloge maître ;
- MIDI généré depuis la grille effective après corrections ;
- guitare clean GM 27 par défaut, piano GM 0 en option ;
- un down par temps avec vélocités accentuées ;
- même flux MIDI pour écoute et export .mid ;
- aucun port MIDI système ;
- aucun streamlit.components.v1.html.

## Modularisation

EZScore.py passe d'environ 12940 à 6140 lignes.

Modules extraits :
- ezscore/notation.py
- ezscore/persistence.py
- ezscore/printing.py
- ezscore/timeline.py
- ezscore/transcription.py
- ezscore/midi/events.py
- ezscore/midi/export.py
- ezscore/midi/web_player.py

## Livrable

Le ZIP contient :
- EZScore.py
- readme.md
- templates/EZScore.score
- ezscore/__init__.py
- ezscore/notation.py
- ezscore/persistence.py
- ezscore/printing.py
- ezscore/timeline.py
- ezscore/transcription.py
- ezscore/midi/__init__.py
- ezscore/midi/events.py
- ezscore/midi/export.py
- ezscore/midi/web_player.py

Dézipper dans H:\EZScore en conservant l'arborescence.
