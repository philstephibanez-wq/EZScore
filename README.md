# EZScore R31 STABILIZATION — FSM, players, impression, volume

Base : dernier push utilisateur `31de8c7641ec619667befe4ad83b65eada1545a0`.

Cette version est volontairement une version de stabilisation. Elle ne lance
pas encore la refonte de la timeline phonétique canonique.

## Navigation : FSM

La navigation d'un morceau est maintenant pilotée par
`ezscore/ui/song_fsm.py`.

États :
- vues : Grille, Paroles + accords, Blocs, Analyse ;
- modes : Vue, Édition.

Règles :
- une seule clé Streamlit pour la vue ;
- une seule clé Streamlit pour le mode ;
- suppression du doublon `song_mode_*_radio` ;
- changer de vue revient en mode Vue ;
- Analyse ne possède jamais de mode Édition ;
- Édition n'est disponible que si `song.edit` est autorisé.

L'objectif est d'empêcher les états incohérents Vue/Édition et de préparer
l'extraction progressive de chaque vue hors du monolithe.

## Régressions corrigées

- restauration de l'import `build_midi_file` utilisé dans Analyse ;
- le player MIDI et l'export MIDI utilisent à nouveau le même constructeur ;
- l'impression de la vue courante est rendue dans le panneau latéral permanent
  afin de rester accessible sans remonter la page ;
- boutons explicites :
  - Imprimer la grille ;
  - Imprimer paroles + accords.

## Volume par chanson

Les préférences de volume sont persistées dans le `settings_json` déjà
associé à `song_preferences` :
- `audio_volume` ;
- `midi_volume`.

Le panneau Morceau expose :
- Volume chanson ;
- Volume MIDI en mode Édition.

Le player de lecture et le player MIDI sont initialisés avec ces valeurs.

## Architecture

R31 introduit une première séparation supplémentaire :

```text
ezscore/
  ui/
    song_fsm.py     # états et transitions de la vue/mode
  player/
    web_player.py   # lecture MP3
  midi/
    web_player.py   # lecture MP3 + synthé MIDI
  backoffice/
    player.py       # orchestration du player d'édition
```

La prochaine refonte fonctionnelle séparera la timeline acoustique/phonétique
des blocs éditoriaux. Les blocs resteront alors une structure de présentation
et ne piloteront plus les timestamps des paroles.

## Fichiers modifiés

- `EZScore.py`
- `ezscore/ui/song_fsm.py`
- `ezscore/player/web_player.py`
- `ezscore/backoffice/player.py`
- `ezscore/midi/web_player.py`
- `readme.md`
