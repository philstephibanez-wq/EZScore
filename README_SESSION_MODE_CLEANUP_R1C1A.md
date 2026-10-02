# EZScore SESSION MODE CLEANUP R1.C1A

Corrige deux incohérences constatées pendant le test réel sur rétroprojecteur.

1. `Mode Présentiel / À distance / Hybride` est supprimé de la Session.
   Le mode appartient au participant, pas à la Session.
2. Le bouton topbar `Session` ne doit plus ouvrir l'ancien POC `/concert/control`.
   Il ouvre maintenant la vraie liste des Sessions EZScore.

Nettoyage sans dette :
- suppression de `EventMode` du domaine ;
- suppression de la colonne SQL `events.mode` ;
- suppression UI/filtres/traductions ;
- suppression de `EventMode.php`.

Le POC historique ConcertSession peut rester momentanément comme brique technique interne, mais il n'est plus accessible via l'UX Session.
