# EZScore_v1 — R38.16g — Lyrics.ovh verified results

Corrige les faux boutons **Utiliser**.

La recherche :
- trie les résultats en privilégiant artiste + titre du morceau courant ;
- vérifie réellement la présence de paroles ;
- affiche **Utiliser** seulement si des paroles existent ;
- affiche **Paroles indisponibles** sinon.

Aucune migration.

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_16G_LYRICS_OVH_VERIFIED_RESULTS.zip" -C H:\EZScore_v1

python .\scripts\install_r38_16g_lyrics_ovh_verified_results.py H:\EZScore_v1

php .\tests\r38_16g_lyrics_ovh_verified_results_contract.php H:\EZScore_v1

php -l .\src\Service\LyricsOvhClient.php
php -l .\src\Controller\LyricsOvhController.php

php bin\console cache:clear
php bin\console cache:warmup

git status --short
```

Puis `Ctrl+F5` et relancer la recherche.
