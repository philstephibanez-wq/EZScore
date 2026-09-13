# EZScore R21 — back-office, player d’édition et modularisation

## Architecture produit

EZScore distingue désormais explicitement deux espaces.

### Back-office — mode Édition

Le mode Édition est le back-office. Il regroupe l’analyse, la correction de grille et de paroles, la structure du morceau, les métadonnées, le workflow version/édition/publication et les outils de contrôle.

Le player MP3 + MIDI est un outil de contrôle du back-office. Il est affiché directement dans les vues Grille et Paroles + accords lorsque le morceau est en mode Édition. Le mode séparé Jouer est supprimé pour cette fonction.

Le MP3 reste l’horloge maître. Le MIDI est généré depuis la grille effective, corrections manuelles comprises.

### Front-office — lecture publiée

Le player définitif sera basé sur le même transport MP3, sans MIDI. Il utilisera un ruban temporel continu : contenu se déplaçant de droite vers gauche, position courante centrée, passé à gauche et anticipation permanente à droite. Pas de pagination pendant la lecture, pas de saut de page et pas de scroll horizontal utilisateur.

Le ruban pourra afficher les accords, les paroles ou les deux.

## Diagrammes et voicings guitare

L’affichage d’un diagramme d’accord sera optionnel. Un accord musical et sa position guitare sont deux données distinctes : par exemple Am peut être ouvert, barré case V, barré case XII ou utiliser un autre voicing.

En édition, l’objectif est de permettre de choisir explicitement le voicing voulu accord par accord, avec aperçu du diagramme. Les éditions Simplifiée / Standard / Avancée pourront proposer des voicings différents sans modifier la timeline harmonique.

## Authentification / autorisation

Une fondation RBAC modulaire est introduite dans ezscore/auth/ :

- admin : tous les droits ;
- editor : import, analyse, édition, validation et publication ;
- reader : lecture ;
- anonymous : contenu public uniquement.

Le contrat prévoit une authentification par e-mail et une couche OAuth/OIDC pour Google et fournisseurs sociaux. Aucun faux login n’est exposé : l’intégration réelle des providers viendra sur cette fondation. Les autorisations doivent être contrôlées côté application et pas seulement par masquage de boutons.

## Responsive

Une couche responsive dédiée est introduite dans ezscore/ui/responsive.py : cibles tactiles, adaptation des colonnes et typographies, prévention du scroll horizontal de page, comportement tablette et smartphone.

Le futur ruban de lecture restera continu sur mobile : la quantité d’anticipation diminuera avec la largeur disponible, mais le principe temporel restera identique.

## Modularisation

R21 sort une nouvelle responsabilité de EZScore.py : le player de comparaison d’édition est maintenant dans ezscore/backoffice/player.py. La suite du développement doit continuer dans ce sens : EZScore.py orchestre, les modules portent les responsabilités métier et UI.

Nouveaux modules :

- ezscore/backoffice/player.py
- ezscore/ui/responsive.py
- ezscore/auth/roles.py

## Livrable

Le ZIP contient uniquement les fichiers modifiés ou ajoutés par R21 :

- EZScore.py
- readme.md
- ezscore/backoffice/__init__.py
- ezscore/backoffice/player.py
- ezscore/ui/__init__.py
- ezscore/ui/responsive.py
- ezscore/auth/__init__.py
- ezscore/auth/roles.py

Dézipper dans H:\\EZScore en conservant l’arborescence.
