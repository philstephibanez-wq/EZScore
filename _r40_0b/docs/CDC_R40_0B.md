# CDC R40.0B — Dual Server Control

## Invariants

1. ONLINE et LOCAL sont deux serveurs distincts et peuvent être actifs simultanément.
2. ONLINE accepte `prod` ou `dev`.
3. LOCAL est toujours `dev`.
4. Maintenance ONLINE est indépendante de `APP_ENV`.
5. Un changement d'environnement ONLINE relance automatiquement son backend.
6. La passerelle ONLINE reste active pendant cette relance et sert une page maintenance.
7. ONLINE et LOCAL ont PID, logs et cache Symfony distincts.
8. Le Worker cible soit ONLINE, soit LOCAL et mémorise ce choix.
9. Tous les modes sont persistés et restaurés au prochain démarrage du Worker.
10. Aucun changement serveur/cible n'est permis pendant un job actif.
11. Aucun fallback CPU et aucune modification du calcul musical.
12. Pas de nouvelle route Symfony de health : `/fr/login` est le contrat de disponibilité.
