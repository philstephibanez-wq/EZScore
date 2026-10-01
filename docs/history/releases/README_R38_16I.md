# EZScore_v1 — R38.16i — Fast Lyrics.ovh autocomplete

R38.16h était fonctionnel mais lent car chaque frappe utilisait la recherche vérifiée R38.16g, qui teste `/v1/{artist}/{title}` pour plusieurs résultats.

R38.16i sépare les deux flux :

- **autocomplete live** : endpoint Symfony léger, uniquement `/suggest/{query}`, debounce 140 ms, annulation de requête précédente, cache navigateur des 40 dernières recherches ;
- **Chercher les paroles / sélection finale** : conserve la recherche vérifiée et les boutons `Utiliser` uniquement quand les paroles existent.

Aucune migration.

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_16I_FAST_AUTOCOMPLETE.zip" -C H:\EZScore_v1

python .\scripts\install_r38_16i_fast_autocomplete.py H:\EZScore_v1

php .\tests\r38_16i_fast_autocomplete_contract.php H:\EZScore_v1

php -l .\src\Service\LyricsOvhClient.php
php -l .\src\Controller\LyricsOvhController.php

php bin\console cache:clear
php bin\console cache:warmup
php bin\console debug:router | Select-String "lyrics_ovh_autocomplete"

git status --short
```

Puis `Ctrl+F5`.
