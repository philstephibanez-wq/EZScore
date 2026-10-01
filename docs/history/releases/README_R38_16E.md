# EZScore_v1 — R38.16e — Targeted Lyrics.ovh mojibake repair

R38.16d repaired reversible encoding corruption, but the real Lyrics.ovh sample for Christophe / Aline still contains already-damaged tokens.

Observed examples:

```text
prâ¨s  -> près
âgme   -> âme
```

R38.16e adds a deliberately narrow Lyrics.ovh repair table before the generic encoding normalizer.

No Doctrine migration.

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_16E_LYRICS_TARGETED_MOJIBAKE.zip" -C H:\EZScore_v1

python .\scripts\install_r38_16e_lyrics_targeted_mojibake.py H:\EZScore_v1

php .\tests\r38_16e_lyrics_targeted_mojibake_contract.php H:\EZScore_v1

php -l .\src\Service\LyricsTextNormalizer.php

php bin\console cache:clear
php bin\console cache:warmup

git status --short
```

Then run Chercher les paroles -> Utiliser again on Christophe / Aline.
