# EZScore_RIFFSTATION_WORKSPACE_R16

Livraison complète de remplacement, sans script, basée sur le `master` poussé `47d40c61dfe04c80fd323ef3717ea25900b782c5` (`EZScore_RIFFSTATION_WORKSPACE_R15`).

## Objet R16

- Une **case = un beat**.
- Les beats sont regroupés visuellement par mesure et le **numéro de mesure** est affiché.
- Exemple 4/4 : `#12 [Cm | - | - | -]`.
- Si Cm continue à la mesure suivante : `#13 [Cm | - | - | -]` — le premier beat de chaque mesure réaffiche l'accord.
- Plusieurs accords dans une mesure sont conservés, par exemple `[Em | - | G | F]` en 4/4 ou `[Em | G]` en 2/4.
- Seule la case correspondant au **beat courant** s'allume.
- Le diagramme reste au-dessus de la mire commune.
- En Step 2, tous les mots restent sur **une seule ligne de vers** ; le mot courant est mis en évidence sur cette même ligne et centré sous la mire. Il n'existe plus de mot courant flottant sur une autre ligne.
- La timeline audio n'est pas modifiée.
- Le moteur WebAudio et le mixeur temps réel de R15 sont conservés sans changement fonctionnel.

## Fichiers à remplacer

Uniquement les fichiers modifiés :

- `ezscore/player/karaoke_stem_webaudio_r12c.py`
- `templates/views/riffstation-workspace.score`
- `templates/views/riffstation-workspace.css`
- `templates/views/riffstation-workspace.js`

## Installation PowerShell

Arrêter Streamlit avant copie.

```powershell
cd H:\EZScore

$pkg = "$env:USERPROFILE\Downloads\EZScore_RIFFSTATION_WORKSPACE_R16.zip"
$tmp = "H:\Temp\EZScore_RIFFSTATION_WORKSPACE_R16"

Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $tmp -Force | Out-Null
Expand-Archive $pkg -DestinationPath $tmp -Force

Copy-Item "$tmp\ezscore\player\karaoke_stem_webaudio_r12c.py" "H:\EZScore\ezscore\player\karaoke_stem_webaudio_r12c.py" -Force
Copy-Item "$tmp\templates\views\riffstation-workspace.score" "H:\EZScore\templates\views\riffstation-workspace.score" -Force
Copy-Item "$tmp\templates\views\riffstation-workspace.css" "H:\EZScore\templates\views\riffstation-workspace.css" -Force
Copy-Item "$tmp\templates\views\riffstation-workspace.js" "H:\EZScore\templates\views\riffstation-workspace.js" -Force

.\.venv-py313\Scripts\python.exe -m py_compile `
  .\ezscore\player\karaoke_stem_webaudio_r12c.py

.\.venv-py313\Scripts\python.exe -m streamlit run EZScore.py `
  --server.address 127.0.0.1 `
  --server.port 8501 `
  --server.headless true
```

## Contrôle visuel

1. En 4/4, vérifier un groupe de quatre cases : `[# accord | beat 2 | beat 3 | beat 4]` sous un numéro de mesure.
2. Pour un accord tenu sur quatre beats, vérifier `[Cm | - | - | -]`.
3. À la mesure suivante avec le même accord, vérifier que Cm est répété : `[Cm | - | - | -]` et non `[- | - | - | -]`.
4. Pendant la lecture, vérifier que **seule la case du beat courant** est éclairée.
5. En Step 2, vérifier que le mot courant reste dans la même baseline que les mots précédents/suivants et se retrouve sous la mire.
6. Vérifier que le mixeur STEM reste modifiable en temps réel pendant la lecture.
