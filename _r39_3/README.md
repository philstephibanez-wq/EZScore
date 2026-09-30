# EZScore_v1 — R39.3 Consolidated Prompter

Base unique : `bcd7448da6e7e0b81d950859545043e9f80da504`
(`EZScore_v1_R39_2F_MOVE_VISUAL_SETTINGS_LYRICS`).

Ce lot remplace toute la série locale R39.2I/K/L/M/N/O/P/P1.

## Architecture

Le suivi horizontal reprend le principe historique R37.2 / R38.1 :

- viewport fixe ;
- ruban interne déplacé par `translate3d()` ;
- aucune limitation `scrollLeft >= 0` ;
- suivi disponible dès la première mesure ;
- position interpolée entre beat courant et beat suivant avec l'horloge canonique.

Le diagramme et le moteur de focus sont deux composants partagés :

- `public/assets/js/components/ezscore-chord-diagram.js`
- `public/assets/css/components/ezscore-chord-diagram.css`
- `public/assets/js/components/ezscore-focus-track.js`

Ils sont réutilisables ensuite dans Lyrics/Karaoke.

## UI

- diagramme fixe sur l'axe focal ;
- 25 % desktop, 30 % tablette, 38 % mobile ;
- carte blanche 150 px ;
- grille noire ;
- cartouche noir ;
- `Profil affiché` supprimé ;
- visual settings R39.2D/F conservés.

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R39_3_CONSOLIDATED_PROMPTER.zip" -C H:\EZScore_v1

H:\EZScore\.venv-py313\Scripts\python.exe .\_r39_3\scripts\apply_r39_3.py H:\EZScore_v1

H:\EZScore\.venv-py313\Scripts\python.exe .\_r39_3\tests\r39_3_consolidated_prompter_contract.py H:\EZScore_v1

php bin\console cache:clear

git diff --check
git status --short
```

Attendu :

```text
R39_3_CONSOLIDATED_PROMPTER_INSTALL_OK
R39_3_CONSOLIDATED_PROMPTER_CONTRACT_OK
```

## Validation visuelle

1. Ouvrir Chords.
2. Lancer Lecture.
3. Dès la première mesure, le ruban doit pouvoir se déplacer sous l'axe du diagramme.
4. Le mouvement doit suivre le temps entre les beats, et non attendre la mesure 5.
5. La mesure courante reste rouge et le beat courant reste surligné.
