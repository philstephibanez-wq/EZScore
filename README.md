# EZScore R30 FIX1 — récupération des sauts de ligne

Correctif incrémental à appliquer après R30.

## Correction

Les retours à la ligne manuels des paroles pouvaient ne plus être visibles après les régressions précédentes, même lorsqu'une ancienne version technique les contenait encore.

FIX1 ajoute une récupération conservatrice depuis `analysis_versions.lyric_edits_json` :

- une ancienne mise en forme n'est reprise que si le texte est strictement identique après normalisation des espaces ;
- seuls les retours à la ligne sont donc restaurés automatiquement ;
- une ancienne correction de mots différente n'est jamais réinjectée ;
- la mise en forme récupérée est immédiatement réenregistrée dans `lyric_block_edits` afin de redevenir la référence courante.

Cette récupération fonctionne aussi avec l'ancien décalage de borne de bloc de quelques millisecondes.

## Fichiers modifiés

- `ezscore/persistence.py`
- `readme.md`
