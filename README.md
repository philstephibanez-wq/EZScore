# EZScore — RIFFSTATION WORKFLOW R8

Base GitHub : `2c420b735ba7eae709f128daaa1d9685b894643b` (`EZScore_RIFFSTATION_WORKSPACE_R7`).

Cette livraison corrige le branchement du workflow produit. Elle ne crée aucun nouveau player, aucun wrapper de monkey-patch et aucun script.

## Ce qui change

- `Analyse` n'expose plus que `1 · STEMS` et `2 · PAROLES`.
- Le Step 1 affiche directement le workspace template-driven déjà livré en R7 : cartouche, formulaire repliable, mixeur repliable, player repliable, diagramme, mire, accords, seeker, vitesse.
- Le Step 1 ne charge ni ne transmet aucune parole au player.
- Le Step 2 réutilise exactement le même workspace et ajoute seulement les mots ancrés.
- Les anciennes étapes `Blocs / structure` et `MIDI` ne font plus partie du workflow produit Analyse.
- Les opérations techniques de régénération STEM restent accessibles dans un expander `Maintenance STEM` sous le workspace.
- Le panneau gauche conserve la navigation globale ; les anciens contrôles chanson sont masqués sur Analyse.

## Installation

Arrêter Streamlit, puis depuis `H:\EZScore` :

```powershell
Expand-Archive "$env:USERPROFILE\Downloads\EZScore_RIFFSTATION_WORKFLOW_R8.zip" -DestinationPath "H:\Temp\EZScore_RIFFSTATION_WORKFLOW_R8" -Force
Copy-Item "H:\Temp\EZScore_RIFFSTATION_WORKFLOW_R8\ezscore\ui\analysis_surface.py" "H:\EZScore\ezscore\ui\analysis_surface.py" -Force
```

Relancer :

```powershell
.\.venv-py313\Scripts\python.exe -m streamlit run EZScore.py --server.address 127.0.0.1 --server.port 8501 --server.headless true
```

## Contrôle visuel attendu

En `Analyse` :

1. uniquement `[1 · STEMS] [2 · PAROLES]` ;
2. immédiatement dessous : cartouche chanson du template R7 ;
3. mixeur STEM repliable ;
4. player repliable ;
5. diagramme optionnel aligné sur la mire ;
6. Step 1 : accords sans ligne paroles ;
7. Step 2 : même écran avec la ligne paroles ajoutée.

Aucun dossier `scripts/`, aucun `apply_*.py`, aucun `test_*.py`.
