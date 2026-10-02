# SESSION R1.A/B HOTFIX 6

Corrige le probleme d'encodage du HOTFIX5.

Le correctif est maintenant execute en PHP et n'utilise aucun litteral non-ASCII
dans le script. Il repare les sequences UTF-8 mojibake du fichier
`translations/event.fr.yaml` et force `event.status.validated` a la valeur UTF-8 canonique.

Commande :
`php .\scripts\fix_session_r1_ab_fr_encoding.php`
