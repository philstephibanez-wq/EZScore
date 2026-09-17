# EZScore — R11d

Correctif visuel ciblé sur les listes `Mesure` et `Vitesse`.

## Correction

Les `<select>` et leurs `<option>` utilisent maintenant explicitement un fond
sombre et un texte clair. La liste déroulée reste lisible sur le thème sombre,
y compris les valeurs non sélectionnées.

Aucun changement sur :
- audio / STEMs ;
- EQ ;
- synchro ;
- géométrie du karaoké ;
- time signature ;
- vitesse ;
- diagrammes.

## Installation

Depuis `H:\EZScore` :

```powershell
cd H:\EZScore

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\EZScore_R11d_dark_selects.zip" `
  -DestinationPath . `
  -Force

python -m py_compile .\ezscore\player\karaoke_stem_webaudio_r11d.py
python -m py_compile .\ezscore\ui\__init__.py

git diff --check
git status
```

Puis redémarrer Streamlit.

Ne pousser qu'après vérification visuelle de `Mesure` et `Vitesse`.
