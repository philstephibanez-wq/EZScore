# CDC R39.4 — Worker desktop robuste

Le Worker desktop distingue :

- panne HTTP temporaire : reconnexion automatique, pas de popup bloquante ;
- panne locale fatale : état ERREUR + popup existante.

Le serveur local ne peut pas être arrêté pendant un job actif.
Le Worker ne démarre qu'après disponibilité HTTP du serveur.
