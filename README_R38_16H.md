# EZScore_v1 — R38.16h — Lyrics.ovh autocomplete

Ajoute une autocomplétion live sous le champ Lyrics.ovh, comme une liste de suggestions standard :

- déclenchement à partir de 2 caractères ;
- debounce 300 ms ;
- 6 suggestions maximum ;
- uniquement les résultats avec paroles réellement disponibles ;
- clic sur une suggestion ;
- navigation clavier avec flèches haut/bas, Entrée et Échap ;
- la sélection remplit le champ puis lance la recherche complète ;
- aucun popup navigateur.

Aucune migration.

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_16H_LYRICS_OVH_AUTOCOMPLETE.zip" -C H:\EZScore_v1

python .\scripts\install_r38_16h_lyrics_ovh_autocomplete.py H:\EZScore_v1

php .\tests\r38_16h_lyrics_ovh_autocomplete_contract.php H:\EZScore_v1

php bin\console cache:clear
php bin\console cache:warmup

git status --short
```

Puis `Ctrl+F5`.
