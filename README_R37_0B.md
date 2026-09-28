# R37.0b — Route LyricsLab extraction

Corrige uniquement l'absence de route Symfony `app_song_lyricslab_extract`.

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R37_0B_LYRICS_ROUTE_FIX.zip" -C H:\EZScore_v1

python .\scripts\apply_r37_0b.py H:\EZScore_v1

php -l .\src\Controller\SongLabController.php
php bin\console cache:clear
php bin\console debug:router | Select-String "lyricslab_extract|lyricslab_analyze|lyricslab_status"

php .\tests\r37_0b_contract.php H:\EZScore_v1
```

Attendu :

```text
R37_0B_APPLIED_OK
app_song_lyricslab_extract
R37_0B_CONTRACT_OK
```
