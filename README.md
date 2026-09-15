# EZScore — filtre anti-vibrato du MIDI vocal

Branche cible :

```text
feature/vocal-midi-analysis
```

Cette livraison modifie uniquement la segmentation des notes chantées.

## Problème traité

Le pYIN détecte correctement les variations fines de fréquence, mais l'ancienne
conversion en MIDI pouvait transformer une excursion de vibrato autour d'une
note en une note MIDI voisine.

Exemple indésirable :

```text
A4 → A#4 → A4
```

alors que le chanteur tient en réalité un A4 avec vibrato.

## Nouveau comportement

La détection F0 reste précise. La réduction de sensibilité intervient uniquement
au moment de transformer le contour F0 en notes MIDI.

Réglages initiaux :

```text
filtre médian          : 7 frames
hystérésis             : 70 cents
nouvelle note stable   : 100 ms
```

Une note voisine n'est donc acceptée que si :
1. la hauteur s'éloigne réellement de la note courante de plus de 70 cents ;
2. la nouvelle note reste stable environ 100 ms.

Lorsqu'un vrai changement est confirmé, le début de la nouvelle note est
replacé au premier frame stable. Il n'y a donc pas 100 ms de retard ajouté au
MIDI.

## Cache

Le schéma vocal passe de `1` à `2`.

Les anciennes analyses vocales ne sont volontairement plus chargées afin de ne
pas continuer à écouter un MIDI généré avec l'ancien segmentateur.

Il faut donc cliquer une fois sur :

```text
Analyser / recalculer la voix
```

pour chaque morceau testé.

Le cache contient aussi les paramètres de segmentation utilisés.

## Ce qui ne change pas

Aucune modification de :

```text
accords
Whisper
phonèmes
paroles
R33
raffinement des blocs
lecteur 3 pistes
horloge MP3
timestamps des autres timelines
```

Le changement est limité à :

```text
ezscore/analysis/vocal.py
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
tar -xf "$env:USERPROFILE\Downloads\EZScore_FEATURE_VOCAL_VIBRATO_FILTER.zip" -C H:\EZScore

python -m py_compile .\ezscore\analysis\vocal.py
python -m py_compile .\EZScore.py
python -m compileall -q .\ezscore

python -m streamlit run .\EZScore.py
```

## Recette

1. Ouvrir `Analyse`.
2. Recalculer la voix.
3. Garder `Alto Sax`.
4. Mettre `Volume accords MIDI = 0`.
5. Écouter MP3 + chant MIDI.
6. Vérifier que les petites notes parasites dues au vibrato ont diminué.
7. Vérifier qu'un vrai passage mélodique d'un demi-ton ou d'un ton reste bien
   détecté.

Ne pas fusionner dans `master` avant validation sur plusieurs morceaux.
