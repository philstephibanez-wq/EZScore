# EZScore — STEP1_RIFFSTATION_STEMS_R3

Base GitHub : `master` / `1294ef6e3950a5a83c218832ad3f193ce1977e38` (`EZScore_STEP1_RIFFSTATION_STEMS_R2`).

## Objet

R3 corrige le problème principal de R2 : le nouveau composant Step 1 existait mais le chemin réellement utilisé par `Analyse > 1 · STEM` continuait d'appeler l'ancien lecteur `stem_webaudio` avec les paroles.

Le point d'entrée historique `stem_webaudio.render_player()` délègue maintenant explicitement les appels `ezstem_player_*` vers `step1_riffstation.render_step1_riffstation()`.

## Step 1 livré

Step 1 = **Riffstation + STEM**, sans parole :

- mixeur Original + STEM ;
- lecture / pause / stop ;
- vitesse 0,50× à 1,50× avec conservation de hauteur ;
- time signature ;
- capo ;
- diagramme courant optionnel ;
- accords seuls ;
- mire fixe ;
- défilement métrique régulier : les beats sont espacés uniformément comme un métronome, tandis que la fonction de projection convertit le temps audio réel en position visuelle sans modifier aucun timestamp.

À `t=0`, aucun beat futur ne peut se trouver à gauche de la mire. Avant le premier beat, aucun accord/diagramme n'est courant.

Le diagramme courant est physiquement ancré sur la même abscisse CSS que la mire (`--playhead-x`).

## Cartouche morceau

Le composant Step 1 contient désormais un cartouche avec :

- titre du morceau ;
- artiste ;
- éditeur ;
- Mode Analyse / Édition / Player ;
- Time sig ;
- Capo ;
- Vitesse ;
- option Diagramme.

Pendant Step 1 / Analyse, l'ancien panneau latéral Streamlit est masqué. Un changement de Mode depuis le cartouche remet le mode demandé dans `ez_work_mode_<hash>` puis relance Streamlit ; le panneau latéral historique redevient alors disponible dans les autres modes.

Time sig et Capo continuent d'utiliser le contrat de persistance EZScore existant (`song_preferences`) et ne recalculent pas les timestamps.

## Step 2

Le moteur / rendu Step 2 n'est pas réécrit dans cette livraison. Les assets historiques de paroles dans `stem_webaudio.py` restent présents. Le nouveau routage ne s'applique qu'aux clés `ezstem_player_*` du Step 1.

La future lane paroles pourra utiliser la même transformation temps -> métrique pour faire passer le mot courant sous la même mire sans déplacer la timeline métier.

## Installation PowerShell

Arrêter Streamlit, puis :

```powershell
cd H:\EZScore

$pkg = "$env:USERPROFILE\Downloads\EZScore_STEP1_RIFFSTATION_STEMS_R3.zip"
$tmp = "H:\Temp\EZScore_STEP1_RIFFSTATION_STEMS_R3"

Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $tmp -Force | Out-Null
tar -xf $pkg -C $tmp

Copy-Item "$tmp\ezscore\player\step1_riffstation.py" "H:\EZScore\ezscore\player\step1_riffstation.py" -Force
Copy-Item "$tmp\ezscore\player\stem_webaudio.py" "H:\EZScore\ezscore\player\stem_webaudio.py" -Force
Copy-Item "$tmp\scripts\test_step1_riffstation_contract.py" "H:\EZScore\scripts\test_step1_riffstation_contract.py" -Force

.\.venv-py313\Scripts\python.exe -m py_compile .\ezscore\player\step1_riffstation.py .\ezscore\player\stem_webaudio.py
.\.venv-py313\Scripts\python.exe .\scripts\test_step1_riffstation_contract.py
```

Résultat attendu :

```text
STEP1_RIFFSTATION_R3_CONTRACT_OK
```

Relancer ensuite :

```powershell
.\.venv-py313\Scripts\python.exe -m streamlit run EZScore.py --server.address 127.0.0.1 --server.port 8501 --server.headless true
```

## Fichiers modifiés

- `ezscore/player/step1_riffstation.py`
- `ezscore/player/stem_webaudio.py`
- `scripts/test_step1_riffstation_contract.py`
- `readme.md`

Aucun `__pycache__` n'est livré.
