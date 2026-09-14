# EZScore R29 FIX7 — ergonomie chanson compacte

Correctif cumulatif basé sur le FIX6.

## Objectif

Supprimer le faux gain ergonomique qui consistait à déplacer le scroll de la page principale vers la sidebar.

Dans une chanson, les commandes réellement utilisées pendant le travail doivent être visibles immédiatement :
- choix de vue ;
- mode Vue / Édition ;
- capodastre.

## Sidebar chanson

Sur `Chanson` et `Import`, le profil devient compact :
- avatar réduit ;
- nom ;
- rôle.

Les actions globales sont secondaires :
- Répertoire ;
- Profil ;
- Mes éditions ;
- Importer ;
- Administration ;
- Déconnexion.

Elles sont regroupées dans une navigation compacte/repliable afin de ne plus repousser les commandes du morceau vers le bas.

## Commandes du morceau

Le bloc `🎼 Morceau` reste dans le left panel et contient :
- Grille / Paroles + accords / Blocs / Analyse ;
- Vue / Éditer ;
- Capodastre.

Il est placé avant les réglages techniques.

Les réglages avancés restent contextuels à Import / Édition et ne doivent plus être le premier élément utile du panneau.

## Paroles

Le FIX6 est conservé :
- Blocs > Édition = source canonique ;
- mêmes frontières temporelles pour Blocs, Paroles + accords et players ;
- nettoyage des corrections historiques chevauchantes.

## Capodastre

Le FIX6 est conservé :
- grille, Paroles + accords, player et diagrammes suivent le capo ;
- MIDI/audio restent dans l'harmonie réelle ;
- aucune réanalyse.

## Fichiers du livrable

- `EZScore.py`
- `readme.md`
- `ezscore/ui/app_shell.py`
- `ezscore/persistence.py`
- `ezscore/player/web_player.py`
- `ezscore/backoffice/player.py`
