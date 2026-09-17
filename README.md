# EZScore — R11c

Correctif ciblé du conducteur karaoké, sans modifier le moteur audio R10.

## Corrections

- suppression de la barre verticale blanche et du texte `temps courant` ;
- `Diagramme` et `Accord courant` sont fixés sur la ligne de mire à 38 % ;
- quand `Diagrammes guitare` est coché, la ligne diagramme reste stable :
  elle ne disparaît plus au hasard selon l'accord ;
- fallback déterministe des slash-chords (`Gm/5` -> voicing de `Gm`) ;
- la signature recompose maintenant la géométrie de **toutes** les files :
  `Accords`, `Chant`, `Chœurs` ;
- passage `4/4 -> 2/4 -> 9/8` : les paroles se repositionnent visuellement
  avec les accords, sans changer leurs timestamps ;
- la vitesse reste synchronisée avec l'horloge WebAudio.

## Installation

Depuis `H:\EZScore` :

```powershell
Expand-Archive -Path .\EZScore_R11c_focus_sync.zip -DestinationPath . -Force

python -m py_compile .\ezscore\player\karaoke_stem_webaudio_r11c.py
python -m py_compile .\ezscore\ui\__init__.py

git diff --check
git status
```

Redémarrer Streamlit après décompression.

## Test avant push

Tester la même position audio successivement en `4/4`, `2/4` puis `9/8`.
Les trois files doivent se recomposer ensemble. Les timestamps audio ne doivent
pas changer.

Cocher `Diagrammes guitare` :
- la ligne Diagramme apparaît au-dessus ;
- le diagramme courant est centré sur la ligne de mire ;
- l'accord courant est juste en dessous au même X ;
- la ligne Diagramme ne saute plus selon les accords.

Ne pas pousser avant validation visuelle.
