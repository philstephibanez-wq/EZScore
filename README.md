# EZScore — R5.1 correctif Streamlit BidiComponent

Erreur corrigée :

```text
BidiComponentInvalidDefaultKeyError:
Key 'snapshot' in default is not a valid state name.
Valid state names are those with corresponding on_[state_name]_change callbacks.
```

Cause : R5 déclare `default={"snapshot": ...}` sans callback correspondant.

R5.1 ajoute uniquement :

```python
on_snapshot_change=lambda: None
```

à l'appel du composant V2.

## Portée

Un seul fichier :
- `ezscore/ui/lyrics_inline_editor.py`

Aucun template modifié.
Aucun player modifié.
Aucun moteur audio modifié.
Aucune donnée runtime modifiée.

## Installation

```powershell
cd H:\EZScore

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\EZScore_INLINE_TIMELINE_R5_1.zip" `
  -DestinationPath . `
  -Force

python -m py_compile .\ezscore\ui\lyrics_inline_editor.py
git diff --check
git status --short
```

Puis relancer Streamlit et ouvrir `Analyse > Paroles`.
