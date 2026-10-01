# EZScore_v1 — R38.16j

- aucune sauvegarde automatique à la frappe ;
- bouton **Sauvegarder cette version** toujours visible sous le textarea ;
- historique Restaurer/Poubelle conservé ;
- état dirty `Modifié — non sauvegardé` ;
- navigation interne ou soumission d'un autre formulaire : modale EZScore `Rester sur la page / Quitter sans sauvegarder` ;
- aucune boîte Chrome `alert/confirm/prompt`.

Limitation navigateur : fermeture physique de l'onglet/fenêtre ou F5 ne peut pas afficher une modale HTML personnalisée. `beforeunload` est volontairement absent car il imposerait une boîte native Chrome.

Aucune migration.

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_16J_MANUAL_SAVE_DIRTY_GUARD.zip" -C H:\EZScore_v1

python .\scripts\install_r38_16j_manual_save_dirty_guard.py H:\EZScore_v1

php .\tests\r38_16j_manual_save_dirty_guard_contract.php H:\EZScore_v1

php -l .\src\Service\LyricsOvhClient.php
php -l .\src\Controller\LyricsOvhController.php

php bin\console cache:clear
php bin\console cache:warmup

php bin\console debug:router | Select-String "lyrics_ovh|lyrics_history"

git status --short
```
