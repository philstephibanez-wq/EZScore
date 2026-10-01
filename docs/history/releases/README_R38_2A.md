# R38.2A — restauration barre de progression LyricsLab

Régression R38.2 :
le JS utilisé pour R38.2 provenait du ruban R38.1A, qui n'embarquait plus le polling de
`data-lyrics-progress`.

R38.2A rétablit :
- affichage `queued` ;
- progression `running` ;
- pourcentage ;
- message extract / align ;
- erreur ;
- 100 % + reload final.

Aucune modification du Worker, de l'analyse, des profils ou du mail admin.

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_2A_PROGRESS_BAR_RESTORE.zip" -C H:\EZScore_v1

python .\scripts\install_r38_2a.py H:\EZScore_v1

php .\tests\r38_2a_contract.php H:\EZScore_v1

php bin\console cache:clear

git diff --check
git status --short
```

Attendu :

```text
R38_2A_INSTALL_OK
R38_2A_CONTRACT_OK
```

Puis `Ctrl+F5`.
