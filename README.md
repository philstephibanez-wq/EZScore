# EZScore R29 FIX4 — source unique paroles + capo player

Correctif cumulatif de cohérence entre Blocs, Paroles + accords et les players.

## Paroles : une seule source canonique

La vue **Blocs > Édition** est désormais l'unique éditeur de paroles.

Les anciennes corrections concurrentes issues de l'ancien éditeur `Corriger les paroles` ne doivent plus prendre la main dans une autre vue.

Lorsqu'une correction de bloc est enregistrée :
- elle remplace les anciennes corrections qui chevauchent le même intervalle ;
- elle reste rattachée aux bornes du bloc structurel courant ;
- les corrections devenues obsolètes après un ancien découpage sont ignorées par le player.

La timeline effective des paroles est reconstruite à partir des **blocs structurels persistés courants**.

Elle alimente :
- Paroles + accords ;
- player Vue ;
- player MIDI de contrôle en Édition.

L'ancien éditeur redondant `Corriger les paroles` de Paroles + accords est retiré de l'interface.

## Structure persistée

La structure persistée du morceau reste disponible comme référence même lorsque la détection automatique de sections est désactivée.

Ainsi les mêmes blocs sont utilisés pour :
- l'édition des paroles ;
- Paroles + accords ;
- les players.

## Capodastre temps réel

Le capodastre reste disponible dans la sidebar de `Chanson`, en Vue comme en Édition.

Le changement est immédiat et ne relance aucune analyse.

Séparation explicite :
- harmonie réelle : utilisée par l'analyse et le MIDI ;
- accord affiché : transformé par le capo ;
- diagramme guitare : construit depuis l'accord affiché.

Exemple :

```text
Accord réel : Cm
Capo : 3
Affichage : Am
MIDI : Cm
Diagramme : Am
```

## Fichiers du livrable

- `EZScore.py`
- `readme.md`
- `ezscore/persistence.py`
- `ezscore/player/web_player.py`
- `ezscore/backoffice/player.py`
