# EZScore_v1 — R35.5a WORKFLOW TABS FIX

Correction ciblée de R35.5.

Le besoin correct est :

**Tableau de bord · Import · Édition · StemsLab · ChordsLab · LyricsLab · Publication**

`Analyse` est renommé **Tableau de bord**, mais les autres onglets du workflow restent présents.

Les verrous sont conservés :
- Stems après Import ;
- Chords après Stems ;
- Lyrics après Chords ;
- Publication après Lyrics.

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R35_5a_WORKFLOW_TABS_FIX.zip" -C H:\EZScore_v1

python .\EZScore_v1_R35_5a_WORKFLOW_TABS_FIX\scripts\apply_r35_5a.py H:\EZScore_v1

php bin\console cache:clear
php bin\console lint:twig templates
php .\EZScore_v1_R35_5a_WORKFLOW_TABS_FIX\tests\r35_5a_contract.php H:\EZScore_v1

git diff --check
git status --short
```

Attendu :
`R35_5A_APPLIED_OK`
`R35_5A_CONTRACT_OK`

Le script ne committe et ne pousse rien.
