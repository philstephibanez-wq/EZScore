# EZScore_v1 — R38.17C — correction locale du début des paroles

Ce correctif remplace l'approche globale R38.17A/B par une correction strictement locale.

Principe :
- trouver le premier `lexical_anchor` fiable ;
- ne modifier **aucun mot à partir de cet ancrage** ;
- reconstruire uniquement les mots qui le précèdent ;
- utiliser les timestamps Whisper présents avant l'ancrage comme contrôles acoustiques,
  même si leur texte n'a pas été apparié lexicalement ;
- utiliser le `lead_vocals.wav` pour raffiner le début vocal et les noyaux syllabiques ;
- conserver le mot comme unité visuelle ;
- ne toucher à aucun timestamp beat/chord.

L'installateur accepte le dépôt GitHub de base ou un arbre local où R38.17B aurait déjà
été installé.

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_17C_LEADING_PREFIX_ALIGNMENT.zip" -C H:\EZScore_v1

python .\scripts\install_r38_17c_leading_prefix_alignment.py H:\EZScore_v1

php .\tests\r38_17c_leading_prefix_alignment_contract.php H:\EZScore_v1

H:\EZScore_v1\.venv-py313\Scripts\python.exe -m py_compile .\analysis\lyrics_timeline_analysis.py
php -l .\src\Service\LyricsTimelineResultService.php

php bin\console cache:clear
php bin\console cache:warmup

git status --short
```

Attendu :
- `R38_17C_LEADING_PREFIX_ALIGNMENT_INSTALL_OK`
- `R38_17C_LEADING_PREFIX_ALIGNMENT_CONTRACT_OK`

## Test

Relancer **Analyser les paroles** uniquement sur Aline.

Le worker doit ajouter une ligne :

```text
[LYRICS] R38.17C prefix repair: words=...; raw=... ms; repaired_start=... ms;
fixed_anchor=... ms; controls=...
```

`fixed_anchor` et tous les événements qui suivent sont laissés inchangés par la correction.
