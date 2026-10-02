# EZScore ROLE_DISPLAY R1B STRICT

Ce lot ne fait plus de remplacement tolérant silencieux.

L'installateur échoue si le code local attendu n'est pas trouvé, et le contrat vérifie le comportement réel de `User::setRoles()` / `getPrimaryRole()`.

Après installation et test, `role_display_r1b_db_diag.php` permet de voir la valeur réellement stockée dans `users.roles`.
