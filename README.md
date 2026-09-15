# EZScore — feature/vocal-midi-analysis — lecteur 3 pistes

Branche cible obligatoire :

```text
feature/vocal-midi-analysis
```

## Lecteur d'analyse

Le lecteur joue désormais, sur la même horloge MP3 :

```text
MP3 original
+ MIDI accords
+ MIDI chant
```

Volumes indépendants :

```text
Volume chanson
Volume accords MIDI
Volume chant MIDI
```

Le chant MIDI n'est actif que si une analyse vocale persistée existe.

## Instrument du chant

Sélecteur dédié :

```text
Instrument du chant MIDI
```

Choix :

```text
Alto Sax
Tenor Sax
Soprano Sax
Baritone Sax
Voice Oohs
Acoustic Grand Piano
```

Valeur par défaut :

```text
Alto Sax
```

Le but est de distinguer clairement la ligne mélodique de l'accompagnement lors
de la comparaison à l'oreille.

## Synchronisation

Le MP3 reste l'horloge maître.

FluidSynth utilise deux canaux :

```text
canal 1 = accords
canal 2 = chant
```

Un seek du MP3 recale les deux curseurs MIDI.

## Aucun changement du moteur d'analyse

Cette livraison ne change pas :

```text
accords
Whisper
phonèmes
R33
raffinement expérimental des blocs
timestamps
```

Elle ajoute uniquement la lecture de la timeline vocale déjà calculée.

## Fichiers

```text
ezscore/analysis/vocal.py
ezscore/midi/analysis_player.py
ezscore/ui/app_shell.py
readme.md
```

## Installation

```powershell
cd H:\EZScore
git branch --show-current
```

Résultat obligatoire :

```text
feature/vocal-midi-analysis
```

Puis :

```powershell
tar -xf "$env:USERPROFILE\Downloads\EZScore_FEATURE_VOCAL_DUAL_PLAYER.zip" -C H:\EZScore

python -m py_compile .\ezscore\analysis\vocal.py
python -m py_compile .\ezscore\midi\analysis_player.py
python -m py_compile .\ezscore\ui\app_shell.py
python -m py_compile .\EZScore.py
python -m compileall -q .\ezscore

python -m streamlit run .\EZScore.py
```

## Recette

1. Ouvrir `Analyse`.
2. Vérifier MP3 + MIDI accords.
3. Calculer la mélodie vocale si nécessaire.
4. Vérifier l'apparition de `Instrument du chant MIDI`.
5. Garder `Alto Sax`.
6. Charger le synthé MIDI.
7. Lancer la lecture.
8. Régler séparément les trois volumes.
9. Mettre les accords MIDI à zéro pour contrôler voix détectée + chanson.
10. Mettre la chanson à zéro pour écouter uniquement les deux MIDI.

Ne pas fusionner dans master avant validation sur plusieurs morceaux.
