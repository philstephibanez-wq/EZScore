# EZScore_v1 — R38.17 — correction acoustique syllabique des paroles

Objectif : corriger le décalage observé sur Aline sans dégrader les morceaux déjà bons.

- Le premier mot n'est plus forcé sur le premier onset RMS.
- L'onset RMS devient une borne inférieure et peut être recalibré par le premier ancrage lexical fiable.
- Tous les mots source participent au DP global.
- Les trous sont interpolés par cadence syllabique, avec fin de la cascade `+1 ms`.
- Les noyaux de syllabes sont raffinés dans `lead_vocals.wav` par maximum RMS local.
- Symfony conserve `syllables`, `alignment`, `recognized_index`, `cue_ms`.
- Le mot reste l'unité visuelle, mais son point de lecture devient le noyau de sa première syllabe.
- La timeline harmonique n'est pas modifiée.

Aucune migration.

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_17_ACOUSTIC_SYLLABIC_ALIGNMENT.zip" -C H:\EZScore_v1
python .\scripts\install_r38_17_acoustic_syllabic_alignment.py H:\EZScore_v1
php .\tests\r38_17_acoustic_syllabic_alignment_contract.php H:\EZScore_v1
H:\EZScore_v1\.venv-py313\Scripts\python.exe -m py_compile .\analysis\lyrics_timeline_analysis.py
php -l .\src\Service\LyricsTimelineResultService.php
php bin\console cache:clear
php bin\console cache:warmup
git status --short
```

Attendu :
`R38_17_ACOUSTIC_SYLLABIC_ALIGNMENT_INSTALL_OK`
`R38_17_ACOUSTIC_SYLLABIC_ALIGNMENT_CONTRACT_OK`

Validation : relancer **Analyser les paroles** sur Aline, Breakfast in America, La Bohême, Sailing, Joyeux anniversaire.
Le worker doit afficher `[LYRICS] R38.17 vocal timeline: ...`.
