# EZScore — BS-RoFormer multi-format

Ce livrable ajoute une couche audio modulaire sans modèles, stems ni temporaires dans `H:\EZScore`.

## Fonctionnement

Entrées acceptées : WAV, MP3, FLAC, M4A, OGG, OPUS, AAC, WMA.

Pipeline :

`audio utilisateur -> FFmpeg WAV 44,1 kHz stéréo -> BS-RoFormer -> mix harmonique -> analyse EZScore -> nettoyage`

BS-RoFormer est prioritaire. Demucs reste disponible en secours pour éviter une régression sur un autre environnement.

Pour le mix harmonique BS-RoFormer :
- vocals : exclu
- drums : exclu
- guitar : 1,00
- piano : 1,00
- other : 0,80
- bass : 0,65

## Temporaires

Priorité :
1. `EZSCORE_TEMP_DIR` si définie ;
2. sous Windows, `H:\Temp\EZScore` si `H:\Temp` existe ;
3. sinon le temp système.

Les modèles restent hors dépôt via :
`BS_ROFORMER_MODELS_PATH=H:\EZScoreModels\bs-roformer`

## Dézip

```powershell
New-Item -ItemType Directory -Force H:\Temp\EZScore_BSRoformer_Update | Out-Null
Expand-Archive -Force .\EZScore_BSRoformer_Multiformat.zip H:\Temp\EZScore_BSRoformer_Update
```

## Vérifier le dépôt avant application

```powershell
cd H:\EZScore
git status --short
```

## Appliquer

```powershell
python H:\Temp\EZScore_BSRoformer_Update\apply_integration.py H:\EZScore
```

Le script :
- ajoute `ezscore\audio\__init__.py`
- ajoute `ezscore\audio\separation.py`
- modifie `EZScore.py`
- crée `EZScore.py.before_bs_roformer`
- ne fait aucun commit
- ne fait aucun push

## Compilation

```powershell
cd H:\EZScore
python -m py_compile EZScore.py
python -m py_compile ezscore\audio\__init__.py
python -m py_compile ezscore\audio\separation.py
```

## Test

```powershell
python -m streamlit run EZScore.py
```

La sidebar doit afficher `BS-RoFormer : disponible`.

Tester ensuite un MP3 directement dans l'import EZScore. La conversion WAV est interne et temporaire.

## Contrôle des temporaires

Pendant l'analyse :

```powershell
Get-ChildItem H:\Temp\EZScore -Recurse
```

Après l'analyse, le sous-dossier `ezscore_audio_*` doit avoir disparu.

## Contrôle Git avant ton push

```powershell
cd H:\EZScore
git status --short
git diff -- EZScore.py ezscore/audio/__init__.py ezscore/audio/separation.py
```

Aucun `.ckpt`, stem `.wav` ou fichier temporaire ne doit apparaître.

Après validation :

```powershell
Remove-Item H:\EZScore\EZScore.py.before_bs_roformer
```

Puis tu fais ton commit/push selon ton workflow.
