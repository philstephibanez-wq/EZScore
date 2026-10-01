# EZScore_v1 — R39.0.1 — Sections + seeker manuel

Hotfix strictement LyricsLab.

- restaure les sections/chips disparues lors du passage au renderer R39 ;
- conserve leur ordre éditorial et leurs répétitions ;
- ajoute un seeker manuel au-dessus de la timeline LyricsLab ;
- le seeker pilote l'horloge audio via `ezscore:request-seek` ;
- il permet de se positionner précisément avant de modifier un accord ;
- aucune géométrie temporelle n'est modifiée ;
- aucun fichier ChordsLab n'est modifié par l'installateur.

## Installation

```powershell
cd H:\EZScore_v1
tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R39_0_1_SECTIONS_SEEKER.zip" -C H:\EZScore_v1
python .\scripts\install_r39_0_1_sections_seeker.py H:\EZScore_v1
php .\tests\r39_0_1_sections_seeker_contract.php H:\EZScore_v1
php bin\console cache:clear
php bin\console cache:warmup
git status --short
```

Attendu :
- `R39_0_1_SECTIONS_SEEKER_INSTALL_OK`
- `R39_0_1_SECTIONS_SEEKER_CONTRACT_OK`

Test :
1. ouvrir LyricsLab ;
2. vérifier le retour des boutons de sections ;
3. cliquer une section : l'audio se positionne dessus ;
4. déplacer le seeker : audio + timeline suivent ;
5. s'arrêter sur un accord et le modifier ;
6. vérifier que ChordsLab reste inchangé.
