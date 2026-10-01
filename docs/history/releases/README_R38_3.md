# EZScore_v1 R38.3 — Player/UI + Lyrics clock sync

Corrige les quatre régressions visibles dans LyricsLab.

- Sections: restauration du listener de seek et du highlight pendant la lecture.
- Volume rapide: alias réel du master volume, synchronisé et persisté via `stem_mix_settings`.
- Paroles: `align` utilise désormais la source/original, pas `lead_vocals`, afin de partager exactement la même horloge que le player. `extract` continue à préférer le stem vocal.
- Diagramme d'accord: état mémorisé par chanson dans `localStorage`.

Après installation, relancer **Analyser les paroles** pour recalculer les timestamps sur la source audio.

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_3_PLAYER_UI_SYNC_FIX.zip" -C H:\EZScore_v1

python .\scripts\install_r38_3.py H:\EZScore_v1
python -m py_compile .\worker_app\lyrics_worker_r37.py
php .\tests\r38_3_contract.php H:\EZScore_v1
php bin\console cache:clear
git diff --check
git status --short
```

Attendu:

```text
R38_3_INSTALL_OK
R38_3_CONTRACT_OK
```
