# CDC R39.5 FULL

Base : R39.4 master propre.

## Lyrics
Le diagramme partagé doit être instancié à l'intérieur de `lyrics-ribbon-stage`.
Il ne doit pas être positionné dans le wrapper `chordslab-stage`.

La stage réserve une bande supérieure explicite pour un diagramme de taille identique à Chords.

La timeline canonique reste la source temporelle.
Aucune shape guitare n'est dupliquée dans Lyrics.

## Catalog
`adminUpdateSong()` doit initialiser `$requestedStatus` depuis le POST avant appel à `applyStatus()`.
