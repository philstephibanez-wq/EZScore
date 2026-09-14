# EZScore R32 - Phoneme timeline diagnostics

Base utilisateur : `4cf5abedbeb890a63bf8bc2345f6d918d4af9bf5` (R31 STABILIZATION FSM).

## Objectif

Rendre visibles les phonèmes utilisés par EZScore et les replacer dans la
grille musicale : temps audio, mesure et beat.

Cette version ne prétend pas encore effectuer une détection acoustique directe
des phonèmes. La source actuelle reste :

```text
audio
  -> Whisper
  -> mots horodatés
  -> représentation phonétique
  -> unités phonétiques réparties dans l'intervalle du mot
  -> projection sur beats / mesures
```

Le diagnostic est volontairement explicite sur cette provenance afin de ne pas
confondre phonétique dérivée et future détection acoustique.

## Nouveau module

`ezscore/phonetics/timeline.py`

Il fournit une timeline indépendante des blocs éditoriaux :

```text
phoneme
start
end
duration
word
measure
beat
beat_index
source
acoustic
liaison
```

La modification des bornes d'un bloc ne doit donc jamais modifier cette
timeline.

## Vue Analyse

La vue Analyse affiche maintenant :

1. une vue musicale groupée par beat :
   - mesure ;
   - beat ;
   - plage de temps ;
   - phonèmes ;
   - paroles correspondantes ;

2. un détail phonème par phonème :
   - début ;
   - fin ;
   - durée ;
   - mesure ;
   - beat ;
   - phonème ;
   - mot ;
   - source.

## Modèle cible

```text
                    audio.currentTime
                           |
             +-------------+-------------+
             |                           |
             v                           v
        BeatTimeline               PhonemeTimeline
        mesures/beats              voix / phonèmes
             |                           |
             +-------------+-------------+
                           |
                           v
                       Player
```

Les blocs structurels restent une couche éditoriale et ne gouvernent pas
l'horodatage vocal.

## Fichiers du livrable

- `EZScore.py`
- `ezscore/phonetics/__init__.py`
- `ezscore/phonetics/timeline.py`
- `readme.md`
