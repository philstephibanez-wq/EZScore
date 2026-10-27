# 1.0j — diagnostic du refus de récupération FastCGI 8602

MAIN : le listener 8602 PID 28720 a une ligne de commande PHP-CGI apparemment conforme, mais la récupération 1.0h retourne `DEV_FASTCGI_RECOVERY_IDENTITY_MISMATCH`. Cette erreur regroupe un éventuel échec du filtre TCP `LocalAddress=127.0.0.1` et de l'identité CIM. L'action `scripts/dev-fastcgi.cmd diagnose` est **strictement lecture seule** et montre chaque écouteur, adresse, PID et résultats des comparaisons d'identité, sans écrire ni arrêter quoi que ce soit. Aucune modification de la politique de refus de `recover`, `start` ou `stop`.

Recette MAIN : `php tests/dev_fastcgi_diagnostic_contract.php`, parser PowerShell sur le script, `scripts/dev-fastcgi.cmd diagnose`. Ne pas lancer `recover` tant que la cause n'est pas identifiée. Caddy, 8502, PROD et médias inchangés.
