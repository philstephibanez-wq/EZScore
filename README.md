# EZScore R19

R19 remplace le synthé Web Audio par une vraie sortie MIDI synchronisée avec le MP3.

## Instruments
- Electric Guitar (clean) : GM 27, par défaut.
- Acoustic Grand Piano : GM 0.

## Pattern
Un accord MIDI est rejoué à chaque temps.
Les temps forts utilisent une vélocité plus élevée.
La guitare applique un léger down grave vers aigu ; le piano joue les notes simultanément.

## Player
Chemin : Chanson > Grille > Jouer.

Le MP3 est le transport maître.
Le player envoie Program Change, Note On et Note Off via Web MIDI.
Cliquer sur Activer MIDI, choisir une sortie MIDI, puis lancer Play.

Aucun oscillateur Web Audio n'est utilisé.

Le futur player Jouer > Paroles + accords reste une fonction séparée.

## Livrable
- EZScore.py
- readme.md
