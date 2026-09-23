# EZScore — Riffstation workspace R7

Base : `master` / commit `638e90917c40b90f3b201225b64848b7f21db2cc` (`EZScore_STEP1_RIFFSTATION_STEMS_R3`).

## Principe

Cette livraison ne crée aucun nouveau composant Python parallèle et ne contient aucun script de patch/test.

La vue du player est définie dans :

- `templates/views/riffstation-workspace.score`
- `templates/views/riffstation-workspace.css`
- `templates/views/riffstation-workspace.js`

Le module Python déjà existant `ezscore/player/karaoke_stem_webaudio_r12c.py` ne fait que préparer les données, persister le cartouche et instancier le composant existant à partir du template SCORE.

## Workflow

- Analyse n'expose plus que `1 · STEM` et `2 · Paroles`.
- Step 1 : STEMS + mixage + player + beats/accords + diagramme optionnel, sans paroles.
- Step 2 : même player et même timeline musicale, avec la lane paroles en plus.
- Les timestamps ne sont jamais modifiés par la représentation.
- Les beats sont espacés régulièrement à l'écran ; la projection des paroles est indépendante pour garder le mot courant sous la mire.
- À t=0, aucun beat futur n'est placé à gauche de la mire.
- Vitesse : 0,50× à 1,50×, avec conservation de hauteur via les propriétés natives du navigateur.

## Cartouche

Toujours en tête du workspace : titre, auteur/interprète, éditeur, time signature, capo et strum. Le formulaire est repliable.

- l'éditeur vient en priorité de `song_editor_assignments` ;
- la liste d'éditeurs est modifiable uniquement par un admin ;
- time signature et capo utilisent `song_preferences` ;
- la mise à jour Streamlit passe par `_pending_song_preferences`, donc aucune écriture d'une clé de widget déjà instanciée.

## Timeline

Ordre de chargement :

1. `riffstation_step1.json` ;
2. `structure_analysis.json` existante ;
3. calcul HQ Step 1 si aucune timeline exploitable n'existe.

Aucun fallback librosa n'est utilisé pour les beats. `rhythm_quality.py` accepte les deux API madmom-infer rencontrées selon les versions (`features.beats` ou `features.downbeats`).

## Installation

Arrêter Streamlit puis, depuis PowerShell :

```powershell
cd H:\EZScore
$pkg = "$env:USERPROFILE\Downloads\EZScore_RIFFSTATION_WORKSPACE_R7.zip"
$tmp = "H:\Temp\EZScore_RIFFSTATION_WORKSPACE_R7"

Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $tmp -Force | Out-Null
tar -xf $pkg -C $tmp

Copy-Item "$tmp\ezscore\analysis\rhythm_quality.py" "H:\EZScore\ezscore\analysis\rhythm_quality.py" -Force
Copy-Item "$tmp\ezscore\player\karaoke_stem_webaudio_r12c.py" "H:\EZScore\ezscore\player\karaoke_stem_webaudio_r12c.py" -Force
Copy-Item "$tmp\ezscore\ui\analysis_surface.py" "H:\EZScore\ezscore\ui\analysis_surface.py" -Force
Copy-Item "$tmp\templates\views\riffstation-workspace.score" "H:\EZScore\templates\views\riffstation-workspace.score" -Force
Copy-Item "$tmp\templates\views\riffstation-workspace.css" "H:\EZScore\templates\views\riffstation-workspace.css" -Force
Copy-Item "$tmp\templates\views\riffstation-workspace.js" "H:\EZScore\templates\views\riffstation-workspace.js" -Force
```

Compilation rapide, sans script ajouté au dépôt :

```powershell
.\.venv-py313\Scripts\python.exe -m py_compile `
  .\ezscore\analysis\rhythm_quality.py `
  .\ezscore\player\karaoke_stem_webaudio_r12c.py `
  .\ezscore\ui\analysis_surface.py
```

Puis relancer :

```powershell
.\.venv-py313\Scripts\python.exe -m streamlit run EZScore.py --server.address 127.0.0.1 --server.port 8501 --server.headless true
```

## À vérifier avant push

1. panneau gauche : plus de Mode / Time signature / Capodastre dans Analyse ;
2. seulement deux étapes : STEM / Paroles ;
3. Step 1 : aucune parole ;
4. diagramme exactement au-dessus de la mire ;
5. beat courant centré sur la mire ;
6. Step 2 : mot courant maintenu sur la même mire ;
7. cartouche et formulaire repliable présents ;
8. vitesse de lecture fonctionnelle ;
9. éditeur correctement affiché depuis l'affectation utilisateur.

Ne pousser qu'après ce contrôle visuel.
