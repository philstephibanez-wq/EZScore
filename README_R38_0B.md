# R38.0b

Corrige :
- WinError 5 sur progress.json via temp unique + retry os.replace ;
- cache navigateur : Twig passe les assets LyricsLab en r38_0b ;
- le nouveau prompteur read-only est donc réellement chargé ;
- polling de progression conservé.

Commandes :
cd H:\EZScore_v1
tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_0B_PROGRESS_IO_CACHE_FIX.zip" -C H:\EZScore_v1
python .\scripts\install_r38_0b.py H:\EZScore_v1
python -m py_compile .\analysis\lyrics_timeline_analysis.py
php .\tests\r38_0b_contract.php H:\EZScore_v1
php bin\console cache:clear
git diff --check
git status --short

Attendu:
R38_0B_INSTALL_OK
R38_0B_CONTRACT_OK

Puis Ctrl+F5 et relancer Analyser les paroles.
