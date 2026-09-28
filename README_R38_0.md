# R38.0
Source éditoriale unique + sections + prompteur read-only.

Installation:
cd H:\EZScore_v1
tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_0_STRUCTURED_LYRICS_SIMPLE_PROMPTER.zip" -C H:\EZScore_v1
python .\scripts\install_r38.py H:\EZScore_v1
python -m py_compile .\analysis\lyrics_timeline_analysis.py
php .\tests\r38_0_contract.php H:\EZScore_v1
php bin\console cache:clear
git diff --check
git status --short

Attendu:
R38_INSTALL_OK
R38_0_CONTRACT_OK

Puis Ctrl+F5 et relancer Analyser les paroles.
