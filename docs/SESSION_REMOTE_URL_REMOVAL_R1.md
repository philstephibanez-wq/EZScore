# SESSION REMOTE URL REMOVAL R1

Décision produit : une Session EZScore ne possède aucun `remote_url` saisi par l'utilisateur.

Le lien distant est toujours l'URL permanente EZScore de la Session, générée par l'application.

Ce lot supprime :
- la propriété `Event::$remoteUrl` ;
- getter/setter ;
- lecture du champ dans `EventController` ;
- champs UI création/édition ;
- affichage résumé ;
- traductions ;
- colonne SQL `events.remote_url`.

Migration : `Version20261002183000`.
