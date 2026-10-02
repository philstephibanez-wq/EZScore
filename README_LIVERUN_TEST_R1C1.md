# EZScore LiveRun TEST R1.C1

Premier incrément exécutable du POC projection.

## Ce lot fait
- ajoute `LiveRun` persistant ;
- ajoute la migration `live_runs` ;
- ajoute `Tester la session` / `Arrêter le test` sur la Session du Chef ;
- n'envoie aucune invitation lors du test ;
- ajoute une notification globale pour `ROLE_DISPLAY` ;
- permet au Display passif de rejoindre un écran de test ;
- propose le choix audio `none / local_display / conductor_local` dans l'UI de Display.

## Ce lot ne fait pas encore
- synchronisation Lyrics ;
- chanson courante ;
- play/pause/seek ;
- audio réellement routé.

C'est volontaire : on valide d'abord Session → LiveRun → notification → Display réel.

## Installation
Voir commande fournie dans le chat.
