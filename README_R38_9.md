# EZScore_v1 R38.9 — ancien alignement + offset acoustique

Principe:
- conserver le détecteur R38.8 de première syllabe;
- remettre l'ancien alignement global SequenceMatcher/interpolation;
- calculer `offset = T0_acoustique - T0_ancien`;
- appliquer exactement le même offset à toute la timeline paroles;
- verrouiller le premier mot à T0;
- ne plus afficher le traceback Python brut dans LyricsLab.

Installation:
```powershell
cd H:\EZScore_v1
tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_9_LEGACY_PLUS_ACOUSTIC_OFFSET.zip" -C H:\EZScore_v1
python .\scripts\install_r38_9.py H:\EZScore_v1
python -m py_compile .\analysis\lyrics_timeline_analysis.py
php .\tests\r38_9_contract.php H:\EZScore_v1
python .\tests\test_r38_9_offset_contract.py H:\EZScore_v1
php bin\console cache:clear
```
Puis redémarrer le Worker et relancer l'analyse LyricsLab.
