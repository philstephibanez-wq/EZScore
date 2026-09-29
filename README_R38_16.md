# EZScore_v1 — R38.16 — Lyrics.ovh API

Intégration de Lyrics.ovh directement dans **EZScore_v1 / LyricsLab**.

## Fonctionnement

Dans le bloc `Paroles source` :

- input de recherche prérempli avec `artiste + titre` ;
- bouton **Chercher les paroles** ;
- recherche via `https://api.lyrics.ovh/suggest/{query}` ;
- liste de résultats ;
- bouton **Utiliser** ;
- récupération via `https://api.lyrics.ovh/v1/{artist}/{title}` ;
- sauvegarde automatique du bloc courant avant remplacement ;
- création d'une révision R38.15 de source `lyrics_ovh` avec commentaire automatique.

Tous les appels Lyrics.ovh passent par Symfony côté serveur.

Aucune nouvelle migration Doctrine.

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_16_LYRICS_OVH.zip" -C H:\EZScore_v1

python .\scripts\install_r38_16_lyrics_ovh.py H:\EZScore_v1

php .\tests\r38_16_lyrics_ovh_contract.php H:\EZScore_v1

php -l .\src\Service\LyricsOvhClient.php
php -l .\src\Controller\LyricsOvhController.php

php bin\console cache:clear
php bin\console cache:warmup

php bin\console debug:router | Select-String "lyrics_ovh"

git status --short
```

Attendu :

```text
R38_16_LYRICS_OVH_INSTALL_OK
R38_16_LYRICS_OVH_CONTRACT_OK
```

Puis `Ctrl+F5` dans LyricsLab.
