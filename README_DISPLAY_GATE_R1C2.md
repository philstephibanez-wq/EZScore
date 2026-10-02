# EZScore DISPLAY GATE R1.C2

Objectif : un compte `ROLE_DISPLAY` ne voit plus l'application normale.

Après connexion :
- redirection forcée vers `/live/display-home` ;
- si aucune Session Live autorisée : `Aucune session ouverte` ;
- si un LiveRun existe ET que le compte Display est membre du Groupe de la Session :
  - badge TEST/LIVE ;
  - titre ;
  - Chef d'orchestre ;
  - bouton Rejoindre.

Après Rejoindre :
- aucun contrôle transport ;
- choix uniquement `Sans son` / `Son local du rétro` ;
- le Chef d'orchestre restera maître de chanson, play/pause/seek ;
- la synchronisation Lyrics arrive au lot suivant.

ROLE_DISPLAY seul ne suffit pas : membership du Groupe obligatoire.
