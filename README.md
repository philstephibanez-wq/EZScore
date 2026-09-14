# EZScore R30 FIX5 — validation Blocs, synchro paroles, impression

Correctif cumulatif à appliquer sur le dernier push utilisateur `5683aec`.

## 1. Validation Blocs + paroles

Correction de :

```text
StreamlitWidgetAlreadyInstantiatedError:
st.session_state.song_view_... cannot be modified after the widget ...
```

Après `Valider blocs + paroles`, EZScore ne réécrit plus les clés Streamlit
`song_view`, `song_mode` ni leur radio après instanciation.

La vue courante reste naturellement `Blocs > Édition` sans provoquer
l'exception.

## 2. Player : conservation des timestamps

L'ancien mécanisme redistribuait tous les mots corrigés sur toute la durée du
bloc dès que le nombre de mots changeait. Cela pouvait décaler progressivement
les paroles du player.

FIX5 utilise un alignement lexical local :
- les mots inchangés gardent exactement leurs timestamps Whisper ;
- un remplacement 1 pour 1 garde la fenêtre temporelle du mot source ;
- seules les insertions ou remplacements de longueur différente sont interpolés
  localement entre leurs voisins ;
- les retours à la ligne manuels restent conservés.

Ainsi une correction orthographique ou un déplacement partiel n'entraîne plus
le recalage artificiel de tout le bloc.

## 3. Impression visible

Les fonctions d'impression existaient toujours mais étaient exposées sous forme
d'une icône 34 px devenue difficile à repérer.

Le contrôle est maintenant un bouton explicite :
- `🖨 Imprimer la grille`
- `🖨 Imprimer paroles + accords`

Le document autonome et le dialogue d'impression navigateur existants sont
conservés.

## 4. Base SQLite

Le dépôt contient bien `data/EZScore.sqlite3`. Le dernier push utilisateur qui
la modifie est `5683aec`.

## Fichiers modifiés

- `EZScore.py`
- `ezscore/persistence.py`
- `ezscore/printing.py`
- `readme.md`
