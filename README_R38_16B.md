# EZScore_v1 — R38.16b

Ergonomie LyricsLab :

- l'input Lyrics.ovh + **Chercher les paroles** sont au même niveau que **Extraire les paroles** et **Analyser les paroles** ;
- les résultats restent sous le bloc de texte ;
- `Source + Commentaire + Sauvegarder cette version` restent toujours visibles sous le bloc texte ;
- seule la liste de l'historique reste repliable.

Aucune migration.

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_16B_LYRICS_TOOLBAR_AND_SAVE.zip" -C H:\EZScore_v1

python .\scripts\install_r38_16b_lyrics_toolbar_and_save.py H:\EZScore_v1

php .\tests\r38_16b_lyrics_toolbar_and_save_contract.php H:\EZScore_v1

php bin\console cache:clear
php bin\console cache:warmup

git status --short
```

Puis `Ctrl+F5`.
