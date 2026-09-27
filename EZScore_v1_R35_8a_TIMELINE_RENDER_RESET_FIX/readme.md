# EZScore_v1 — R35.8a TIMELINE / RENDER / RESET FIX

Hotfix du R35.8 rejeté.

## Causes exactes

1. **Mesures vides absentes** : `extend_beats_to_zero()` avait été ajoutée mais n'était jamais appelée. R35.8a la branche réellement après la détection tempo/mètre, puis ajuste la phase métrique.
2. **Crochets `[ ... ]`** : ils étaient injectés par CSS via `.chord-measure-notation::before/::after`, pas par les labels d'accord. R35.8a supprime cette règle et ajoute un override final anti-régression.
3. **Réinitialiser après réanalyse** : `ChordTimelineResultService` sauvegardait puis réappliquait les corrections manuelles sur la nouvelle analyse. R35.8a change la règle : une réanalyse est autoritative et supprime les overrides de l'analyse précédente.

La persistance de la case anti-bruit et le préchargement Opus de R35.8 sont conservés.

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R35_8a_TIMELINE_RENDER_RESET_FIX.zip" -C H:\EZScore_v1

python .\EZScore_v1_R35_8a_TIMELINE_RENDER_RESET_FIX\scripts\apply_r35_8a.py H:\EZScore_v1

php bin\console cache:clear
php bin\console lint:container
php bin\console lint:twig templates
python -m py_compile .\analysis\chord_timeline_analysis.py
php .\EZScore_v1_R35_8a_TIMELINE_RENDER_RESET_FIX\tests\r35_8a_contract.php H:\EZScore_v1

git diff --check
git status --short
```

Attendu :

```text
R35_8A_APPLIED_OK
R35_8A_CONTRACT_OK
```

Ensuite, faire **une seule réanalyse ChordsLab** sur La Bohème.

Vérifier :
- aucun `[ ]` autour des mesures ;
- timeline visible à partir de `0:00` ;
- si le MP3 commence par du silence, les beats correspondants sont `.` ;
- si l'intro contient du piano harmonique, des accords peuvent apparaître dès l'intro ;
- après la réanalyse, `Réinitialiser les accords` n'est plus proposé tant qu'aucune correction manuelle n'a été faite.

Le script ne committe et ne pousse rien.
