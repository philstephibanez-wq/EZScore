# EZScore — R12c

Correctif de portée après audit du changement de vitesse.

## Portée contrôlée

Le changement de vitesse touche :
- état du sélecteur ;
- intention Lecture/Pause ;
- horloge musicale ;
- arrêt/redémarrage des AudioBufferSourceNode ;
- offset de reprise ;
- cache/décodage des variantes tempo ;
- rendu Accords / Chant / Chœurs ;
- diagramme courant ;
- changement de mesure pendant lecture.

## Correctifs R12c

1. Le sélecteur de vitesse reste toujours manipulable.
2. Les changements rapides ne perdent plus l'intention de lecture.
   Exemple validé par construction :
   `1.00 -> 0.75 -> 1.25 -> 0.85`
   pendant la lecture doit reprendre avec le dernier choix.
3. Les décodages asynchrones obsolètes sont ignorés.
4. Le retard visuel de 350 ms est appliqué aussi lors :
   - d'un changement de mesure ;
   - d'un changement d'affichage des diagrammes.
5. Aucun changement sur :
   - sources audio / STEMs ;
   - EQ ;
   - volumes ;
   - timestamps persistés ;
   - analyse harmonique ;
   - time-stretch FFmpeg `atempo`.

## Installation

```powershell
cd H:\EZScore

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\EZScore_R12c_speed_transition_safe.zip" `
  -DestinationPath . `
  -Force

python -m py_compile .\ezscore\player\karaoke_stem_webaudio_r12c.py
python -m py_compile .\ezscore\ui\__init__.py

git diff --check
git status
```

Puis redémarrer Streamlit.

## Test ciblé

Pendant Lecture :
1. `1.00 -> 0.75`
2. immédiatement `0.75 -> 1.25`
3. immédiatement `1.25 -> 0.85`
4. retour `1.00`

Attendus :
- sélecteur toujours actif ;
- le dernier choix gagne ;
- la lecture reprend ;
- tonalité inchangée ;
- aucune désynchronisation STEM ;
- conducteur toujours légèrement retardé.
