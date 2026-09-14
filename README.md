# EZScore R30 FIX4 — éditeur Blocs + Paroles déterministe

Correctif incrémental à appliquer après R30 FIX2.

## Cause des comportements aléatoires

Deux états indépendants coexistaient :
- le brouillon de structure ;
- les textareas de paroles.

De plus, les clés Streamlit des paroles dépendaient des bornes temporelles.
Déplacer une frontière changeait donc la clé du widget et pouvait faire
réapparaître une ancienne valeur ou perdre une modification non validée.

Enfin, deux boutons de validation distincts rendaient possible la validation
du découpage sans sauvegarder les paroles visibles.

## FIX4

- clé des textareas basée sur le block_id stable ;
- déplacer une frontière ne recrée plus le champ de paroles ;
- suppression du bouton indépendant Valider ce découpage ;
- suppression du bouton indépendant Valider les paroles ;
- un seul bouton : Valider blocs + paroles ;
- ce bouton persiste les frontières/noms puis l'état complet des paroles ;
- un seul snapshot est créé ;
- la vue reste explicitement Blocs > Édition ;
- la réinitialisation des paroles nettoie aussi les widgets de session.

## Fichiers modifiés

- EZScore.py
- readme.md
