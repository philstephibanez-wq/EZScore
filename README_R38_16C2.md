# EZScore_v1 — R38.16c2

Corrige l'ergonomie Lyrics.ovh :

- un seul input + bouton **Chercher les paroles**, dans la barre avec Extraire/Analyser ;
- suppression de l'ancien champ sous le textarea ;
- correction JS du bouton de recherche ;
- la liste des résultats Lyrics.ovh s'affiche **au-dessus du bloc texte éditable** ;
- aucune migration.

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_16C2_LYRICS_OVH_RESULTS_ABOVE.zip" -C H:\EZScore_v1

python .\scripts\install_r38_16c2_lyrics_ovh_results_above.py H:\EZScore_v1

php .\tests\r38_16c2_lyrics_ovh_results_above_contract.php H:\EZScore_v1

php bin\console cache:clear
php bin\console cache:warmup

git status --short
```

Puis `Ctrl+F5`.
