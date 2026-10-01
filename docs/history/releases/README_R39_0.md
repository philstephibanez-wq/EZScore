# EZScore_v1 R39.0 — Timeline canonique + rendu syllabique

- ChordsLab reste la référence fonctionnelle.
- Nouveau moteur temporel commun.
- ChordsLab l'utilise pour projection beat/mesure et current beat, sans changer son smooth scroll.
- LyricsLab utilise le même axe `time_ms -> X`.
- Pas de warp temporel dans le nouveau renderer LyricsLab.
- Affichage syllabé avec tirets.
- Édition des accords dans LyricsLab via le même beat override que ChordsLab.
- CDC complet du pipeline Whisper -> forced aligner phonétique -> phonèmes -> syllabes -> timeline.
- Aucun timestamp beat/chord modifié.
- Aucune migration.

Le forced aligner phonétique n'est pas installé dans ce bundle : son pipeline et son contrat sont désormais figés, et le renderer R39 consomme déjà les `nucleus_ms` lorsqu'ils existent.

## Installation

```powershell
cd H:\EZScore_v1
tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R39_0_CANONICAL_TIMELINE_SYLLABLES.zip" -C H:\EZScore_v1
python .\scripts\install_r39_0_canonical_timeline_syllables.py H:\EZScore_v1
php .\tests\r39_0_canonical_timeline_syllables_contract.php H:\EZScore_v1
php bin\console cache:clear
php bin\console cache:warmup
git status --short
```

Attendu :
`R39_CANONICAL_TIMELINE_SYLLABLES_INSTALL_OK`
`R39_CANONICAL_TIMELINE_SYLLABLES_CONTRACT_OK`

Recette prioritaire : ChordsLab d'abord, puis LyricsLab au même timestamp, puis édition d'un accord dans LyricsLab.
