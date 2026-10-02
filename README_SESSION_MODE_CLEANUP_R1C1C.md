# EZScore SESSION MODE CLEANUP R1.C1C

Récupération stricte après les échecs R1.C1A/R1.C1B.

Ce lot part explicitement de l'état potentiellement partiel du dépôt local et :
- supprime les résidus `EventMode` dans `Event.php` et `EventController.php` ;
- retire le mode Session de l'UI et des filtres ;
- supprime `EventMode.php` ;
- conserve le LiveRun R1.C1 ;
- fait pointer le bouton topbar Session vers la vraie page Sessions ;
- installe la migration de suppression `events.mode` si elle n'est pas déjà présente.

Aucun push avant validation technique + UI.
