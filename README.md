# EZScore — lecteur unifié STEM + karaoké — R9

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


## R7 — lisibilité + ré-analyse sans réimport

### Lisibilité

La rangée des accords n'utilise plus la compression sémantique des paroles.
Chaque mesure dispose maintenant d'un slot visuel fixe. La tête de lecture
reste synchronisée sur le temps réel et interpole sa position à l'intérieur de
la mesure. Cela supprime les superpositions/flous visibles en R6.

Le mot actif ne subit plus de `scale()` CSS, ce qui évite également le flou et
les petits sauts typographiques.

### Ré-analyse

Trois boutons sont ajoutés au-dessus du conducteur :

- `Ré-analyser paroles` : relance Whisper à partir de l'audio déjà persisté ;
- `Ré-analyser accords` : invalide puis recalcule rythme + harmonie ;
- `Ré-analyser tout` : relance les deux chaînes.

Aucun de ces boutons ne demande de réimporter le MP3 et aucun ne refait les
STEM BS-RoFormer existants.


## R8 — piste Chœurs restaurée + suppression du double STEM

Deux corrections ciblées :

1. **Piste Chœurs**
   - `Chant` = mots de la transcription Whisper principale sur le mix original ;
   - `Chœurs` = mots/vocalises ajoutés uniquement par la passe Whisper sur le
     stem `vocals`, c'est-à-dire les événements trouvés dans les trous de la
     transcription principale ;
   - la piste Chœurs a une couleur violette distincte et défile sur la même
     timeline compacte.
   - Cette attribution est volontairement qualifiée de *provisoire* : elle ne
     prétend pas encore être une séparation acoustique lead/backing parfaite.

2. **STEM non doublés**
   - le conducteur ne rend plus son propre mixeur STEM ;
   - il ne charge/joue plus les stems séparés ;
   - son transport utilise uniquement l'audio original comme horloge maître.
   - Le mixeur STEM normal de l'analyse reste la seule interface STEM.

Le composant frontend est renommé `ezscore_karaoke_stem_player_r8` pour forcer
le rechargement du bundle Bidi.


## R9 — lecteur final unifié : STEM + EQ + karaoké continu

R9 annule la mauvaise direction de R8 qui avait réduit le lecteur à l'audio
original uniquement.

Le même composant possède maintenant :

- une seule horloge WebAudio pour toutes les pistes ;
- `Original` + les STEM canoniques disponibles ;
- preset `Original` ;
- preset `Mix STEM` ;
- ON/OFF individuel par piste ;
- volume individuel ;
- égaliseur 3 bandes **restauré depuis le lecteur STEM validé** :
  - Graves : crossover < 250 Hz ;
  - Médiums : 250 Hz → 4 kHz ;
  - Aigus : > 4 kHz ;
  - réglages ±12 dB ;
  - compensation automatique de niveau ;
  - bouton `Reset EQ` par piste ;
- volume Master ;
- seek/lecture/pause/stop communs ;
- conducteur continu sur la même horloge ;
- ligne `Chant` ;
- ligne `Chœurs` en violet, incluant les vocalises récupérées (`la la la`,
  `na na`, `oh`, etc.) ;
- accords et notation `-` / `.` ;
- signature N/D et groupement modifiables uniquement pour la présentation ;
- boutons de ré-analyse utilisant l'audio/stems déjà persistés.

Il n'y a plus deux lecteurs concurrents : le mixeur STEM et le karaoké vivent
dans le même composant et démarrent tous les buffers au même instant WebAudio.
