# EZScore_v1 — R35.9 EDITABLE EMPTY BEATS + RESET FIX

## Fonctionnel

- Toutes les cellules de beat sont éditables, y compris `.`.
- Convention figée : `.` = aucune harmonie ; `-` = accord précédent toujours joué.
- `-` est une convention d'affichage, pas un accord stocké.
- Un accord saisi sur un beat vide crée un événement avec `original="."` + `override=<accord>`.
- `Réinitialiser` peut donc remettre cette cellule à `.`.
- Une réanalyse est autoritative : anciens beats/accords supprimés explicitement via Doctrine avant insertion du nouveau résultat. Cela évite les overrides fantômes qui faisaient réapparaître `Réinitialiser` juste après analyse.
- La timeline depuis `t=0` reste la référence commune pour la future synchronisation LyricsLab/apocopes : le chant pourra démarrer sur des beats `.` avant l'harmonie sans être repoussé vers le premier accord.

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R35_9_EDITABLE_EMPTY_BEATS_RESET_FIX.zip" -C H:\EZScore_v1

python .\EZScore_v1_R35_9_EDITABLE_EMPTY_BEATS_RESET_FIX\scripts\apply_r35_9.py H:\EZScore_v1

php bin\console cache:clear
php bin\console lint:container
php bin\console lint:twig templates
php .\EZScore_v1_R35_9_EDITABLE_EMPTY_BEATS_RESET_FIX\tests\r35_9_contract.php H:\EZScore_v1

git diff --check
git status --short
```

Attendu :

```text
R35_9_APPLIED_OK
R35_9_CONTRACT_OK
```

## Test

1. Réanalyser ChordsLab.
2. `Réinitialiser` doit être absent tant qu'aucune correction manuelle n'existe.
3. Cliquer sur un `.` et saisir `Am`.
4. Le beat devient `Am`; les suivants sans changement restent `-`.
5. `Réinitialiser` apparaît alors.
6. Réinitialiser remet la cellule à `.`.
7. Une nouvelle réanalyse efface les anciennes corrections manuelles.

Aucune migration DB. Aucun commit/push automatique.
