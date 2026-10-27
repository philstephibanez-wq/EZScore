# 1.0k2 — correction de duplication accidentelle du script 1.0k1

La génération JavaScript du script 1.0k1 a interprété la séquence `$'` dans le remplacement et dupliqué la fin du fichier. 1.0k2 reprend exactement la base 1.0j confirmée par GitHub (6009 caractères), puis insère le changement d'identité via un remplacement littéral sans interprétation. Vérification d'une seule section `status` et d'une seule fonction Identity. Aucune action sur les processus ; tests PowerShell MAIN requis avant toute commande.
