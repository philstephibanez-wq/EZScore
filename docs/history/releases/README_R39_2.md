# EZScore_v1 R39.2 — Micro-chevauchements syllabiques

Correction purement visuelle des micro-chevauchements anglais observés sur Dance Me.

Principe :
- aucun changement de `nucleus_ms` ;
- aucun changement de `time_ms -> X` ;
- aucun déplacement horizontal ;
- d'abord légère compaction typographique ;
- si insuffisant, alternance sur deux micro-lignes verticales ;
- ChordsLab strictement inchangé.

## Installation

```powershell
cd H:\EZScore_v1
tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R39_2_LYRIC_COLLISION_LAYOUT.zip" -C H:\EZScore_v1
python .\scripts\install_r39_2_lyric_collision_layout.py H:\EZScore_v1
php .\tests\r39_2_lyric_collision_layout_contract.php H:\EZScore_v1
php bin\console cache:clear
php bin\console cache:warmup
git status --short
```

Attendu :
- `R39_2_LYRIC_COLLISION_LAYOUT_INSTALL_OK`
- `R39_2_LYRIC_COLLISION_LAYOUT_CONTRACT_OK`

## Recette

Sur Dance Me :
1. lancer la lecture ;
2. regarder les passages où deux syllabes se touchaient ;
3. vérifier qu'elles ne se chevauchent plus ;
4. vérifier que le current beat / accord / timing audio sont strictement inchangés ;
5. vérifier Aline rapidement pour s'assurer que la nouvelle disposition verticale reste lisible.
