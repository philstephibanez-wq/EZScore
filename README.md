# EZScore R28 FIX1 — navigation Compte

Correctif ciblé du module d'authentification R28.

## Correction

Streamlit interdit de modifier directement `st.session_state["main_menu"]`
après l'instanciation du widget `main_menu`.

Les transitions du module `ezscore/auth/ui.py` passent désormais par
`st.session_state["_pending_main_menu"]`, mécanisme déjà traité par
`EZScore.py` au rerun suivant.

Chemins corrigés :
- ouverture de la page Compte ;
- login e-mail réussi ;
- création de compte réussie ;
- déconnexion depuis le profil.

## Encodage

Le fichier est écrit en UTF-8 natif et conserve les accents / emojis.

## Fichiers du livrable

- `readme.md`
- `ezscore/auth/ui.py`

## Installation

Extraire le ZIP directement dans `H:\EZScore` puis compiler :

```powershell
cd H:\EZScore
python -m py_compile .\ezscore\auth\ui.py .\EZScore.py
```
