# EZScore — conducteur karaoké paroles + accords — R6

Base lue : branche `feature/stem-analysis-pipeline`, commit
`c1fd40afa47890fadb5a8efe83745f8ca010ad65`.

## But de ce livrable

Afficher, dès que l'analyse Whisper est terminée, un conducteur synchronisé
sur l'audio avec :

- ligne précédente / ligne active / ligne suivante ;
- mot actif mis en évidence ;
- accords au-dessus de la ligne active ;
- notation de mesure avec `-` pour la tenue et `.` pour l'absence d'accord ;
- support du `^` dès qu'une timeline canonique fournit une fermata ;
- signature éditable `N/D` ;
- groupement métrique éditable (`3+3`, `2+2+3`, `3+2`, `4+3`, etc.) ;
- prise en charge de 2/4, 3/4, 4/4, 5/4, 7/4, 3/8, 5/8, 6/8, 7/8,
  9/8, 12/8 et des signatures personnalisées ;
- changement de métrique sans relancer Whisper ni BS-RoFormer.

La timeline rythmique utilise `madmom-infer` sur le stem batterie et la
timeline harmonique utilise `lv-chordia`, comme l'étape 3 actuelle. Le cache
est écrit dans le répertoire d'analyse du morceau sous
`karaoke_conductor.json`.

## Installation

Décompresser directement ce ZIP dans la racine du dépôt `H:\EZScore`
en conservant l'arborescence et en autorisant l'écrasement de
`ezscore/ui/__init__.py`.

Aucun `H:\Temp` n'est utilisé.

Puis lancer EZScore normalement. Après `2 · Paroles`, revenir au lecteur STEM :
le conducteur apparaît sous le transport avec les accords synchronisés.

## Remarque d'intégration

Pour éviter de modifier le gros fichier `stem_lab_analysis.py` à ce stade,
`ezscore/ui/__init__.py` remplace uniquement la fonction lecteur importée par
l'analyse STEM. C'est volontairement un crochet de validation. Une fois le
rendu validé, il faudra transformer ce crochet en import explicite dans
`stem_lab_analysis.py`.


## Correctifs R2

- corrige l'erreur Bidi `Cannot access 'lines' before initialization` ;
- réutilise la `beat_timeline` canonique si l'étape 3 existe déjà ;
- tente ensuite `madmom-infer` ;
- si `madmom-infer` est installé mais incomplet/incompatible
  (`No module named 'madmom_infer.features.beats'`), le conducteur immédiat
  utilise temporairement `librosa` sur le stem batterie ;
- ce fallback est limité à l'aperçu karaoké : il n'altère pas le principe
  d'analyse HQ canonique.


## Correctif R3

- corrige `name 'np' is not defined` dans le fallback rythmique provisoire ;
- aucun autre changement fonctionnel : le conducteur reste immédiatement
  disponible après Whisper, avec accords dès que la timeline harmonique/rythmique
  est construite.


## Correctifs R4 — vocalises d'introduction

Le cache Whisper du morceau de test commence à 32,30 s sur `Dance`; les
vocalises d'introduction n'étaient donc pas absentes du lecteur, elles étaient
absentes de la transcription originale.

R4 ajoute un deuxième passage Whisper-small, une seule fois, sur le stem
`vocals`. Il sert uniquement à compléter les grands trous laissés par le
passage sur le mix original (pré-roll, vocalises `la/na/oh/ah`, etc.).
Le résultat est mis en cache dans `whisper_vocals_small.json`.

La transcription originale reste autoritaire : le passage `vocals` ne remplace
pas les mots déjà horodatés, il ajoute seulement des mots dans les intervalles
vides. Le lecteur n'affiche plus non plus la première ligne future pendant une
longue introduction si aucune parole n'a été détectée.


## R5 — karaoké continu

Le rendu n'est plus basé sur des pages/lignes actives qui apparaissent puis
disparaissent. Les paroles et les accords sont maintenant placés sur une
timeline horizontale continue en fonction de leurs timestamps absolus.

- tête de lecture fixe à ~38 % de la largeur ;
- texte passé à gauche, temps courant sous la tête de lecture, futur visible à droite ;
- aucun écran noir entre deux groupes de mots ;
- aucune saute de page ;
- accord/mesure actif mis en évidence ;
- `-` et `.` conservés dans la notation de mesure ;
- changement N/D + groupement sans relancer Whisper ;
- structure HTML/CSS déjà prévue pour une future seconde piste `Chœurs`,
  volontairement masquée tant qu'une séparation lead/backing fiable n'est pas
  intégrée.


## R6 — suppression des grands vides visuels

La R5 utilisait une échelle spatiale proportionnelle au temps. C'était une
mauvaise abstraction pour un karaoké : une longue intro ou une pause vocale
créait mécaniquement un grand écran vide.

R6 utilise une timeline **sémantique continue** :

- les mots sont disposés sans grands espaces visuels ;
- leurs timestamps restent la seule vérité pour la synchronisation ;
- le défilement entre deux mots est interpolé avec le temps réel ;
- avant la première parole, la première phrase reste visible à droite et
  approche progressivement la tête de lecture ;
- les accords utilisent la même transformation temps -> position visuelle ;
- aucun silence audio ne peut créer un canyon noir dans le conducteur ;
- nouveau nom de composant Bidi `ezscore_karaoke_stem_player_r6` pour éviter
  de réutiliser un ancien bundle frontend en cache.
