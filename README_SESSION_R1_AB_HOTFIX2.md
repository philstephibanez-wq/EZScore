# SESSION R1.A/B HOTFIX 2

Corrige le second défaut de l'installateur :
le ZIP étant extrait directement à la racine de `H:\EZScore`, les fichiers
`migration/test/contrat` sont déjà à leur destination. Le script tentait
ensuite de les recopier sur eux-mêmes.

Le hotfix supprime ces `Copy-Item` et vérifie simplement que les trois fichiers
de livraison sont présents.

Le script reste idempotent : il peut être relancé après l'échec précédent.
