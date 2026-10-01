# EZScore_v1 — R41.0I Chords + Lyrics compact guitar toggle

Base GitHub exacte : `e1f473758bb813d620c08e00cc740cc1e20d844e` (`cleanup`).

Ce FULL remplace les tentatives H/H1 locales et corrige ChordsLab + LyricsLab ensemble.

## ChordsLab

- OFF : diagramme masqué et réserve verticale R39.3 totalement supprimée.
- ON : diagramme réaffiché immédiatement au temps courant, y compris en pause.
- OFF : `padding-top:0`, `min-height:0`.
- ON : géométrie R39.3 existante conservée (`164 px`, `220 px`).

## LyricsLab

- ON : géométrie existante 392 px conservée.
- OFF : hauteur 236 px.
- Accords / zone de lecture à 18 px.
- Syllabes à 128 px.
- Axe temporel X inchangé.

## Cache Symfony — obligatoire à chaque livraison

Le script exécute automatiquement :

```powershell
php bin\console cache:clear --env=dev
php bin\console cache:clear --env=prod
```

Si l'un des deux échoue, les fichiers suivis sont restaurés et le script s'arrête.

## Installation

```powershell
cd H:\EZScore_v1
git status --short
git rev-parse HEAD
```

Attendu : dépôt propre et HEAD `e1f473758bb813d620c08e00cc740cc1e20d844e`.

Puis :

```powershell
tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R41_0I_CHORDS_LYRICS_COMPACT_TOGGLE.zip" -C H:\EZScore_v1

H:\EZScore_v1\.venv-py313\Scripts\python.exe .\_r41_0i_full\scripts\apply_r41_0i.py H:\EZScore_v1
```

Attendu final :

`R41_0I_CHORDS_LYRICS_COMPACT_TOGGLE_INSTALL_OK`

Sinon : **STOP**.

Puis seulement :

```powershell
H:\EZScore_v1\.venv-py313\Scripts\python.exe .\_r41_0i_full\tests\r41_0i_contract.py H:\EZScore_v1

git diff --check
git status --short
```

Attendu :

`R41_0I_CHORDS_LYRICS_COMPACT_TOGGLE_CONTRACT_OK`
