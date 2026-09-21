# EZScore_KARAOKE_DIAG_R1

Base : `master` / `origin/master`
HEAD de départ : `45f0bcb`

## Inclus

1. **Karaoké Chant / Chœurs**
   - X dépend uniquement du timestamp.
   - suppression du déplacement horizontal indépendant anti-chevauchement.
   - même temps = même X sur Chant et Chœurs.

2. **Aline / Ooooooooo**
   - segmentation acoustique plus permissive ;
   - onset + flux spectral + attaques RMS ;
   - journal `data/logs/ezscore_choir_display.log`.

3. **Langue Whisper**
   - consensus sur plusieurs fenêtres énergétiques du morceau ;
   - évite qu'une intro trompe la détection et francise un morceau anglais.

4. **Python 3.13 / Demucs**
   - ajout `demucs==4.1.0` au requirement ;
   - vérification de l'import dans le script d'installation.

5. **Audit stems / stem_lab**
   - `scripts/audit_analysis_storage.py`
   - recherche des vrais doublons SHA-256 ;
   - aucune suppression automatique.

6. **Remontée diagnostics**
   - `scripts/collect_ezscore_diagnostics.ps1`
   - génère un ZIP de logs/état Git/liste des artefacts JSON sans audio.

## Installation

```powershell
cd H:\EZScore
tar -xf "$env:USERPROFILE\Downloads\EZScore_KARAOKE_DIAG_R1.zip" -C H:\EZScore

.\.venv-py313\Scripts\python.exe -m py_compile `
  .\ezscore\player\lyrics_layout.py `
  .\ezscore\player\choir_vocalises.py `
  .\ezscore\analysis\whisper_policy.py `
  .\ezscore\analysis\__init__.py `
  .\scripts\audit_analysis_storage.py

powershell -ExecutionPolicy Bypass -File .\scripts\install_analysis_hq.ps1
```

Puis :

```powershell
.\.venv-py313\Scripts\python.exe -m streamlit run EZScore.py
```

## Tests

### Aline
Tester le même passage `Ooooooooo`. Si le texte reste collé, envoyer :

`H:\EZScore\data\logs\ezscore_choir_display.log`

### Gospel anglais
Il faut **ré-analyser les paroles** afin de ne pas réutiliser le cache créé avec
l'ancienne détection de langue.

### Doublons
```powershell
.\.venv-py313\Scripts\python.exe .\scripts\audit_analysis_storage.py
```

### Blocage upload / remontée générale
Après redémarrage, lancer :

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\collect_ezscore_diagnostics.ps1
```

et envoyer le ZIP créé dans `data\logs`.
