# EZScore_v1 — R38.16d — Correction encodage Lyrics.ovh

Ce correctif ajoute une normalisation **uniquement sur les paroles importées depuis Lyrics.ovh**.

Il traite notamment les mojibakes classiques produits lorsqu'un texte UTF-8 a été décodé auparavant comme :

- Windows-1252 ;
- ISO-8859-1 ;
- MacRoman.

Exemples couverts par le contrat :

```text
FranÃ§ais  -> Français
pr√®s      -> près
```

Un texte UTF-8 déjà propre (`Déjà près de l'âme`) reste strictement inchangé.

Le correctif est volontairement conservateur : il ne tente une réparation que si la ligne contient des marqueurs typiques de mojibake, et ne retient le candidat que si son score d'anomalies est inférieur.

Aucune migration Doctrine.

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_16D_LYRICS_ENCODING_FIX.zip" -C H:\EZScore_v1

python .\scripts\install_r38_16d_lyrics_encoding_fix.py H:\EZScore_v1

php .\tests\r38_16d_lyrics_encoding_fix_contract.php H:\EZScore_v1

php -l .\src\Service\LyricsTextNormalizer.php
php -l .\src\Service\LyricsOvhClient.php

php bin\console cache:clear
php bin\console cache:warmup

git status --short
```

Puis refaire une recherche Lyrics.ovh et **Utiliser** le résultat. La correction intervient avant l'enregistrement de la révision `lyrics_ovh`.
