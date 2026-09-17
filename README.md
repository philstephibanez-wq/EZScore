# EZScore — Paroles + ancres entre les mots R2

Baseline à préserver :
`stable-karaoke-pre-editor` / `45a912e`

## Portée

Fichiers applicatifs modifiés/ajoutés :
- `ezscore/ui/__init__.py`
- `ezscore/ui/lyrics_word_anchor_editor.py`

Le moteur player validé n'est pas modifié.
`stem_lab_analysis.py` n'est pas réécrit : l'écran EZScore > Analyse > Paroles
est enrichi au runtime au point exact où `Texte transcrit` est rendu.

## Paroles

Dans `EZScore > Analyse > 2 · Paroles` :
- police 20 px ;
- interligne 1.48 ;
- sauts de ligne conservés exactement ;
- bouton `💾 Enregistrer` explicite ;
- indicateur `✓ Enregistré` / `● Modifications non enregistrées` ;
- bouton `↩ Texte Whisper`.

La correction est stockée séparément dans :
`data/analysis/stem_lab/<audio_hash>/lyrics_editorial.json`

Le cache Whisper original n'est jamais modifié.

## Ancres

Sous le texte :
- tous les mots Whisper sont affichés ;
- cliquer exactement entre deux mots sélectionne une frontière ;
- saisir le nom puis `＋ Ajouter` ;
- renommage et suppression restent en brouillon ;
- `💾 Enregistrer les ancres` persiste explicitement.

Une ancre stocke :
- `anchor_id`
- `label`
- `boundary_index`
- mot gauche / mot droit
- timestamp dérivé de la frontière

Elle ne contient aucune mesure.

## Zéro fallback

- fichier éditorial invalide => erreur ;
- fingerprint Whisper différent => erreur ;
- ancre hors frontière => erreur ;
- nom vide => erreur ;
- doublon sur une frontière => erreur ;
- aucun remapping automatique.

## Installation

```powershell
cd H:\EZScore

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\EZScore_LYRICS_ANCHORS_R2.zip" `
  -DestinationPath . `
  -Force

python -m py_compile .\ezscore\ui\lyrics_word_anchor_editor.py
python -m py_compile .\ezscore\ui\__init__.py

git diff --check
git status --short
```

## Contrôle d'impact

```powershell
git diff --name-only stable-karaoke-pre-editor
```

Les seuls nouveaux changements de ce livrable doivent concerner :
- `ezscore/ui/__init__.py`
- `ezscore/ui/lyrics_word_anchor_editor.py`

Attention : si `backoffice/player.py` apparaît encore, c'est le R1 précédent déjà
présent dans votre working tree. R2 ne le modifie pas.

## Test ciblé

1. Ouvrir Analyse > Paroles.
2. Ajouter plusieurs retours à la ligne.
3. Cliquer `Enregistrer`.
4. Changer d'onglet puis revenir : le texte doit être identique.
5. Redémarrer Streamlit : le texte doit être identique.
6. Cliquer entre deux mots dans `Ancres`.
7. Nommer l'ancre et cliquer `＋ Ajouter`.
8. Cliquer `Enregistrer les ancres`.
9. Changer d'onglet / redémarrer et vérifier sa présence.
10. Revalider le player stable : Original/Mix STEM, EQ, volumes, vitesse,
    Chant, Chœurs/la-la-la, seek et synchro.
