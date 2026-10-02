# SESSION R1.A/B HOTFIX 1

Corrige uniquement le script d'installation PowerShell.

Cause : les helpers `R/W/X` entraient en collision avec des alias PowerShell (`R` = `Invoke-History`).

Aucun fichier métier n'avait encore été modifié lorsque l'installation a échoué.

Réextraire ce ZIP à la racine de `H:\EZScore` puis relancer la chaîne R1.A/B.
