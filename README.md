# EZScore_STEP1_RIFFSTATION_STEMS_R2

Base de travail vérifiée : GitHub `master` commit `e949eb1db272dc07695f032bf91af6187290fd1e`.

Cette livraison remplace la R1. Elle ne modifie aucun fichier du Step 2 (`chords_lyrics_editor.py`, `lyrics_inline_editor.py`, `templates/views/lyrics-editor.*`, `stem_analysis_conductor.py`).

## Contrat Step 1

Step 1 = Riffstation + STEMS, pour audit à l'oreille :

- extraction STEM existante conservée ;
- timeline musicale dédiée `riffstation_step1.json` ;
- beats : batterie / `madmom-infer` ;
- accords : audio original / `lv-chordia` ;
- time signature calculée à partir des accents batterie ;
- aucun fallback métrique inventé ;
- mixeur STEM ;
- lecture / pause / stop / seek ;
- vitesse 0,50x / 0,75x / 1,00x / 1,25x / 1,50x avec conservation de hauteur ;
- Time sig dans le composant Step 1 ;
- Capo dans le composant Step 1 ;
- diagramme optionnel ;
- prompteur accords uniquement ;
- aucune parole n'est fournie au composant Step 1.

La time signature, le capo et la vitesse sont des paramètres de représentation/lecture. Les timestamps de la timeline musicale ne sont jamais déplacés.

## Mire temporelle

La mire est fixe à 34 % de la fenêtre. La timeline se déplace dessous.

À `t = 0`, la position temporelle zéro est exactement sur la mire : aucun événement de temps positif ne peut apparaître à gauche. Avant le premier beat, aucun accord n'est marqué `current` ou `past`.

Quand la lecture avance, le passé passe à gauche et le futur reste à droite. Le diagramme courant est centré au-dessus de la même mire que l'accord courant.

## Time sig / Capo

Les contrôles historiques de la sidebar sont seulement masqués pendant que le composant Step 1 est monté. Ils ne sont pas supprimés du reste d'EZScore.

Les contrôles du composant Step 1 utilisent le contrat existant `song_preferences` :

1. changement dans le composant ;
2. sauvegarde dans `song_preferences` ;
3. alimentation de `_pending_song_preferences` ;
4. rerun ;
5. EZScore resynchronise son état global avant de recréer ses widgets.

Aucune seconde source de vérité métier n'est créée dans `localStorage`.

## Important : redémarrage complet

La R1 pouvait sembler ne rien changer si Streamlit était resté lancé : `stem_lab_analysis.py` importe `render_player` au chargement du module. Après remplacement des fichiers, il faut donc arrêter complètement le serveur puis le relancer.

```powershell
cd H:\EZScore

# arrêter le serveur actuel avec Ctrl+C avant ceci
.\.venv-py313\Scripts\python.exe -m streamlit run EZScore.py --server.address 127.0.0.1 --server.port 8501 --server.headless true
```

## Installation

Depuis `H:\EZScore` :

```powershell
$pkg = "$env:USERPROFILE\Downloads\EZScore_STEP1_RIFFSTATION_STEMS_R2.zip"
$tmp = "H:\Temp\EZScore_STEP1_RIFFSTATION_STEMS_R2"

Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $tmp -Force | Out-Null
tar -xf $pkg -C $tmp

Copy-Item "$tmp\ezscore\analysis\riffstation_step1.py" "H:\EZScore\ezscore\analysis\riffstation_step1.py" -Force
Copy-Item "$tmp\ezscore\player\step1_riffstation.py" "H:\EZScore\ezscore\player\step1_riffstation.py" -Force
Copy-Item "$tmp\ezscore\player\stem_webaudio.py" "H:\EZScore\ezscore\player\stem_webaudio.py" -Force
Copy-Item "$tmp\scripts\test_step1_riffstation_contract.py" "H:\EZScore\scripts\test_step1_riffstation_contract.py" -Force

.\.venv-py313\Scripts\python.exe -m py_compile `
  .\ezscore\analysis\riffstation_step1.py `
  .\ezscore\player\step1_riffstation.py `
  .\ezscore\player\stem_webaudio.py

.\.venv-py313\Scripts\python.exe .\scripts\test_step1_riffstation_contract.py
```

Résultat attendu :

```text
STEP1_RIFFSTATION_R2_CONTRACT_OK
```

## Contrôle visuel attendu

Après redémarrage et ouverture du Step 1 :

- pas de ligne `Paroles` / `Chant` dans le prompteur ;
- pas de diagramme dans une ligne séparée sous les accords ;
- `Time sig`, `Capo`, `Vitesse`, `Diagramme` sont dans la barre du composant ;
- la mire verticale traverse l'accord courant ;
- le diagramme optionnel est au-dessus de cette mire ;
- à `0:00`, rien de temporellement antérieur n'apparaît à gauche de la mire.

Si l'ancien conducteur `Structure / Accords / Chant` est encore visible après copie, le serveur n'a pas été redémarré avec les nouveaux modules.
