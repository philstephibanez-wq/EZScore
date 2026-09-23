# EZScore_RIFFSTATION_WORKSPACE_R13

Base de travail : R12, elle-même livrée depuis le master GitHub R8 `c860c3d898d6a4d7ce1dadb3399d581b2fb392a2`.

Cette livraison corrige précisément les défauts constatés dans la vidéo R12 :

- **Assets du composant forcés à se recharger** : le composant Streamlit v2 porte maintenant un nouvel identifiant `ezscore_karaoke_stem_player_r13`. R12 gardait le nom historique `...r12c`, ce qui permettait au navigateur de réutiliser l'ancien JavaScript ; c'est la raison pour laquelle l'écran montrait encore un accord brut par beat malgré le nouveau code `Em--- / Em-.-` présent sur disque.
- **Navigation STEMS/PAROLES sans rebouclage** : le composant n'écrit plus un état persistant `active_step`. Un clic émet désormais une requête ponctuelle `{step, token}` ; Python consomme chaque token une seule fois. Un vieux rerun ne peut donc plus réactiver l'onglet précédent.
- **Notation compacte par mesure réellement chargée** : la rangée d'accords utilise `measureNotation()` et affiche les occupations `Em---`, `Em-.-`, `D-G-`, etc. Les points restent des beats non joués et les tirets des tenues.
- **Message d'attente avant analyse HQ** : lorsque ni cache Step 1, ni structure, ni analyse persistée ne sont disponibles, le statut est envoyé au navigateur avant le calcul bloquant madmom/lv-chordia.

La timeline audio et les timestamps ne sont pas modifiés.

## Installation

Arrêter complètement Streamlit avant la copie.

```powershell
cd H:\EZScore

$pkg = "$env:USERPROFILE\Downloads\EZScore_RIFFSTATION_WORKSPACE_R13.zip"
$tmp = "H:\Temp\EZScore_RIFFSTATION_WORKSPACE_R13"

Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $tmp -Force | Out-Null
Expand-Archive $pkg -DestinationPath $tmp -Force

Copy-Item "$tmp\ezscore\ui\analysis_surface.py" `
  "H:\EZScore\ezscore\ui\analysis_surface.py" -Force
Copy-Item "$tmp\ezscore\player\karaoke_stem_webaudio_r12c.py" `
  "H:\EZScore\ezscore\player\karaoke_stem_webaudio_r12c.py" -Force
Copy-Item "$tmp\templates\views\analysis-workspace-shell.score" `
  "H:\EZScore\templates\views\analysis-workspace-shell.score" -Force
Copy-Item "$tmp\templates\views\riffstation-workspace.score" `
  "H:\EZScore\templates\views\riffstation-workspace.score" -Force
Copy-Item "$tmp\templates\views\riffstation-workspace.css" `
  "H:\EZScore\templates\views\riffstation-workspace.css" -Force
Copy-Item "$tmp\templates\views\riffstation-workspace.js" `
  "H:\EZScore\templates\views\riffstation-workspace.js" -Force
```

Relancer ensuite :

```powershell
.\.venv-py313\Scripts\python.exe -m streamlit run EZScore.py --server.address 127.0.0.1 --server.port 8501 --server.headless true
```

## Contrôle visuel attendu

1. La ligne d'accords montre des **mesures compactes** (`Em---`, `Em-.-`, etc.), et non une suite `G  Em  Em  C  C ...`.
2. `STEMS -> PAROLES -> STEMS` reste stable, sans clignotement.
3. Diagramme et accord courant restent sur la mire.
4. En Step 2, le mot courant reste sur cette même mire.
5. Si une analyse HQ est nécessaire, le statut est visible avant les lignes `Inference:` du terminal.

Aucun `scripts/`, aucun `apply_*.py`, aucun `test_*.py`, aucun `__pycache__` n'est livré.
