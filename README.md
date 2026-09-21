# EZScore_KARAOKE_DIAG_R2

Base logique :
- `master`
- R1 appliqué localement par l'utilisateur
- diagnostic collecté le 2026-09-21 à 11:07

## Ce que le diagnostic R1 a prouvé

`ezscore_choir_display.log` ne contient que :

`choir.patch.installed`

Il ne contient aucun `choir.display.input`, `choir.display.vocalise` ou
`choir.display.output`.

Donc le splitter R1 était bien installé, mais **jamais appelé par le vrai chemin
du lecteur**.

Cause trouvée : `ezscore/integration/choir_pipeline.py` remplace ensuite
`_derive_choir_words_from_vocals` et le composant R12c lit directement
`choir_analysis.json`. Le wrapper R1 était donc court-circuité.

## Correctifs R2

### 1. Ooooooooo / Aline

Le raffinement des vocalises est maintenant appelé sur la liste
`backing_words` **finale**, issue de `choir_analysis.json`, juste avant l'envoi
au composant navigateur.

Le fichier :

`data/logs/ezscore_choir_display.log`

doit désormais contenir au minimum :
- `choir.display.final.input`
- `choir.display.vocalise` pour les vocalises candidates
- `choir.display.final.output`

### 2. Régression J' avais

R1 avait supprimé toute correction typographique afin de rendre X strictement
temporel. Cela séparait `J'` et `avais`.

R2 conserve la règle temporelle pour tous les mots ordinaires, avec une seule
exception graphique : les contractions séparées par Whisper sont recollées :
- `J'` + `avais`
- `l'` + `amour`
- token commençant par `'` ou `’`

Le timestamp et le highlight de chaque token restent inchangés.

## Installation

```powershell
cd H:\EZScore
tar -xf "$env:USERPROFILE\Downloads\EZScore_KARAOKE_DIAG_R2.zip" -C H:\EZScore

.\.venv-py313\Scripts\python.exe -m py_compile `
  .\ezscore\player\lyrics_layout.py `
  .\ezscore\player\choir_vocalises.py `
  .\ezscore\integration\choir_pipeline.py
```

Relancer complètement EZScore :

```powershell
.\.venv-py313\Scripts\python.exe -m streamlit run EZScore.py
```

Tester Aline sans réanalyse obligatoire : R2 raffine la présentation du
`choir_analysis.json` existant.

Si les O restent collés, envoyer uniquement :

`H:\EZScore\data\logs\ezscore_choir_display.log`
