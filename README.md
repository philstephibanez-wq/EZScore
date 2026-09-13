# EZScore R20_FIX3

R20_FIX3 corrige les régressions découvertes après le découpage modulaire.

## Player MIDI d'édition

- MP3 original = horloge maître ;
- MIDI généré depuis la grille effective après corrections ;
- guitare clean GM 27 par défaut, piano GM 0 en option ;
- un down par temps avec accentuation métrique ;
- même flux d'événements pour le player et l'export .mid ;
- synthèse FluidSynth + SoundFont directement dans le navigateur ;
- aucun port MIDI système requis ;
- aucun streamlit.components.v1.html ;
- player migré vers Streamlit Components v2.

## Impression

Correction des constantes de pagination déplacées dans ezscore/printing.py :
- PRINT_PAGE_CONTENT_MM ;
- PRINT_FIRST_PAGE_HEADER_MM.

EZScore.py importe désormais explicitement ces constantes publiques.

## Modularisation

EZScore.py reste autour de 6140 lignes, contre environ 12940 avant R20.

Modules :
- ezscore/notation.py
- ezscore/persistence.py
- ezscore/printing.py
- ezscore/timeline.py
- ezscore/transcription.py
- ezscore/midi/events.py
- ezscore/midi/export.py
- ezscore/midi/web_player.py

## Livrable

Le ZIP contient uniquement :
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
