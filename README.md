# EZScore — README / CONTRAT / HANDOFF

## Objet

EZScore analyse un fichier audio afin de produire une grille métrique d'accords et des paroles synchronisées.

Le principe directeur est :

> **Interpréter le signal audio, ne pas inventer une progression.**

Le moteur doit donc s'appuyer sur les informations réellement présentes dans l'audio et conserver l'incertitude lorsqu'un élément ne peut pas être déterminé de manière suffisamment fiable.


### Lancement courant

```powershell
cd H:\EZScore
python -m streamlit run .\EZScore.py
```

Entrée produit : `EZScore.py`.

## Architecture courante

```text
morceau original
├─ beat tracking / tempo / accents
├─ Whisper -> paroles + timestamps mot à mot
└─ Demucs
   ├─ vocals
   └─ no_vocals
      └─ analyse harmonique / accords
```

Le morceau original sert principalement au beat tracking. Le stem `no_vocals` sert de source harmonique pour les accords.

## Contrat d'affichage

### Grille

Exemple 4/4 :

```text
🎼 Grille
| Am--- | Am-Em- | Em--- | D-C- |
```

### Paroles

Chaque motif métrique complet de mesure doit être projeté au-dessus des paroles au moment correspondant :

```text
🎤 Paroles

Am---            Am-Em-
I was sitting here waiting for you

                 Em---
Then you walked into the room
```

L'accord doit être répété à chaque nouvelle mesure lorsqu'il est réellement rejoué / réarticulé dans la grille.

## Convention rythmique

```text
- = accord tenu normalement sur le beat suivant
. = beat non joué / silence harmonique
^ = point d'orgue détecté / prolongation libre
```

Exemples :

```text
Am---   = Am sur toute une mesure 4/4
Am-Em-  = Am sur 2 temps, Em sur 2 temps
Am...   = Am puis trois beats non joués
D.C-    = D, silence, C tenu
G---^   = G tenu avec point d'orgue détecté
```

Les doublons consécutifs doivent être compressés :

```text
Am Am Em Em -> Am-Em-
```

et jamais :

```text
AmAm-Em-
```

Après un `.`, un `-` ne peut pas prolonger l'accord précédent : le silence coupe la tenue.

## Signatures rythmiques

Le panneau de réglages propose désormais :

- Auto
- 2/4
- 3/4
- 4/4
- 5/4
- 6/8
- 7/8
- 12/8

Le mode **Auto** est une estimation expérimentale fondée sur les accents détectés aux beats.

Il teste plusieurs hypothèses métriques et expose :

- la signature retenue ;
- une confiance ;
- une phase d'accent proposée ;
- des scores diagnostiques par signature.

### Limite actuelle de l'auto-mètre

L'auto-mètre estime encore principalement un **groupement périodique d'accents**. Il ne réalise pas encore une vraie détection musicologique complète du downbeat et peut donc confondre :

- 2/4 et 4/4 ;
- 3/4 et 6/8 ;
- 6/8 et 12/8.

Le forçage manuel reste donc contractuellement disponible.

### 2/4

La V19 ajoute explicitement le 2/4 dans :

- le sélecteur manuel ;
- l'auto-détection ;
- le scoring des accents.

Le 2/4 recherche une alternance simple fort/faible sur deux beats.

Cas de validation principal : **Susanna**, ressentie potentiellement en 2/4 plutôt qu'en 4/4 / 12/8.

### Signatures composées

Pour les signatures ternaires composées, l'affichage est groupé par 3 subdivisions :

```text
6/8  -> 3+3
12/8 -> 3+3+3+3
```

Exemples :

```text
6/8 :  Cm-- | Fm--
6/8 :  Cm-- | Cm--
12/8 : Cm-- | Fm-- | Cm-- | G--
```

Objectif : conserver une lecture guitaristique naturelle.

## Balance fondamentale / accompagnement

Chordstation calcule deux évidences distinctes :

1. **accompagnement** : accord majeur/mineur déduit du spectre harmonique ;
2. **fondamentale** : racine probable extraite dans les deux octaves graves.

Le paramètre **Poids de la fondamentale** est réglable de 10 % à 45 %.

Valeur par défaut :

```text
22 % fondamentale
78 % accompagnement
```

Formule conceptuelle :

```text
score final =
    poids accompagnement × score accord
  + poids fondamentale × score racine grave
```

La fondamentale ne distingue volontairement pas majeur/mineur ; cette distinction reste fournie par l'accompagnement.

Le poids de la fondamentale est plafonné afin qu'une ligne de basse mobile ne puisse pas imposer seule les changements d'accords.

## Réglages avancés

Les réglages sont regroupés dans un formulaire Streamlit. L'analyse ne redémarre qu'après validation.

Réglages courants :

- signature rythmique ;
- fréquence d'analyse ;
- `hop_length` ;
- seuil silence RMS ;
- seuil silence harmonique ;
- poids de la fondamentale ;
- activation de la détection du point d'orgue ;
- seuil du point d'orgue.

Les paramètres sont passés à la fonction d'analyse et participent donc à la clé du cache Streamlit.

## Point d'orgue

Aucun `^` ne doit être supposé ou injecté manuellement.

Il doit être ajouté uniquement si l'analyse audio fournit suffisamment d'indices :

- intervalle de beat anormalement long ;
- harmonie encore présente ;
- suspension de la pulsation suffisamment nette ;
- confiance supérieure au seuil fixé.

En cas de doute, aucun `^` n'est affiché.

## Accords étendus — spécification future

Le moteur courant reste centré sur les triades majeures / mineures.

Extension envisagée en seconde passe :

- `7`
- `maj7`
- `m7`
- `dim`
- `dim7`
- `m7b5`

Principe prévu :

```text
signal
-> racine
-> majeur / mineur / diminué
-> extension éventuelle
```

Une extension ne devra être ajoutée que si sa note caractéristique est stable dans l'accompagnement séparé de la voix.

## Détection de sections — roadmap

Détection envisagée :

- Intro
- Verse
- Chorus
- Bridge
- Outro

Approche prévue :

1. détecter d'abord des sections répétées A/B/C ;
2. comparer progressions d'accords, rythme harmonique, énergie, timbre et répétitions de paroles ;
3. attribuer ensuite un type `Verse`, `Chorus`, `Bridge` avec un score de confiance ;
4. conserver `Section A/B/C` si le type reste ambigu.

Aucune section ne doit être nommée artificiellement sans suffisamment d'indices.

## Performance

Configuration de développement actuelle :

```text
GPU : NVIDIA GeForce RTX 2060 6 Go
PyTorch : CUDA
Whisper : small
Analyse harmonique : 22050 Hz par défaut
hop_length : 2048 par défaut
```

Optimisations courantes :

1. cache Streamlit du modèle Whisper ;
2. cache de l'analyse musicale ;
3. cache de la transcription ;
4. séparation Demucs `no_vocals` ;
5. exécution parallèle CPU / GPU lorsque pertinent.

## Handoff courant — V19

### État validé

- Demucs opérationnel et détecté dans l'interface ;
- grille type tableur ;
- paroles synchronisées ;
- motif `Am-Em-` correctement représentable ;
- réglages avancés disponibles ;
- balance fondamentale / accompagnement disponible ;
- signatures manuelles 2/4, 3/4, 4/4, 5/4, 6/8, 7/8, 12/8 ;
- auto-détection métrique expérimentale ;
- affichage ternaire groupé pour 6/8 et 12/8.

### Observations de validation

**Susanna** :

- tempo détecté ~92 BPM ;
- motif harmonique attendu souvent proche de `Am-Em-` ;
- l'auto-mètre a pu proposer 12/8, ce qui paraît peu musical ;
- hypothèse actuelle à tester explicitement : **2/4**.

**La Bohème** :

- tonalité détectée autour de Cm ;
- 6/8 forcé donne une lecture plus naturelle que 3/4 ;
- l'auto-mètre peut proposer 12/8, ce qui reste plausible comme regroupement mais moins pratique pour la lecture guitaristique.

### Prochaine validation obligatoire

1. tester Susanna en `2/4`, `4/4` et `Auto` ;
2. comparer le motif `Am-Em-` et le nombre de mesures ;
3. vérifier La Bohème en `6/8` vs `12/8` ;
4. noter les scores métriques et la confiance Auto ;
5. éviter toute nouvelle logique qui force une progression harmonique ;
6. conserver le principe : **interpréter, pas inventer**.

## Lancement

```powershell
cd H:\ChordStation
python -m streamlit run .\chordstation_v19.py
```


## V20 — Détection de structure du morceau

La V20 implémente une première détection réelle de structure :

- sections A/B/C ;
- `Intro` ;
- `Outro` ;
- `Verse probable` ;
- `Chorus probable` ;
- `Bridge possible`.

### Principe contractuel

La classification se fait en deux passes :

1. regrouper des blocs de mesures similaires sous des labels structurels A/B/C ;
2. nommer `Verse`, `Chorus`, `Bridge` seulement si les indices sont suffisants.

Aucun type de section ne doit être imposé si la confiance est faible.

### Indices utilisés

La V20 combine :

- séquence d'accords ;
- vocabulaire harmonique ;
- répétition de progression ;
- similarité des paroles ;
- présence / absence de paroles ;
- position dans le morceau.

La musique reste prioritaire dans le score de similarité structurelle.

### Heuristiques de classification

`Chorus probable` :

- section répétée ;
- forte similarité harmonique ;
- paroles identiques ou très proches.

`Verse probable` :

- matériau harmonique récurrent ;
- paroles présentes ;
- paroles différentes entre occurrences.

`Bridge possible` :

- bloc isolé au milieu du morceau ;
- paroles présentes ;
- faible similarité avec les blocs voisins.

`Intro` / `Outro` :

- bloc initial / final ;
- peu ou pas de paroles.

### Réglages V20

Le panneau avancé ajoute :

- activation/désactivation de la détection de structure ;
- taille de bloc structurel : 2, 4 ou 8 mesures ;
- seuil de similarité de section.

Valeurs recommandées pour commencer :

```text
Détection structure : ON
Bloc structurel     : 4 mesures
Similarité          : 0.66
```

### Affichage

La V20 ajoute un tableau :

```text
Type              Section   Mesures   Confiance
Verse probable    A         1–8       76 %
Chorus probable   B         9–12      84 %
Verse probable    A         13–20     72 %
Bridge possible   C         21–24     61 %
Chorus probable   B         25–28     86 %
```

ainsi qu'un résumé compact de la structure.

### Handoff V20

Validation à effectuer sur plusieurs morceaux :

1. vérifier que les refrains réellement répétés sont regroupés ;
2. vérifier qu'un couplet musicalement similaire mais avec paroles différentes est classé comme `Verse probable` ;
3. vérifier qu'une section unique n'est pas automatiquement appelée `Bridge` sans rupture suffisante ;
4. contrôler les effets des blocs 2 / 4 / 8 mesures ;
5. comparer les résultats sur `Susanna` et `La Bohème` ;
6. conserver la règle : **détecter et qualifier, ne jamais inventer une structure**.

### Lancement V20

```powershell
cd H:\ChordStation
python -m streamlit run .\chordstation_v20.py
```


## V21 — Capodastre comme couche de représentation

La V21 ajoute un réglage de **capodastre** dans le panneau avancé.

### Contrat

Le capodastre ne doit jamais modifier :

- l'audio ;
- la tonalité détectée ;
- les accords internes issus de l'analyse ;
- la détection de structure Verse / Chorus / Bridge ;
- les scores harmoniques.

Il agit uniquement sur la **forme d'accord affichée au guitariste**.

Exemple :

```text
Accord réel détecté : Cm
Capo                : 3
Forme affichée       : Am
```

La grille affiche donc directement :

```text
| Am--- | Dm--- | E--- |
```

et non :

```text
| Cm--- | Fm--- | G--- |
```

lorsque le paramètre est `Capo 3`.

Le texte `capo 3` ne doit pas être répété dans chaque case de grille.

### Paramètre

Le panneau avancé expose :

```text
Capodastre
0 — sans capo
1
2
...
12
```

### Règle de conversion

La forme affichée est obtenue par :

```text
forme affichée = accord réel - nombre de demi-tons du capo
```

Exemple avec capo 3 :

```text
Cm -> Am
Fm -> Dm
G  -> E
```

Les suffixes sont conservés :

```text
C7    -> A7
Cm7   -> Am7
Cmaj7 -> Amaj7
Cdim  -> Adim
```

### Périmètre d'affichage

La conversion capo s'applique à :

- la grille ;
- les accords projetés au-dessus des paroles ;
- la frise chronologique.

La structure détectée reste calculée à partir des accords réels.

### Cache

Le capo est volontairement un paramètre de représentation, pas un paramètre d'analyse.

Changer le capo ne doit donc pas invalider l'analyse harmonique lourde. Les résultats audio restent en cache et seule la présentation est recalculée.

### Handoff V21

Validation obligatoire :

1. charger un morceau détecté en `Cm` ;
2. régler `Capo 3` ;
3. vérifier que la grille affiche `Am` lorsque l'accord réel est `Cm` ;
4. vérifier `Fm -> Dm` et `G -> E` ;
5. vérifier que la tonalité affichée reste `Cm` ;
6. vérifier que Verse / Chorus / Bridge ne changent pas avec le capo ;
7. vérifier que changer seulement le capo ne relance pas Demucs / Whisper inutilement ;
8. conserver le principe : **analyse réelle inchangée, représentation guitaristique seulement**.

### Lancement V21

```powershell
cd H:\ChordStation
python -m streamlit run .\chordstation_v21.py
```


## V22 — Capodastre temps réel

La V22 corrige le comportement du capodastre.

### Correctif fonctionnel

En V21, deux défauts étaient présents :

1. la grille principale utilisait encore les mesures réelles au lieu des mesures d'affichage transposées pour le capo ;
2. le réglage de capo était placé dans le formulaire de paramètres, ce qui imposait une validation explicite.

La V22 corrige les deux points.

### Contrat V22

Le capodastre est maintenant un contrôle **temps réel** séparé du formulaire des paramètres lourds.

Changer :

```text
Capo 0 -> Capo 1 -> Capo 2 -> ...
```

doit mettre à jour immédiatement :

- la grille ;
- les accords au-dessus des paroles ;
- la frise chronologique.

Il ne doit pas relancer :

- Demucs ;
- Whisper ;
- l'analyse harmonique ;
- la détection de tonalité ;
- la détection de structure.

### Séparation analyse / représentation

Interne :

```text
accord réel détecté : Cm
tonalité réelle      : Cm
```

Affichage avec `Capo 3` :

```text
forme guitare affichée : Am
```

La tonalité réelle reste affichée comme `Cm`.

### Exemple attendu

Avec :

```text
Capo 3
```

la grille d'un passage réel :

```text
Cm | Fm | G
```

doit apparaître :

```text
Am | Dm | E
```

sans texte `capo 3` dans les cases.

### Validation V22

1. Charger La Bohème en tonalité détectée `Cm`.
2. Passer de `Capo 0` à `Capo 3`.
3. Vérifier la mise à jour immédiate de la grille.
4. Vérifier `Cm -> Am`.
5. Vérifier `Fm -> Dm`.
6. Vérifier `G -> E`.
7. Vérifier que `Tonalité réelle estimée` reste `Cm`.
8. Vérifier qu'aucune séparation Demucs ni transcription Whisper ne repart.
9. Vérifier que la structure Verse / Chorus / Bridge ne change pas.

### Suite prévue

Le prochain chantier prévu est le **découpage / regroupement des paroles**, sans toucher à la logique du capodastre.


## V23 — Affichage compact et préparation impression

La V23 ne modifie pas le moteur d'analyse. Elle travaille uniquement sur la présentation.

### Objectif

Préparer deux sorties imprimables distinctes :

1. **Grille d'accords**
2. **Paroles + accords**

### Grille d'accords

La grille est désormais rendue comme un tableau continu de type Excel :

- aucune marge verticale entre groupes de mesures ;
- bordures continues ;
- `border-collapse` actif ;
- 4 mesures par ligne ;
- une ligne d'en-tête avec les numéros de mesures ;
- une ligne d'accords immédiatement en dessous.

Exemple visuel :

```text
| Mesure 1 | Mesure 2 | Mesure 3 | Mesure 4 |
| Am---    | Em---    | F---     | G---     |
| Mesure 5 | Mesure 6 | Mesure 7 | Mesure 8 |
| Am-Em-   | Em---    | Am---    | G---     |
```

Il ne doit plus y avoir d'interligne entre les blocs de grille.

### Paroles + accords

Les anciennes cartes `st.code()` séparées sont remplacées par une feuille continue.

Chaque bloc contient :

```text
accords
paroles
```

avec :

- marge verticale minimale ;
- pas de carte séparée ;
- séparation très légère entre lignes ;
- police monospace pour conserver l'alignement accords/paroles.

Objectif visuel :

```text
Am---              Em---
I was sitting here waiting for you
Am-Em-             G---
Then you walked into the room
```

sans espace important entre les lignes.

### Impression

La V23 ajoute des styles `@media print` afin de masquer lors de l'impression :

- sidebar ;
- toolbar Streamlit ;
- header/footer ;
- boutons.

La grille et les paroles passent sur fond blanc avec texte noir.

### Contrat pour la suite

La prochaine étape d'impression doit permettre de choisir explicitement :

```text
Imprimer :
- Grille
- Paroles + accords
```

avec idéalement une sortie PDF propre.

Cette étape ne doit pas modifier :

- l'analyse audio ;
- les accords réels ;
- la tonalité ;
- le capo ;
- la structure Verse / Chorus / Bridge.

### Handoff V23

Validation :

1. vérifier que la grille ne présente plus d'interligne ;
2. vérifier que les bordures forment un tableau continu ;
3. vérifier que les paroles + accords sont affichées en feuille continue ;
4. vérifier que l'alignement monospace reste correct ;
5. vérifier que le capo continue à mettre à jour l'affichage en temps réel ;
6. vérifier qu'aucune analyse lourde n'est relancée par les changements purement visuels ;
7. préparer ensuite le choix d'impression `Grille` ou `Paroles + accords`.

### Lancement

```powershell
cd H:\ChordStation
python -m streamlit run .\chordstation_v23.py
```


## V24 — Blocs détectés par progression de mesures

La V24 modifie le moteur de structure et l'affichage associé.

### Principe

Le découpage structurel ne repose plus sur un simple vocabulaire d'accords ni sur des riffs courts.

L'unité de comparaison est désormais une **progression de mesures complètes**.

Exemple de bloc structurel :

```text
[
  "Am-Em-",
  "Am---",
  "Em---",
  "D-C-"
]
```

Deux blocs sont considérés comme similaires en comparant :

- l'ordre des mesures ;
- la notation complète de chaque mesure ;
- la position des changements d'accords dans chaque mesure ;
- le rythme harmonique interne de chaque mesure.

Ainsi :

```text
Am---
```

et :

```text
Am-Em-
```

sont structurellement différents.

### Détection A/B/C

Le regroupement en blocs `A`, `B`, `C`, etc. est déterminé uniquement par la progression de mesures.

Les paroles ne servent pas à décider si deux blocs musicaux appartiennent au même pattern.

### Qualification Verse / Chorus / Bridge

Une fois les blocs A/B/C détectés :

- même progression + paroles différentes -> `Verse probable` ;
- même progression + paroles proches -> `Chorus probable` ;
- bloc unique suffisamment différent -> `Bridge possible` ;
- absence de confiance suffisante -> `Section A/B/C`.

### Affichage grille

La grille est affichée par blocs structurels.

À l'intérieur d'un bloc :

- aucune ligne blanche ;
- tableau continu type Excel ;
- mesures compactes.

Entre deux blocs :

- exactement un interligne visuel.

Exemple :

```text
Bloc A · Verse probable · mesures 1–4
| M1 | M2 | M3 | M4 |
| .. | .. | .. | .. |

Bloc B · Chorus probable · mesures 5–8
| M5 | M6 | M7 | M8 |
| .. | .. | .. | .. |
```

### Affichage paroles + accords

Même principe :

- lignes accords/paroles compactes à l'intérieur du bloc ;
- aucun interligne interne ;
- un interligne entre deux blocs structurels ;
- le titre du bloc indique `A/B/C`, son type probable et ses mesures.

### Tableau de structure

Le tableau structurel expose désormais également la progression de mesures utilisée pour la comparaison.

Exemple :

```text
Section A
Progression :
Am-Em- | Am--- | Em--- | D-C-
```

### Contrat important

Le moteur de structure doit chercher des **progressions de mesures répétées**, pas des riffs courts.

La progression doit rester sensible au rythme harmonique interne de la mesure.

### Handoff V24

Validation :

1. vérifier que deux occurrences d'une même progression de 4 mesures reçoivent le même label A/B/C ;
2. vérifier que `Am---` et `Am-Em-` ne sont pas considérés identiques ;
3. vérifier que les paroles ne changent pas le regroupement musical A/B/C ;
4. vérifier que les paroles servent seulement à qualifier Verse/Chorus/Bridge ;
5. vérifier l'absence d'interligne à l'intérieur d'un bloc ;
6. vérifier la présence d'un seul interligne entre blocs ;
7. vérifier le même comportement dans la grille et dans `Paroles + accords` ;
8. conserver la règle : **progression de mesures d'abord, qualification textuelle ensuite**.

### Lancement

```powershell
cd H:\ChordStation
python -m streamlit run .\chordstation_v24.py
```


## V25 — Persistance SQLite et métadonnées éditables

La V25 ajoute une persistance locale durable afin qu'un morceau déjà analysé ne soit pas recalculé systématiquement.

### Identité du morceau

La clé persistante principale est une empreinte SHA-256 du contenu audio :

```text
audio_hash = SHA256(audio_bytes)
```

Le nom de fichier n'est pas utilisé comme identité technique unique.

Ainsi, un même contenu audio renommé reste reconnu comme le même morceau.

### Base SQLite

Fichier local :

```text
data/chordstation.sqlite3
```

Tables créées :

```text
songs
analyses
block_edits
```

`block_edits` prépare l'édition future des noms de blocs.

### Métadonnées persistantes

Le morceau possède désormais :

```text
Titre
Auteur / Interprète
```

Ces champs sont éditables et sauvegardés dans SQLite.

Leur modification :

- ne relance pas Demucs ;
- ne relance pas Whisper ;
- ne relance pas l'analyse harmonique ;
- ne change pas la tonalité ;
- ne change pas les blocs détectés.

### Persistance de l'analyse

Une analyse est identifiée par :

```text
audio_hash
analysis_key
engine_version
parameters_json
```

L'`analysis_key` dépend des paramètres lourds d'analyse et de la version du moteur.

Si le même audio est rouvert avec les mêmes paramètres compatibles :

```text
SQLite -> musique + Whisper
```

et aucune nouvelle analyse lourde n'est lancée.

Si un paramètre d'analyse lourd change, une nouvelle entrée persistante peut être créée sans écraser les autres variantes.

### Capodastre

Le capo reste une couche d'affichage.

Il n'appartient pas à la clé d'analyse persistante.

Changer le capo doit donc rester immédiat et ne jamais provoquer Demucs / Whisper.

### Blocs

La V25 supprime les qualifications automatiques visibles :

```text
Verse probable
Chorus probable
Bridge possible
Intro
Outro
```

L'affichage principal reste volontairement neutre :

```text
Bloc A
Bloc B
Bloc C
...
```

La lettre identifie une famille de progression de mesures répétée.

Les noms de blocs seront éditables dans une version ultérieure.

### Impression future

Le titre et l'auteur persistants sont maintenant disponibles pour l'en-tête des futures feuilles imprimables :

```text
Titre
Auteur / Interprète
Tonalité réelle
Capo
Signature
```

### Validation V25

1. analyser un morceau une première fois ;
2. vérifier le message indiquant que l'analyse a été sauvegardée ;
3. relancer l'application ;
4. recharger exactement le même audio ;
5. vérifier que l'analyse est rechargée depuis SQLite ;
6. vérifier que Demucs et Whisper ne repartent pas ;
7. modifier le titre ;
8. modifier l'auteur / interprète ;
9. relancer l'application et recharger le morceau ;
10. vérifier que ces métadonnées sont conservées ;
11. changer seulement le capo et vérifier l'affichage immédiat ;
12. vérifier que les blocs sont affichés uniquement comme `Bloc A/B/C/...`.

### Lancement

```powershell
cd H:\ChordStation
python -m streamlit run .\chordstation_v25.py
```


## V26 — Blocs éditables et persistants

La V26 ajoute l'édition persistante des blocs structurels.

### Champs éditables

Pour chaque cluster technique :

```text
Bloc A
Nom
Mesure début
Mesure fin
```

Exemple :

```text
Bloc A
Nom : Couplet
Mesure début : 1
Mesure fin : 16
```

### Séparation détection / édition

L'analyse automatique est conservée séparément de l'édition utilisateur.

Exemple :

```text
Détection automatique :
Bloc C
mesures 25–32

Édition utilisateur :
Nom : Refrain
mesures 24–33
```

Les bornes détectées restent disponibles pour diagnostic.

### Persistance SQLite

Les champs suivants sont stockés dans `block_edits` :

```text
audio_hash
block_cluster
custom_label
measure_start
measure_end
updated_at
```

Une migration douce ajoute automatiquement `measure_start` et `measure_end` aux bases V25 existantes.

### Règles

- la mesure de début doit être inférieure ou égale à la mesure de fin ;
- les valeurs sont limitées au nombre réel de mesures du morceau ;
- une modification de bloc ne relance ni Demucs, ni Whisper, ni l'analyse harmonique ;
- les blocs de même cluster partagent l'édition persistante du cluster ;
- l'identifiant technique `A/B/C/...` reste distinct du nom utilisateur.

### Affichage

Si aucun nom personnalisé n'existe :

```text
Bloc A · mesures 1–16
```

Si un nom a été défini :

```text
Bloc A — Couplet · mesures 1–16
```

Le même nom et les mêmes bornes sont utilisés dans :

- la grille ;
- les paroles + accords ;
- le tableau structurel ;
- le résumé compact.

### Tableau structurel

La V26 expose :

```text
Bloc
Nom
Mesures
Détection
Confiance
Répétitions
Sim. harmonie
Sim. paroles
Progression
```

`Mesures` correspond aux bornes utilisateur effectives.

`Détection` conserve les bornes automatiques initiales.

### Validation V26

1. analyser ou recharger un morceau persistant ;
2. ouvrir `Éditer les blocs` ;
3. renommer `Bloc A` ;
4. modifier sa mesure de début et/ou de fin ;
5. enregistrer ;
6. vérifier que la grille est mise à jour sans réanalyse ;
7. vérifier la mise à jour de `Paroles + accords` ;
8. relancer Chordstation ;
9. recharger le même audio ;
10. vérifier que nom et bornes sont conservés ;
11. vérifier que les bornes détectées originales restent visibles séparément.

### Lancement

```powershell
cd H:\ChordStation
python -m streamlit run .\chordstation_v26.py
```


## V28 — Bibliothèque persistante, import et affichage des blocs

### Libellé des blocs

Dès qu'un bloc possède un nom utilisateur, seul ce nom est affiché.

Exemple :

```text
Couplet 1
```

et non :

```text
Bloc A — Couplet 1 · mesures 1–17
```

Les bornes de mesures restent disponibles dans l'éditeur et le tableau structurel, mais ne sont plus répétées dans le titre visible du bloc.

Si aucun nom utilisateur n'existe, le fallback reste :

```text
Bloc A
Bloc B
Bloc C
```

L'identifiant technique `A/B/C/...` reste conservé en interne pour la persistance.

### Paroles + accords

Le titre de chaque bloc dans le parolier est rendu plus visible :

- taille augmentée de 2 px ;
- graisse renforcée ;
- couleur d'accent ;
- interligne conservé uniquement entre les blocs.

L'intérieur de chaque bloc reste compact.

### Bibliothèque

La V28 introduit deux modes d'entrée :

```text
Catalogue
Import
```

#### Import

`Import` sert à ajouter une nouvelle chanson.

Lors du premier import :

1. le SHA-256 du fichier audio est calculé ;
2. le morceau est créé ou retrouvé dans SQLite ;
3. le fichier audio est archivé localement dans :

```text
data/audio/<sha256>.<extension>
```

4. l'analyse persistante existante est réutilisée si elle correspond déjà au même SHA-256 et aux mêmes paramètres.

#### Catalogue

Le catalogue liste les chansons persistées par ordre alphabétique :

```text
Titre
puis Auteur / Interprète
```

Un morceau sélectionné dans le catalogue est rouvert depuis son audio local archivé et ses données SQLite.

Les morceaux issus d'une ancienne version de la base peuvent exister sans copie locale de l'audio. Dans ce cas, l'interface demande de réimporter une seule fois le même fichier ; son SHA-256 rattache automatiquement l'audio à l'analyse déjà persistée.

### Enregistrement

Le formulaire `Titre / Auteur` utilise désormais un bouton principal :

```text
💾 Enregistrer
```

Cette opération ne relance aucune analyse audio.

Les éditions de blocs restent également persistées sans réanalyse.

### Persistance

La bibliothèque repose toujours sur :

```text
data/chordstation.sqlite3
```

et l'audio local sur :

```text
data/audio/
```

La séparation reste :

```text
SQLite = métadonnées + analyses + éditions
data/audio = sources audio persistantes
```

### Roadmap restante

Deux étapes majeures restent prévues :

#### Impression

Choix explicite :

```text
Imprimer :
- Grille
- Paroles + accords
```

La sortie devra utiliser :

- titre ;
- auteur / interprète ;
- tonalité réelle ;
- capo ;
- signature ;
- noms édités des blocs.

#### Player synchronisé

Choix explicite :

```text
Player :
- Grille
- Paroles + accords
```

Le player devra utiliser un playhead unique pour synchroniser :

- audio ;
- mesure courante ;
- accord courant ;
- ligne de paroles courante ;
- bloc courant.

### Validation V28

1. renommer un bloc en `Couplet 1` ;
2. vérifier que seul `Couplet 1` est affiché dans la grille ;
3. vérifier le même comportement dans le parolier ;
4. vérifier que le titre du bloc dans le parolier est plus grand et coloré ;
5. importer une nouvelle chanson ;
6. vérifier qu'elle apparaît dans le catalogue ;
7. vérifier le tri alphabétique ;
8. fermer puis relancer Chordstation ;
9. sélectionner le morceau depuis le catalogue sans réimport ;
10. vérifier que l'analyse persistante est rechargée sans Demucs / Whisper ;
11. modifier titre / auteur puis cliquer `Enregistrer` ;
12. vérifier la persistance après relance.

### Lancement

```powershell
cd H:\ChordStation
python -m streamlit run .\chordstation_v28.py
```


## V29 — Chargement catalogue, tri Titre/Auteur et correction d'en-tête

### En-tête

La V29 corrige l'en-tête principal tronqué en augmentant l'espace supérieur et le `line-height` du titre.

### Catalogue

Le catalogue possède désormais un vrai bouton :

```text
📂 Charger la chanson
```

Sélectionner une entrée dans la liste ne charge plus automatiquement le morceau.

Le flux devient :

```text
Catalogue
→ choisir le tri
→ sélectionner le morceau
→ Charger la chanson
→ ouvrir audio + analyse persistante
```

### Tri alphabétique

Le catalogue peut être trié au choix :

```text
Titre
Auteur / Interprète
```

#### Tri par titre

Affichage :

```text
La Bohème — Charles Aznavour
```

Ordre :

```text
titre
puis auteur/interprète
```

#### Tri par auteur / interprète

Affichage :

```text
Charles Aznavour — La Bohème
```

Ordre :

```text
auteur/interprète
puis titre
```

### Pourquoi certains anciens morceaux demandent encore un import unique

Les analyses créées avant l'introduction de l'archivage audio persistent bien dans SQLite, mais leur fichier audio original n'a jamais été copié dans :

```text
data/audio/
```

La base ne contient donc pas les octets audio nécessaires au player et à la réouverture complète.

Pour ces seuls anciens morceaux :

```text
réimport unique du même fichier
→ calcul SHA-256
→ rattachement à l'analyse persistante existante
→ archivage audio local
```

L'analyse lourde n'est pas recalculée si la clé d'analyse correspond.

À partir de V28/V29, tout nouvel import archive automatiquement le fichier audio, donc il n'est plus nécessaire de le réimporter ensuite.

### Persistance de bibliothèque

Un morceau entièrement géré par la bibliothèque comprend :

```text
SQLite
- titre
- auteur/interprète
- analyses
- éditions de blocs

data/audio
- fichier audio source archivé
```

Le catalogue peut ensuite le rouvrir directement avec `Charger la chanson`.

### Validation V29

1. vérifier que le titre Chordstation n'est plus tronqué ;
2. choisir `Catalogue` ;
3. sélectionner `Tri alphabétique : Titre` ;
4. vérifier l'ordre des chansons ;
5. sélectionner `Auteur / Interprète` ;
6. vérifier le nouvel ordre et le format `Auteur — Titre` ;
7. sélectionner un morceau puis cliquer `Charger la chanson` ;
8. vérifier qu'un morceau archivé s'ouvre sans nouvel import ;
9. pour un morceau créé avant l'archivage audio, réimporter une seule fois le même fichier ;
10. revenir ensuite dans le catalogue et vérifier qu'il se charge directement ;
11. vérifier qu'aucune analyse lourde n'est relancée si l'analyse persistante existe.

### Roadmap restante

Les deux prochaines étapes restent :

```text
Imprimer
- Grille
- Paroles + accords

Player synchronisé
- Grille
- Paroles + accords
```

### Lancement

```powershell
cd H:\ChordStation
python -m streamlit run .\chordstation_v29.py
```


## V30 — Paramètres persistants, versions d'analyse et corrections synchronisées

### En-tête

La V30 remplace le `st.title()` principal par un en-tête HTML dédié afin d'éviter le rognage vertical observé dans certaines configurations navigateur / Streamlit.

### Paramètres d'analyse persistants

Les paramètres étaient déjà stockés dans `analyses.parameters_json`, mais ils n'étaient pas automatiquement réinjectés dans les widgets au chargement d'un morceau.

La V30 corrige ce point.

Lorsqu'un morceau est chargé depuis le catalogue :

```text
Catalogue
→ Charger la chanson
→ lecture de la dernière analyse persistée
→ restauration des paramètres dans la sidebar
→ rerun
```

Paramètres restaurés :

```text
signature rythmique
fréquence d'analyse
hop_length
seuil silence RMS
seuil silence harmonique
poids de la fondamentale
détection point d'orgue
seuil point d'orgue
```

Le capo reste volontairement hors de ce mécanisme car il s'agit d'un réglage de représentation.

### Versions d'analyse

La V30 ajoute :

```text
analysis_versions
```

Chaque nouvelle analyse réellement recalculée est automatiquement sauvegardée comme une nouvelle version numérotée.

Exemple :

```text
Version 1
Version 2
Version 3
```

L'interface expose également :

```text
🗂️ Versions d'analyse
```

et un bouton :

```text
💾 Sauver l'analyse courante comme nouvelle version
```

Cela permet de conserver plusieurs états d'analyse d'un même morceau au lieu d'écraser silencieusement le précédent.

### Corrections manuelles accords / battements

La V30 ajoute une table persistante :

```text
beat_edits
```

Clé :

```text
audio_hash
beat_index
```

Valeurs :

```text
chord_override
time_offset_ms
updated_at
```

L'éditeur est accessible depuis :

```text
Grille
Paroles
```

avec le même modèle de données.

Pour une mesure donnée, chaque beat peut être corrigé sur :

```text
Accord
Décalage temporel en millisecondes
```

### Synchronisation grille / parolier

Les corrections ne sont jamais appliquées seulement à une vue.

Le pipeline devient :

```text
analyse brute persistée
→ beat_edits
→ beats effectifs
→ reconstruction des mesures
→ grille
→ paroles + accords
→ structure
→ timeline
```

Une correction effectuée depuis la grille est donc visible dans le parolier après enregistrement, et inversement.

La donnée détectée brute reste préservée.

### Reset

L'éditeur permet également de réinitialiser les corrections de la mesure courante.

### Titres de blocs

Les titres de blocs sont maintenant affichés en bleu dans :

```text
Grille
Paroles + accords
```

Le parolier conserve une taille de titre supérieure de 2 px.

### Contrat important

Les corrections manuelles :

- ne relancent pas Demucs ;
- ne relancent pas Whisper ;
- ne modifient pas l'analyse brute persistée ;
- sont sauvegardées séparément ;
- alimentent toutes les vues à partir d'une source commune.

### Validation V30

1. charger un morceau depuis le catalogue ;
2. vérifier que les paramètres de la dernière analyse reviennent dans la sidebar ;
3. modifier un paramètre lourd puis appliquer ;
4. vérifier qu'une nouvelle analyse est calculée et sauvegardée comme nouvelle version ;
5. ouvrir `Versions d'analyse` et vérifier l'historique ;
6. ouvrir l'éditeur accords/battements dans la grille ;
7. modifier un accord ;
8. enregistrer ;
9. vérifier le même accord dans le parolier ;
10. modifier un décalage temporel ;
11. vérifier que la projection paroles / grille reste synchronisée ;
12. faire la même correction depuis l'éditeur du parolier et vérifier la grille ;
13. relancer Chordstation et vérifier que les corrections persistent ;
14. vérifier les titres de blocs en bleu ;
15. vérifier que l'en-tête principal n'est plus tronqué.

### Roadmap restante

Les deux chantiers principaux restent :

```text
Impression
- Grille
- Paroles + accords

Player synchronisé
- Grille
- Paroles + accords
```

La persistance des corrections manuelles constitue désormais la base commune pour ces deux futures fonctions.

### Lancement

```powershell
cd H:\ChordStation
python -m streamlit run .\chordstation_v30.py
```


## V31 — Dernier morceau rouvert automatiquement et catalogue robuste

### En-tête

Le titre principal n'utilise plus `st.title()` et reçoit désormais :

```text
font-size réduit
line-height augmenté
padding-top augmenté
min-height explicite
overflow visible
```

Objectif : supprimer définitivement le rognage vertical observé dans certains rendus navigateur/Streamlit.

### Dernier morceau ouvert

La V31 ajoute une table :

```text
app_state
```

Elle mémorise notamment :

```text
last_song_hash
source_mode
catalog_sort
```

Ainsi, après avoir ouvert un morceau depuis le catalogue :

```text
fermer Chordstation
→ relancer
→ le dernier morceau est rouvert automatiquement
```

Il n'est plus nécessaire de cliquer `Ouvrir` à chaque démarrage pour le morceau courant.

Le bouton `📂 Ouvrir` reste disponible pour changer explicitement de chanson.

### Import

Lorsqu'une nouvelle chanson est importée :

1. son SHA-256 est calculé ;
2. son audio est archivé dans `data/audio/` ;
3. elle devient automatiquement le dernier morceau actif ;
4. si une analyse persistante correspondant déjà au même SHA-256 existe, elle est réutilisée.

Une chanson importée à partir de V28/V29/V30/V31 ne doit plus demander son fichier source aux démarrages suivants.

### Anciens morceaux

Important : une chanson analysée avant l'introduction de SQLite et de l'archivage audio n'existe pas automatiquement dans la bibliothèque persistante.

Si `Susanna` a été analysée avec une ancienne version avant V25, son résultat pouvait être présent uniquement dans le cache Streamlit de l'époque. Ce cache n'est pas une entrée de catalogue durable.

Dans ce cas, une seule nouvelle importation de `Susanna` est nécessaire pour créer :

```text
songs
analyses
data/audio/<sha256>.<extension>
```

À partir de cette importation, elle reste au catalogue.

### Réparation du catalogue audio

La V31 tente également une migration automatique des fichiers déjà présents dans :

```text
data/audio/
```

Si un fichier archivé possède un nom SHA-256 valide mais aucune entrée correspondante dans `songs`, une entrée de catalogue est recréée.

Cette migration ne peut toutefois pas reconstruire un morceau ancien dont aucun audio ni aucune entrée SQLite n'a jamais été persisté.

### Tri

Le choix de tri est maintenant lui-même persistant :

```text
Titre
Auteur / Interprète
```

Le dernier tri choisi est restauré au prochain démarrage.

### Validation V31

1. importer La Bohème une fois ;
2. vérifier que `data/audio/<sha256>.<extension>` existe ;
3. fermer l'application ;
4. relancer ;
5. vérifier que La Bohème est ouverte automatiquement ;
6. changer de morceau via `📂 Ouvrir` ;
7. relancer et vérifier que ce nouveau morceau devient le morceau courant ;
8. vérifier que le tri Titre/Auteur est conservé ;
9. vérifier l'en-tête non tronqué ;
10. pour Susanna : si elle date d'avant la persistance, l'importer une seule fois puis vérifier qu'elle reste ensuite dans le catalogue.

### Roadmap restante

```text
Impression
- Grille
- Paroles + accords

Player synchronisé
- Grille
- Paroles + accords
```

### Lancement

```powershell
cd H:\ChordStation
python -m streamlit run .\chordstation_v31.py
```


## V32 — Répertoire alphabétique réel

La V32 remplace le `selectbox` du catalogue par un vrai répertoire destiné à supporter un grand nombre de chansons.

### Navigation principale

La bibliothèque est séparée en deux onglets :

```text
Répertoire
Import
```

`Répertoire` sert à parcourir les chansons persistées.

`Import` sert uniquement à ajouter une nouvelle chanson.

### Classement

Le répertoire peut être classé au choix par :

```text
Titre
Auteur / Interprète
```

Le choix est persisté.

### Index alphabétique

Le répertoire expose :

```text
Tous
#
A B C D ... Z
```

La lettre active filtre immédiatement la liste.

`#` regroupe les titres ou auteurs dont le premier caractère n'est pas A-Z.

La lettre sélectionnée est persistée.

### Recherche

Un champ de recherche filtre sur :

```text
titre
auteur / interprète
nom de fichier original
```

La recherche se combine avec l'index alphabétique.

### Présentation

En mode Titre :

```text
B

La Bohème
Charles Aznavour
[Ouvrir]
```

En mode Auteur / Interprète :

```text
A

Charles Aznavour
La Bohème
[Ouvrir]
```

Les chansons sont regroupées sous leur initiale.

### Ouverture

Chaque chanson possède son propre bouton :

```text
Ouvrir
```

Le morceau actuellement actif est repéré par :

```text
▶
```

Cliquer `Ouvrir` :

1. mémorise le morceau courant ;
2. restaure les derniers paramètres d'analyse persistés ;
3. recharge l'audio local archivé ;
4. recharge l'analyse persistante si compatible ;
5. ne redemande pas l'import si l'audio existe dans `data/audio`.

### Import

Après import :

```text
SHA-256
→ songs
→ data/audio
→ last_song_hash
```

La chanson apparaît ensuite dans le répertoire et reste disponible aux lancements suivants.

### Compteur

Le répertoire affiche le nombre total de chansons persistées.

Exemple :

```text
127 chanson(s) dans le répertoire
```

### Validation V32

1. vérifier l'affichage des deux chansons actuellement présentes ;
2. tester `Titre` ;
3. tester `Auteur / Interprète` ;
4. tester les index `A`, `B`, `S` ;
5. tester `Tous` ;
6. tester la recherche `Susanna` ;
7. tester la recherche `Aznavour` ;
8. ouvrir une chanson ;
9. vérifier l'indicateur `▶` ;
10. relancer Chordstation ;
11. vérifier que la chanson courante reste sélectionnée ;
12. importer un nouveau morceau et vérifier son apparition immédiate dans le répertoire.

### Roadmap restante

```text
Impression
- Grille
- Paroles + accords

Player synchronisé
- Grille
- Paroles + accords
```

### Lancement

```powershell
cd H:\ChordStation
python -m streamlit run .\chordstation_v32.py
```


## V32b — Correction ouverture du répertoire

### Terminologie

L'interface principale utilise désormais le terme :

```text
Répertoire
```

et non plus `Bibliothèque`.

### Erreur corrigée

L'ouverture d'un morceau depuis le répertoire provoquait :

```text
StreamlitWidgetAlreadyInstantiatedError
```

Cause :

```text
hydrate_settings_from_parameters(...)
```

essayait de modifier `st.session_state` pour des widgets de réglages déjà instanciés pendant le même rerun.

### Correctif

Le chargement passe désormais par un état temporaire :

```text
_pending_analysis_settings
```

Flux :

```text
clic Ouvrir
→ charger latest_params
→ stocker dans _pending_analysis_settings
→ st.rerun()
→ appliquer les paramètres AVANT création des widgets
→ construire la sidebar avec les valeurs restaurées
```

Le même mécanisme est utilisé lorsqu'un import correspond à un morceau déjà connu.

### Résultat attendu

Cliquer sur :

```text
Ouvrir
```

doit :

- ouvrir le morceau ;
- restaurer ses paramètres persistés ;
- ne plus provoquer d'erreur Streamlit ;
- ne pas relancer inutilement Demucs / Whisper si l'analyse compatible existe.

### Validation V32b

1. lancer Chordstation ;
2. ouvrir `Répertoire` ;
3. cliquer `Ouvrir` sur La Bohème ;
4. vérifier l'absence d'erreur `StreamlitWidgetAlreadyInstantiatedError` ;
5. vérifier la restauration de la signature, fréquence, hop length et seuils ;
6. ouvrir ensuite Susanna ;
7. vérifier le même comportement ;
8. relancer l'application et vérifier le dernier morceau persistant.

### Lancement

```powershell
cd H:\ChordStation
python -m streamlit run .\chordstation_v32b.py
```


## V33 — Menu principal Répertoire / Chanson / Import

La V33 remplace la page unique très longue par une navigation principale.

### Menu

Le haut de l'application expose :

```text
Répertoire | Chanson | Import
```

### Répertoire

Affiche uniquement :

- tri Titre / Auteur ;
- recherche ;
- index Tous / # / A-Z ;
- liste des morceaux ;
- bouton `Ouvrir`.

Cliquer `Ouvrir` :

```text
Répertoire
→ sélection du morceau
→ restauration des paramètres persistés
→ bascule automatique vers Chanson
```

### Chanson

Affiche uniquement le morceau courant :

- player audio ;
- titre / auteur ;
- paramètres ;
- grille ;
- éditeurs ;
- paroles ;
- structure ;
- timeline ;
- versions d'analyse.

Le Répertoire n'est plus affiché au-dessus de la chanson.

### Import

Affiche uniquement le contrôle d'import.

Après import :

```text
audio archivé
→ entrée répertoire
→ morceau actif
→ bascule automatique vers Chanson
```

### Cycle Streamlit

Le changement automatique de menu utilise :

```text
_pending_main_menu
```

puis `st.rerun()`.

Cela évite de modifier directement l'état du widget de navigation après son instanciation.

### Validation V33

1. ouvrir Répertoire ;
2. ouvrir Susanna ;
3. vérifier la bascule automatique vers Chanson ;
4. vérifier que seul le morceau est affiché ;
5. revenir manuellement sur Répertoire via le menu ;
6. ouvrir La Bohème ;
7. vérifier la nouvelle bascule ;
8. tester Import ;
9. vérifier qu'un nouvel import bascule vers Chanson ;
10. vérifier qu'il n'y a plus de page unique Répertoire + chanson à faire défiler.

### Roadmap restante

```text
Impression
- Grille
- Paroles + accords

Player synchronisé
- Grille
- Paroles + accords
```

### Lancement

```powershell
cd H:\ChordStation
python -m streamlit run .\chordstation_v33.py
```


## V33b — Ouverture sans réanalyse implicite

### Problème corrigé

Un morceau déjà analysé pouvait être recalculé à l'ouverture si les valeurs courantes des widgets ne produisaient pas exactement la même `analysis_key` que l'analyse persistée.

Ce comportement est interdit.

### Nouveau contrat

Ouvrir une chanson depuis le Répertoire ne doit jamais lancer automatiquement :

```text
Demucs
Whisper
analyse harmonique
```

### Ordre de décision

À l'ouverture :

```text
1. chercher une analyse persistée correspondant exactement aux paramètres
2. si elle existe -> la charger
3. sinon, charger la dernière analyse persistée du morceau
4. ne recalculer que si l'utilisateur clique explicitement :
   Appliquer les paramètres
```

Pour un morceau jamais analysé :

```text
aucune analyse persistée
-> première analyse
-> sauvegarde SQLite
-> création d'une version
```

### Paramètres

Les paramètres de la dernière analyse restent restaurés à l'ouverture.

Un décalage temporaire entre les widgets et la clé persistée ne doit plus provoquer de nouvelle analyse.

### Nouvelle analyse volontaire

Pour créer une nouvelle version :

```text
modifier les paramètres
-> Appliquer les paramètres
-> nouvelle analyse
-> nouvelle version persistée
```

### Validation V33b

1. ouvrir Susanna depuis Répertoire ;
2. vérifier que Demucs ne repart pas ;
3. vérifier que Whisper ne repart pas ;
4. vérifier le message `Analyse persistante chargée` ;
5. modifier un paramètre lourd ;
6. ne pas cliquer Appliquer et vérifier qu'aucune analyse ne repart ;
7. cliquer explicitement `Appliquer les paramètres` ;
8. vérifier qu'une nouvelle analyse est alors créée et versionnée.

### Lancement

```powershell
cd H:\ChordStation
python -m streamlit run .\chordstation_v33b.py
```


## V34 — Blocs séquentiels, scission et fusion

### Principe

Les blocs ne sont plus édités comme des objets indépendants.

Ils forment désormais une **partition continue du morceau** :

```text
Bloc 1 fin = X
→ Bloc 2 début = X + 1
```

et réciproquement :

```text
Bloc 2 début = Y
→ Bloc 1 fin = Y - 1
```

### Garanties

La structure persistante respecte toujours :

```text
premier bloc commence à la mesure 1
aucun trou entre les blocs
aucun chevauchement
chaque bloc contient au moins une mesure
dernier bloc finit à la dernière mesure
```

### Nouveau stockage

La V34 ajoute :

```text
structure_blocks
```

Cette table stocke chaque occurrence de bloc individuellement :

```text
audio_hash
block_id
order_index
cluster
custom_label
measure_start
measure_end
detected_measure_start
detected_measure_end
updated_at
```

Ceci corrige une limitation des versions précédentes où une édition attachée au cluster A/B/C pouvait modifier plusieurs occurrences à la fois.

### Migration

Lors de la première ouverture :

1. la détection structurelle fournit les blocs initiaux ;
2. une partition continue est créée ;
3. les anciens noms personnalisés de `block_edits` sont récupérés si possible ;
4. les anciennes bornes indépendantes sont volontairement ignorées si elles créaient trous ou chevauchements.

### Édition des frontières

Modifier :

```text
Mesure début
Mesure fin
```

recalcule automatiquement les voisins.

Le début du premier bloc est verrouillé à `1`.

La fin du dernier bloc est verrouillée à la dernière mesure.

### Scission

Chaque bloc de plus d'une mesure propose :

```text
Scinder après la mesure N
[Scinder]
```

Exemple :

```text
Bloc C : 25–40
Scinder après 32
```

devient :

```text
Bloc C : 25–32
Bloc X : 33–40
```

Le nouveau bloc reçoit un nouvel identifiant technique interne et peut être renommé ensuite.

### Fusion

Chaque bloc sauf le dernier propose :

```text
Fusionner avec le suivant
```

Exemple :

```text
Couplet 1 : 1–16
Bloc B : 17–24
```

devient :

```text
Couplet 1 : 1–24
```

La frontière intermédiaire disparaît.

### Persistance

Les opérations :

```text
renommer
changer frontière
scinder
fusionner
```

sont persistées sans relancer :

```text
Demucs
Whisper
analyse harmonique
```

### Validation V34

1. ouvrir un morceau déjà analysé ;
2. modifier la fin d'un bloc, par exemple `33` ;
3. vérifier que le bloc suivant commence automatiquement à `34` ;
4. modifier le début d'un bloc intermédiaire ;
5. vérifier que la fin du précédent est recalée ;
6. vérifier l'absence de trou et chevauchement ;
7. scinder un bloc ;
8. vérifier l'apparition immédiate du nouveau bloc ;
9. le renommer ;
10. fusionner deux blocs ;
11. relancer Chordstation ;
12. vérifier que toute la structure éditée est conservée.

### Roadmap

Restent ensuite :

```text
Impression
- Grille
- Paroles + accords

Player synchronisé
- Grille
- Paroles + accords
```

### Lancement

```powershell
cd H:\ChordStation
python -m streamlit run .\chordstation_v34.py
```


## V35 — Grille éditable par mesure et parolier structuré par blocs

### Grille

Le principe d'édition devient explicitement musical :

```text
1 case = 1 mesure
```

Les champs `Beat 1 / Beat 2 / Décalage ms` disparaissent de l'interface principale.

Chaque mesure est éditée directement avec la notation Chordstation :

```text
Am---
Am-Em-
D.C-
Am-- | Em--
```

Le nombre de positions attendu dépend de la signature active.

### Validation syntaxique

Une mesure est validée avant sauvegarde.

Règles principales :

```text
- = tenue de l'accord précédent
. = silence harmonique
^ = point d'orgue final
| = séparateur visuel pour 6/8 et 12/8
```

Une notation qui ne contient pas le bon nombre de positions est refusée.

### Capodastre

La grille reste éditée sous la forme réellement jouée par le musicien.

Exemple :

```text
accord réel : Cm
capo 3
forme affichée / éditée : Am
```

À la sauvegarde, Chordstation reconvertit la forme capo vers l'accord réel avant persistance.

Ainsi :

```text
analyse interne = tonalité réelle
interface = formes à jouer
```

### Persistance des corrections de grille

Nouvelle table :

```text
measure_edits
```

Colonnes :

```text
audio_hash
measure_no
notation_real
updated_at
```

Les corrections sont appliquées aux beats internes puis propagées à :

```text
grille
parolier
structure
timeline
```

sans relancer Demucs ou Whisper.

### Sauvegarde par bloc

Chaque bloc possède :

```text
Enregistrer <nom du bloc>
Réinitialiser <nom du bloc>
```

La sauvegarde traite toutes les mesures du bloc.

### Éditeur de blocs simplifié

L'éditeur n'expose plus simultanément début et fin.

Le musicien édite :

```text
Nom
Mesure fin
```

Le début est calculé automatiquement :

```text
fin bloc précédent + 1
```

Le premier bloc commence toujours à 1.

Le dernier bloc finit toujours à la dernière mesure.

### Scission

La commande de scission est rangée dans :

```text
Scinder ce bloc
```

Elle ne montre le choix de mesure qu'au moment où la fonction est ouverte.

### Fusion

La commande :

```text
Fusionner avec le suivant
```

supprime une frontière structurelle.

### Parolier

La structure persistante des blocs est maintenant la charpente exacte du parolier.

Exemple :

```text
Couplet 1
  lignes de paroles du Couplet 1

Refrain
  lignes de paroles du Refrain

Couplet 2
  lignes de paroles du Couplet 2
```

Un mot est affecté à un seul bloc selon sa position temporelle.

Une ligne de paroles ne peut donc plus être dupliquée dans deux blocs adjacents.

### Lisibilité des paroles

À l'intérieur d'un bloc, les retours de ligne utilisent :

```text
ponctuation
pauses vocales
longueur maximale
```

Il n'y a pas d'interligne artificiel entre les lignes d'un même bloc.

L'espace visuel est réservé à la séparation entre blocs.

Les titres de blocs restent bleus.

### Bloc instrumental

Un bloc sans parole est conservé dans le parolier avec :

```text
[instrumental]
```

afin que la structure du morceau reste lisible.

### Contrat commun

La même partition persistante alimente désormais :

```text
Grille
Paroles + accords
Structure
future impression
futur player
```

### Validation V35

1. ouvrir un morceau déjà analysé ;
2. ouvrir l'éditeur des blocs ;
3. modifier la fin d'un bloc ;
4. vérifier que le début du suivant est recalé automatiquement ;
5. scinder un bloc ;
6. vérifier le nouveau bloc dans la grille ET le parolier ;
7. fusionner deux blocs ;
8. vérifier la disparition de la frontière dans les deux vues ;
9. modifier une case de grille ;
10. enregistrer le bloc ;
11. vérifier la correction dans le parolier ;
12. relancer Chordstation ;
13. vérifier la persistance des blocs et des mesures éditées ;
14. vérifier qu'aucune réanalyse audio n'est lancée.

### Roadmap restante

```text
Impression
- Grille
- Paroles + accords

Player synchronisé
- Grille
- Paroles + accords
```

### Lancement

```powershell
cd H:\ChordStation
python -m streamlit run .\chordstation_v35.py
```


## V36 — Tableau simple de découpage

La V36 remplace l'éditeur de blocs complexe par une seule table.

### Interface

```text
Nom         Début   Fin
Couplet 1      1     17
Refrain 1     18     24
Couplet 2     25     40
...
```

Sous la table :

```text
💾 Enregistrer le découpage
✂ Ajouter une séparation
↩ Réinitialiser depuis l’analyse
```

### Règles

- `Début` n'est pas éditable directement ;
- le début d'un bloc = fin du précédent + 1 ;
- le premier bloc commence toujours à 1 ;
- le dernier bloc finit toujours à la dernière mesure ;
- aucune superposition ;
- aucun trou ;
- chaque bloc contient au moins une mesure.

### Ajouter une séparation

`Ajouter une séparation` demande seulement :

```text
Après la mesure : N
```

La frontière est ajoutée au bloc contenant cette mesure.

Le nouveau bloc reçoit par défaut :

```text
Nouveau bloc
```

et peut ensuite être renommé directement dans la table.

### Réinitialiser depuis l’analyse

Le reset supprime uniquement :

```text
structure_blocks
```

pour le morceau courant.

Il conserve :

```text
audio
analyse harmonique
Whisper
titre / auteur
corrections de grille par mesure
versions d'analyse
```

Au rerun suivant, le découpage est reconstruit depuis l'analyse persistée.

Aucune réanalyse Demucs / Whisper n'est lancée.

### Structure commune

Ce tableau pilote la même structure persistante pour :

```text
grille
parolier
future impression
futur player
```

### Validation V36

1. ouvrir un morceau ;
2. ouvrir `Découpage du morceau` ;
3. modifier la fin de `Couplet 1` ;
4. enregistrer ;
5. vérifier que le début du bloc suivant est automatiquement recalé ;
6. ajouter une séparation ;
7. vérifier `Nouveau bloc` dans la table, la grille et le parolier ;
8. renommer ce nouveau bloc ;
9. réinitialiser depuis l'analyse ;
10. vérifier le retour au découpage initial sans Demucs / Whisper.

### Lancement

```powershell
cd H:\ChordStation
python -m streamlit run .\chordstation_v36.py
```

## V36c+ — Décisions validées pour la suite

### 1. Découpage structurel

L'éditeur de blocs doit rester volontairement simple :

```text
Nom          Début   Fin   Nb mesures
Couplet 1      1      17       17
Refrain 1     18      34       17
Couplet 2     35      52       18
...
```

Règles :

- `Nom` éditable ;
- `Fin` éditable ;
- `Début` calculé automatiquement ;
- `Nb mesures` calculé automatiquement avec `Fin - Début + 1` ;
- premier bloc toujours à la mesure 1 ;
- dernier bloc toujours à la dernière mesure ;
- aucun trou ;
- aucun chevauchement ;
- chaque bloc contient au moins une mesure.

Lorsqu'une `Fin` est déplacée, tous les blocs suivants doivent se décaler automatiquement en conservant leur durée autant que possible.

Exemple :

```text
Refrain 1 : 18–33
=> Couplet 2 commence automatiquement à 34
=> tous les blocs suivants sont décalés
```

Opérations disponibles :

```text
💾 Enregistrer le découpage
✂ Ajouter une séparation
↩ Réinitialiser depuis l’analyse
```

`Ajouter une séparation` demande seulement une mesure et crée un bloc nommé par défaut :

```text
Nouveau bloc
```

`Réinitialiser depuis l’analyse` supprime seulement la structure manuelle du morceau et reconstruit le découpage depuis l'analyse déjà persistée.

Le reset NE DOIT PAS relancer :

```text
Demucs
Whisper
analyse harmonique
```

Il conserve notamment :

```text
audio
analyse persistée
titre / artiste
corrections de grille
versions d'analyse
```

Le même découpage structurel doit alimenter :

```text
grille
parolier
future impression
futur player
```

---

### 2. Grille

Contrat maintenu :

- 1 cellule = 1 mesure ;
- notation Chordstation conservée ;
- pas de notation ChordU ;
- pas de retour vers un éditeur beat-par-beat visible.

Notation :

```text
- = accord tenu au beat suivant
. = beat non joué / silence harmonique
^ = point d'orgue détecté uniquement
```

Exemples :

```text
Am---
Am-Em-
Am...
D.C-
G---^
```

Le capo reste un post-traitement d'affichage et ne doit jamais modifier l'analyse du signal.

---

### 3. Parolier : contrat visuel validé

Le parolier doit ressembler à une vraie feuille `paroles + accords`.

Point essentiel : on conserve la notation métrique Chordstation (`Am---`, `Em--`, etc.) ET on décale les paroles / syllabes horizontalement afin qu'elles tombent sous les accords au bon moment.

Exemple de principe :

```text
Am---              Am---
    Je vous parle d'un temps
                       Am---
    Que les moins de vingt ans
                        Em---
    Ne peuvent pas connaître.
```

Pour une ligne plus chargée :

```text
E7- Am- Am- Em7- Em7- Am- B7- Em-
La bohème,   la bohème, ça voulait dire, on est heureux
```

Le moteur de parolier ne doit donc PAS simplement imprimer les mesures en tête d'une ligne de texte.

Il doit utiliser :

```text
timestamps des beats / changements d'accord
+
timestamps Whisper des mots
```

puis calculer l'alignement horizontal.

Principe :

```text
ligne d'accords construite selon le temps
+
paroles positionnées selon les timestamps Whisper
=
alignement accord <-> syllabe / mot
```

#### Police

Le parolier doit utiliser une police NON PROPORTIONNELLE / MONOSPACE pour les accords ET les paroles.

Contraintes CSS / rendu :

```text
font-family: monospace
white-space: pre ou pre-wrap
même taille de caractère pour accords et paroles
même métrique horizontale
pas de police proportionnelle
```

L'alignement doit être calculé en colonnes / caractères, pas avec une approximation visuelle en pixels utilisant une police proportionnelle.

#### Découpage des lignes

Les lignes doivent rester lisibles :

- ponctuation ;
- pauses vocales ;
- longueur maximale raisonnable ;
- aucune ligne ne traverse deux blocs structurels ;
- changement de découpage => parolier recalculé immédiatement ;
- vraie séparation verticale entre blocs ;
- pas d'espacement excessif à l'intérieur d'un bloc.

Les noms de blocs restent la charpente visuelle du parolier.

---

### 4. Persistance des paramètres par morceau

Défaut constaté : les paramètres avancés et le capo ne sont pas tous persistés / restaurés correctement lorsqu'une chanson est rouverte depuis le Répertoire.

Contrat à appliquer :

```text
Morceau
├─ Titre
├─ Artiste
├─ Capo
├─ Paramètres d’analyse
│  ├─ signature
│  ├─ fréquence d’échantillonnage
│  ├─ hop length
│  ├─ seuil RMS / silence
│  ├─ seuil harmonique
│  ├─ poids fondamentale
│  ├─ réglages de point d’orgue
│  ├─ modèle Whisper
│  └─ device Whisper
├─ Paramètres structurels
│  ├─ activation
│  ├─ taille / options éventuelles
│  └─ sensibilité éventuelle
└─ Éditions
   ├─ découpage
   ├─ accords par mesure
   └─ paroles à venir
```

#### Ouverture d'une chanson existante

À l'ouverture depuis le Répertoire :

```text
restaurer paramètres persistés
+
restaurer capo
+
charger analyse persistée
+
charger découpage / corrections
```

et surtout :

```text
AUCUNE réanalyse implicite
AUCUN Demucs implicite
AUCUN Whisper implicite
```

Si la combinaison exacte de paramètres n'existe pas, charger la dernière analyse persistée du morceau tant que l'utilisateur n'a pas explicitement demandé une nouvelle analyse.

#### Modification de paramètres d'analyse

Changer un widget d'analyse ne doit pas lancer de traitement immédiatement.

Flux :

```text
modifier paramètres
=> aucune analyse

cliquer "Appliquer les paramètres"
=> nouvelle analyse explicite
=> sauvegarde d'une nouvelle version
=> nouveaux paramètres deviennent ceux du morceau
```

#### Capo

Le capo est une préférence persistante du morceau.

Flux :

```text
modifier capo
=> sauvegarde immédiate
=> réaffichage immédiat des formes jouées
=> aucune réanalyse
=> aucun Demucs
=> aucun Whisper
```

À l'ouverture suivante, le capo sauvegardé doit être restauré avant le rendu de la grille et du parolier.

---

### 5. Priorités suivantes

Ordre de travail recommandé :

```text
1. corriger persistance / restauration de tous les paramètres + capo
2. refaire le moteur d'alignement monospace accords / paroles
3. valider grille + parolier sur La Bohème et Susanna
4. impression
5. player synchronisé
```

L'impression devra proposer au minimum :

```text
Grille
Paroles + accords
```

Le player synchronisé devra proposer les mêmes deux vues et utiliser une seule timeline commune pour :

```text
audio
mesure courante
accord courant
ligne / mot courant
bloc courant
```

---

### 6. Rappel fondamental

Contrat musical global :

> Interpréter le signal audio, ne pas inventer une progression.

Les améliorations UI, structurelles et de persistance ne doivent jamais contourner cette règle.

## V37 — Persistance paramètres avancés + capo

### Objectif

À l'ouverture d'une chanson depuis le Répertoire, Chordstation doit restaurer :

```text
Capo
Signature
Fréquence d'analyse
Hop length
Seuil silence RMS
Seuil silence harmonique
Poids de la fondamentale
Détection point d'orgue
Seuil point d'orgue
Détection structurelle
Taille de bloc structurel
Sensibilité de répétition
```

sans relancer implicitement Demucs, Whisper ou l'analyse harmonique.

### Nouvelle persistance

Table SQLite locale :

```text
song_preferences
├─ audio_hash
├─ capo
├─ settings_json
└─ updated_at
```

Cette table reste dans `data/chordstation.sqlite3`, donc locale et ignorée par Git.

### Ouverture d'un morceau

Ordre de restauration :

```text
1. paramètres de la dernière analyse persistée = fallback historique
2. song_preferences = préférences propres au morceau, prioritaires
3. injection dans session_state AVANT l'instanciation des widgets
4. rendu de la chanson
```

Cela évite `StreamlitWidgetAlreadyInstantiatedError`.

### Capo

Le capo reste strictement un paramètre d'affichage.

```text
modifier capo
=> sauvegarde immédiate dans song_preferences
=> rerendu des accords joués
=> aucun Demucs
=> aucun Whisper
=> aucune analyse harmonique
```

À la prochaine ouverture du morceau, le capo est restauré automatiquement.

### Paramètres avancés

Les changements dans le formulaire ne lancent rien tant que l'utilisateur n'a pas cliqué :

```text
Appliquer les paramètres
```

Lors de cette validation :

```text
=> snapshot complet des réglages persisté pour la chanson
=> logique normale de variante d'analyse
=> nouvelle analyse uniquement si nécessaire / explicitement demandée
```

Les paramètres structurels possèdent maintenant des clés Streamlit stables afin d'être restaurés eux aussi.

### Contrat d'ouverture protégé maintenu

```text
ouvrir chanson déjà analysée
=> charger analyse persistée
=> restaurer paramètres
=> restaurer capo
=> aucun recalcul implicite
```

### Validation demandée

Tester successivement sur La Bohème puis Susanna :

```text
1. ouvrir La Bohème
2. changer capo
3. modifier plusieurs paramètres avancés
4. cliquer Appliquer les paramètres
5. revenir au Répertoire
6. ouvrir Susanna
7. vérifier ses propres paramètres / capo
8. rouvrir La Bohème
9. vérifier restauration exacte du capo et des paramètres
10. vérifier qu'aucun Demucs / Whisper n'est lancé à l'ouverture
```

Étape suivante après validation V37 :

```text
parolier monospace
+
notation Am--- conservée
+
alignement paroles / syllabes sur timestamps accords
```

## UX V39 — Vues de travail et lecture

### Objectif

Chordstation ne doit plus présenter toute la chanson sur une seule longue page verticale.

La page principale `Chanson` doit devenir une interface de **partition lisible, éditable et jouable**, pas seulement une interface de correction.

Le morceau courant doit proposer trois vues distinctes :

```text
Grille
Paroles + accords
Blocs
```

Une seule vue principale est affichée à la fois.

### Navigation attendue

Dans `Chanson`, prévoir une navigation simple et stable :

```text
[ Grille ] [ Paroles + accords ] [ Blocs ]
```

Le changement de vue :

- ne relance aucune analyse ;
- ne relance ni Demucs ni Whisper ;
- ne modifie aucun paramètre musical ;
- conserve le morceau courant ;
- conserve le capo ;
- conserve le découpage ;
- conserve les corrections de grille ;
- conserve les corrections de paroles ;
- doit être immédiat.

La vue choisie peut être mémorisée en session pour éviter de revenir systématiquement à une vue par défaut lors d'un rerun.

---

### Vue `Grille`

Cette vue est destinée à la lecture harmonique et à l'édition de la grille.

Elle doit contenir prioritairement :

```text
titre / artiste
lecteur audio
informations musicales utiles
grille par blocs
édition des mesures
```

Contrat maintenu :

```text
1 cellule = 1 mesure
notation Chordstation conservée
Am---
Am-Em-
D.C-
G---^
```

Le découpage structurel doit rester visible comme séparation logique des blocs, sans obliger à afficher l'éditeur des blocs dans cette vue.

---

### Vue `Paroles + accords`

Cette vue devient une vraie **partition paroles + accords**, utilisable pour lire et jouer le morceau.

Elle doit contenir prioritairement :

```text
titre / artiste
lecteur audio
noms des blocs
accords
paroles
```

Le résultat actuel est jugé suffisamment prometteur pour poursuivre cette direction.

Contrat visuel :

- police monospace ;
- accords positionnés selon leur timeline ;
- paroles alignées sous les accords ;
- notation complète Chordstation conservée ;
- retours à la ligne par vers ;
- corrections de paroles persistantes ;
- accords inchangés lors d'une correction textuelle ;
- affichage lisible sans page gigantesque.

Cette vue ne doit pas être présentée comme un simple panneau d'édition : elle doit être directement exploitable comme feuille de musique.

---

### Vue `Blocs`

Cette vue regroupe toute l'édition structurelle.

Elle doit contenir :

```text
Nom
Début
Fin
Nb mesures
```

Exemple :

```text
Nom          Début   Fin   Nb mesures
Intro           1     10       10
Couplet 1      11     28       18
Refrain 1      29     45       17
Couplet 2      46     63       18
...
```

Actions :

```text
💾 Enregistrer le découpage
✂ Ajouter une séparation
↩ Réinitialiser depuis l’analyse
```

Règles maintenues :

- début calculé automatiquement ;
- nombre de mesures calculé automatiquement ;
- modification d'une fin => décalage automatique des blocs suivants ;
- aucun trou ;
- aucun chevauchement ;
- dernier bloc termine à la dernière mesure ;
- reset structurel sans relancer Demucs / Whisper / analyse harmonique.

L'édition des noms de blocs doit également rester dans cette vue.

---

### Séparation lecture / édition

Les contrôles d'édition doivent être disponibles sans empêcher une lecture propre de la partition.

Direction UX :

```text
lecture d'abord
édition accessible mais secondaire
```

Autrement dit :

- la partition doit rester lisible sans être noyée dans les formulaires ;
- les éditeurs peuvent être placés dans des expanders, panneaux ou sections secondaires ;
- les boutons techniques ne doivent pas dominer l'écran ;
- les informations de diagnostic ne doivent pas encombrer les vues de lecture.

---

### Lecteur audio

Le lecteur fait partie de la partition.

Il doit rester accessible dans les vues utiles, en particulier :

```text
Grille
Paroles + accords
```

À terme, une seule timeline synchronisée doit piloter :

```text
audio
mesure courante
accord courant
vers / parole courante
bloc courant
```

Le futur player n'est donc pas un outil séparé : il prolonge directement les vues de partition.

---

### Positionnement produit

Chordstation doit être pensé comme :

```text
analyse audio
+
édition musicale
+
partition
+
lecture / jeu synchronisé
```

et non comme :

```text
simple outil de correction des résultats d'analyse
```

La page web doit donc pouvoir être utilisée par un musicien qui ouvre une chanson pour :

```text
lire
jouer
suivre
corriger si nécessaire
imprimer plus tard
```

---

### Ordre de travail suivant

Priorité UX :

```text
1. introduire les trois vues Grille / Paroles + accords / Blocs
2. alléger chaque vue pour éviter les pages trop longues
3. stabiliser le parolier comme partition lisible
4. préparer le player synchronisé dans Grille et Paroles + accords
5. ajouter l'impression
```

Le contrat fondamental reste inchangé :

> Interpréter le signal audio, ne pas inventer une progression.

### Mode `Vue` / `Édition` par écran

Chaque vue principale doit avoir son propre bouton de mode :

```text
Grille
[ 👁 Vue ] [ ✏️ Édition ]

Paroles + accords
[ 👁 Vue ] [ ✏️ Édition ]

Blocs
[ 👁 Vue ] [ ✏️ Édition ]
```

Le mode est local à la vue courante.

#### Mode `Vue`

But : lecture propre, sans contrôles d'édition visibles.

Afficher uniquement ce qui est utile pour lire / jouer :

```text
titre
artiste
lecteur audio
capo / tonalité / signature si utile
contenu musical de la vue
```

Masquer :

```text
data_editor
text_area
boutons Enregistrer
boutons Reset
boutons Ajouter séparation
diagnostics techniques
contrôles de correction
```

#### Mode `Édition`

But : corriger le contenu de la vue courante.

Afficher les contrôles spécifiques :

```text
Grille
→ édition des mesures / accords

Paroles + accords
→ correction des paroles / retours de ligne

Blocs
→ nom / fin / nb mesures
→ ajouter séparation
→ reset depuis analyse
```

#### Règles de navigation

Changer :

```text
Vue <-> Édition
```

ne doit jamais :

```text
relancer Demucs
relancer Whisper
relancer l'analyse harmonique
changer de chanson
modifier le capo
modifier le découpage
```

Le changement doit être immédiat.

Le dernier mode peut être mémorisé en session pour chaque vue, par exemple :

```text
Grille -> Vue
Paroles + accords -> Vue
Blocs -> Édition
```

Objectif produit :

```text
ouvrir une chanson
→ lire / jouer immédiatement en mode Vue
→ passer en Édition seulement si nécessaire
```

Le mode par défaut recommandé pour `Grille` et `Paroles + accords` est `Vue`.

Pour `Blocs`, le mode par défaut peut rester `Vue`, avec passage explicite en `Édition`.

## Répertoire — gestion des versions d'une chanson

Le `Répertoire` doit permettre de gérer les différentes versions persistées d'une même chanson.

### Objectif

Depuis la ligne d'un morceau, l'utilisateur doit pouvoir :

```text
choisir une version
voir une version
modifier une version
supprimer une version
```

Exemple d'ergonomie :

```text
La Bohème — Charles Aznavour
Version : [ V3 ▾ ]

[ Ouvrir ] [ Voir ] [ Modifier ] [ Supprimer ]
```

### Définition d'une version

Une version correspond à un état musical persistant du morceau.

Elle doit au minimum référencer :

```text
audio_hash
analysis_version / analysis_key
paramètres d'analyse
date de création
capo associé au morceau
structure / blocs persistés
corrections de grille
corrections de paroles
```

Le morceau audio reste unique ; les versions représentent différents états d'analyse / édition du même morceau.

### Choisir une version

Le Répertoire doit afficher un sélecteur de version pour chaque chanson qui possède plusieurs versions.

Le choix d'une version :

```text
=> charge cette version
=> restaure ses paramètres
=> restaure son état éditorial
=> n'effectue aucune nouvelle analyse
```

La version choisie devient la version courante du morceau.

### Voir une version

`Voir` ouvre la chanson en mode lecture :

```text
mode Vue
+
version sélectionnée
```

Aucun contrôle d'édition obligatoire à l'ouverture.

### Modifier une version

`Modifier` ouvre la chanson sur la version sélectionnée en mode :

```text
Édition
```

Les changements éditoriaux doivent être sauvegardés dans cette version ou dans une nouvelle version selon l'action choisie par l'utilisateur.

À terme, prévoir explicitement :

```text
Enregistrer
Enregistrer comme nouvelle version
```

afin d'éviter d'écraser involontairement une version de référence.

### Supprimer une version

`Supprimer` doit demander une confirmation.

La suppression :

```text
supprime uniquement la version sélectionnée
ne supprime jamais le fichier audio
ne supprime jamais la chanson si d'autres versions existent
```

Si la version supprimée est la version courante, Chordstation doit sélectionner automatiquement une autre version persistée, de préférence la plus récente.

Si une chanson ne possède plus aucune version, le morceau reste dans le Répertoire tant que son audio / entrée `songs` existe.

### Version courante

Chaque chanson doit pouvoir mémoriser une `version courante`.

Le Répertoire doit indiquer clairement :

```text
Version courante
Version la plus récente
Date / heure
```

sans transformer la ligne en panneau technique surchargé.

### Ergonomie recommandée

Le Répertoire doit rester compact.

Direction :

```text
Titre | Artiste | Version | Actions
```

avec par exemple :

```text
La Bohème | Charles Aznavour | V3 ▾ | Ouvrir · Voir · Modifier · Supprimer
Susanna   | The Art Company  | V1 ▾ | Ouvrir · Voir · Modifier · Supprimer
```

Les détails techniques de version peuvent être placés dans un expander ou une vue secondaire.

### Règles

Toute action de gestion de version depuis le Répertoire doit respecter :

```text
aucun Demucs implicite
aucun Whisper implicite
aucune analyse harmonique implicite
```

Une analyse ne doit être créée que lors d'une action explicite telle que :

```text
Appliquer les paramètres
Créer une nouvelle version
```

### Intégration avec les vues

Après ouverture d'une version, les trois vues restent disponibles :

```text
Grille
Paroles + accords
Blocs
```

et chacune garde son mode :

```text
Vue
Édition
```

La version sélectionnée doit rester active lors des changements de vue.

## V39c — Mode Vue propre + champ Éditeur

### Mode Vue

Le mode `Vue` est destiné à la lecture / au jeu.

Il ne doit afficher aucun contrôle d'édition.

Masqués en mode Vue :

```text
bouton Enregistrer des métadonnées
éditeur de grille
éditeur de paroles
éditeur de blocs
boutons reset
boutons restauration / retour vers une version d'analyse
panneau Versions d'analyse
bouton Sauver l'analyse courante comme nouvelle version
```

Le mode Vue conserve uniquement les informations utiles à la partition :

```text
titre
artiste
éditeur si renseigné
lecteur audio
capo / tonalité / signature
contenu musical de la vue
```

### Mode Édition

Le mode `Édition` expose les outils nécessaires à la vue courante ainsi que les métadonnées éditables.

Le panneau :

```text
Versions d'analyse
```

est donc disponible uniquement en mode Édition.

Il représente une fonction de gestion / restauration de versions et ne doit pas encombrer la partition en lecture.

### Nouveau champ `Éditeur`

Ajout d'une métadonnée persistante :

```text
Éditeur
```

But :

```text
nom de l'auteur des modifications de la partition
```

Exemples possibles :

```text
Steve
Philippe S.
Log & Play
```

Cette information est distincte de :

```text
Auteur / Interprète
```

Le champ est stocké dans la table locale :

```text
songs.editor
```

Migration automatique :

```text
ALTER TABLE songs ADD COLUMN editor TEXT NOT NULL DEFAULT ''
```

pour les bases existantes.

### Affichage

En mode Édition :

```text
Titre
Auteur / Interprète
Éditeur
[ Enregistrer ]
```

En mode Vue :

```text
Titre
Auteur / Interprète
Éditeur : <nom>
```

sans bouton `Enregistrer`.

### Persistance

Modifier l'Éditeur :

```text
=> sauvegarde dans songs
=> aucune analyse
=> aucun Demucs
=> aucun Whisper
```

Le champ revient automatiquement à l'ouverture du morceau.

### Contrat UX confirmé

Chaque vue conserve :

```text
Grille
Paroles + accords
Blocs
```

et chaque vue fonctionne selon :

```text
👁 Vue
✏️ Édition
```

Principe global :

```text
Vue = partition propre et jouable
Édition = outils de modification
```

## V39d — Versions de partition complètes

### Défaut corrigé

Le Répertoire affichait seulement les versions d'analyse.

Conséquences constatées :

```text
l'Éditeur n'était pas visible dans le Répertoire
sauvegarder avec un nom d'Éditeur ne créait pas de nouvelle version
les versions ne représentaient pas réellement l'état édité de la partition
```

V39d transforme les versions existantes en **snapshots de partition**.

### Contenu d'une version

Une version stocke désormais :

```text
analyse
paramètres d'analyse
titre
artiste
éditeur
capo
découpage des blocs
corrections de grille
corrections de paroles
date de création
```

La table historique `analysis_versions` est conservée pour compatibilité, mais enrichie automatiquement avec les colonnes nécessaires.

### Répertoire

Chaque morceau affiche maintenant :

```text
Titre
Artiste
Éditeur
Version
Actions
```

Exemple :

```text
La Bohème | Charles Aznavour | Éditeur : Steve | V2 | Voir | Modifier | Supprimer
```

L'Éditeur affiché correspond à la version sélectionnée.

### Création d'une nouvelle version

Toute sauvegarde éditoriale crée maintenant une nouvelle version :

```text
Enregistrer les métadonnées
Enregistrer le découpage
Enregistrer un bloc de grille
Enregistrer les paroles
```

Exemple :

```text
V1 = analyse initiale
V2 = modification par Steve
V3 = nouvelle correction de grille
```

Aucune de ces sauvegardes ne relance automatiquement Demucs ou Whisper.

### Ouvrir une version

`Voir` ou `Modifier` restaure le snapshot sélectionné comme copie de travail :

```text
titre
artiste
éditeur
capo
blocs
accords corrigés
paroles corrigées
analyse liée à la version
```

La version persistée reste immuable.

Une modification suivie d'un Enregistrer crée une nouvelle version au lieu d'écraser la version source.

### Supprimer une version

La suppression retire uniquement le snapshot sélectionné.

Elle ne supprime pas :

```text
le fichier audio
la chanson
les autres versions
```

### Migration SQLite

Ajout automatique aux bases existantes des colonnes :

```text
title
artist
editor
capo
structure_json
measure_edits_json
lyric_edits_json
```

dans `analysis_versions`.

Aucune manipulation manuelle de la base n'est requise.

### Contrat produit

Une version correspond désormais à :

```text
un état éditorial complet de la partition
```

et non plus seulement à :

```text
une variante technique d'analyse
```

C'est ce modèle qui doit servir pour la suite : consultation, édition, suppression, impression et player synchronisé.

## V39e — Grille type Excel par bloc

### Référence visuelle

Le classeur fourni `La fille du Père Noël - Jacques Dutronc.xlsx` sert de référence ergonomique pour la grille.

Principes repris :

```text
nom du bloc visible à gauche
quadrillage net type Excel
1 case = 1 mesure
aucun libellé "Mesure 1", "Mesure 2", etc.
notation d'accord directement dans la case
police plus grande et plus lisible
```

Exemple de structure visuelle :

```text
Intro       | E--A | E--A |      |      |

Couplet 1   | E--- | D-E- |      |      |
            | A-   | E--A | E--A |      |
            | E--- | D-E- |      |      |
```

### Mode Vue — Grille

Le mode `Vue` devient une vraie partition de grille.

Règles :

- le nom du bloc apparaît dans une colonne dédiée à gauche ;
- le quadrillage apparaît à droite ;
- 4 mesures par ligne par défaut ;
- aucune numérotation de mesure visible ;
- cellules bordées de façon nette ;
- notation monospace ;
- taille de police augmentée ;
- les cases vides nécessaires pour compléter une ligne restent visuellement neutres.

Le contenu musical reste inchangé :

```text
Am---
Am-Em-
D.C-
G---^
```

### Mode Édition — Grille

Même principe de lecture :

```text
1 input = 1 mesure
```

Les labels `Mesure N` sont masqués visuellement.

Les champs d'accords utilisent une police monospace plus grande.

La numérotation interne des mesures reste conservée dans le code et la persistance, mais n'est plus affichée au musicien.

### Objectif

La grille doit être utilisable directement comme partition à l'écran, avec un rendu compact, structuré et lisible, tout en restant éditable sans changer de modèle de données.

## V39h — Parolier lisible + entête guitariste

### Parolier

Le parolier suit la même logique de lisibilité que la grille :

```text
police nettement plus grande
police monospace
accords très visibles
paroles très lisibles
espacement vertical compact mais confortable
noms de blocs renforcés
```

Réglages visuels V39h :

```text
accords : ~1.28rem
paroles : ~1.42rem
nom de bloc : ~1.24rem
```

Le contrat d'alignement reste inchangé :

```text
accords = référence temporelle
paroles = alignées dessous
notation Chordstation conservée
```

### Entête guitariste

Le capodastre fait désormais partie des informations principales du morceau, au même niveau que :

```text
Tempo
Signature
Tonalité réelle
Capo
Nb mesures
```

Exemple :

```text
Tempo        Signature       Tonalité      Capo      Mesures
129.2 BPM    3/4             Cm            3         175
```

Si aucun capo :

```text
Capo : —
```

Le capo reste strictement un paramètre de représentation et ne relance aucune analyse.

### Strumming

Ajout de deux champs éditables et persistants :

```text
Strumming principal
Strumming alternatif
```

Exemples :

```text
Strumming principal : ↓ ↓↑ ↑↓↑
Strumming alternatif : ↓↑ ↓↑ ↓↑ ↓↑
```

Le second champ peut servir à documenter un pattern différent, par exemple pour :

```text
refrain
pont
break
variation
```

Ces champs sont enregistrés dans `songs` :

```text
strumming_primary
strumming_secondary
```

et restaurés à l'ouverture du morceau.

Ils sont aussi inclus dans les snapshots de versions de partition.

### Mode Vue

Quand un strumming est renseigné, il apparaît dans l'entête de la chanson sous forme compacte :

```text
🎸 Strumming : ↓ ↓↑ ↑↓↑ · Alternatif : ↓↑ ↓↑ ↓↑ ↓↑
```

Aucun contrôle d'édition n'apparaît en mode Vue.

### Mode Édition

Les deux champs de strumming sont éditables dans les métadonnées du morceau avec :

```text
Titre
Auteur / Interprète
Éditeur
Strumming principal
Strumming alternatif
```

Enregistrer ces champs :

```text
=> crée une nouvelle version de partition
=> ne relance pas Demucs
=> ne relance pas Whisper
=> ne relance pas l'analyse harmonique
```

### Positionnement produit

La priorité reste :

```text
partition lisible pour un guitariste
avant interface technique
```

La grille et le parolier doivent donc être exploitables directement pour jouer le morceau à l'écran.

## V40 — Surface compacte / modes Vue · Éditer · Jouer

### Objectif UX

Réduire fortement la hauteur et la surface consommée par les éléments non musicaux.

La page `Chanson` doit privilégier la partition.

### Entête unique compact

Le titre et l'auteur/interprète sont sur la même ligne :

```text
La Bohème — Charles Aznavour          · Version 3 · Version éditée
```

La note de version est discrète et correspond à la version réellement chargée.

Statuts proposés :

```text
Analyse auto
Analyse auto + corrections
Version éditée
```

Le statut est informatif uniquement.

### Éditeur

Le nom de l'Éditeur n'est plus dans l'entête central.

Il est déplacé dans la marge / sidebar :

```text
Éditeur : Steve
```

afin de gagner de la place verticale.

### Informations principales

Sous le titre :

```text
Tempo | Signature | Tonalité réelle | Capo | Mesures
```

Le strumming reste visible de façon compacte.

### Suppression du player générique

Le player audio Streamlit affiché en haut de la chanson est supprimé.

Il sera remplacé par deux expériences synchronisées spécifiques :

```text
Grille -> player synchronisé grille / mesures / accords
Paroles + accords -> player synchronisé paroles / accords
```

La présentation exacte de ces players sera définie ultérieurement.

### Modes de la vue

Pour `Grille` et `Paroles + accords` :

```text
👁 Vue
✏️ Éditer
▶ Jouer
```

Pour `Blocs` :

```text
👁 Vue
✏️ Éditer
```

`Jouer` n'est donc pas proposé pour la vue structurelle.

Le mode `Jouer` V40 réserve seulement l'emplacement fonctionnel ; aucun nouveau player visuel n'est encore imposé.

### Surface de lecture

En mode Vue ou Jouer, les messages techniques de chargement d'analyse sont masqués.

Ils restent disponibles en mode Édition lorsque nécessaire.

Principe :

```text
lecture / jeu = contenu musical prioritaire
édition = contrôles techniques disponibles
```

### Impression future

Après stabilisation de l'ergonomie et des players :

```text
Imprimer Grille
Imprimer Paroles + accords
```

Les deux formats doivent exploiter le même état de partition et la même version active.

## TODO — Prochaine session

### 1. Impression

Objectif : produire une vraie sortie de partition imprimable à partir de la version active du morceau.

Prévoir au minimum :

```text
Imprimer Grille
Imprimer Paroles + accords
```

Contraintes :

```text
utiliser la version active
respecter le capo courant
respecter les blocs édités
respecter les accords corrigés
respecter les paroles corrigées
afficher titre — auteur/interprète
afficher version
afficher éditeur
afficher tempo
afficher signature
afficher tonalité réelle
afficher capo
afficher strumming
```

La vue imprimée ne doit contenir aucun contrôle Streamlit inutile :

```text
pas de sidebar
pas de boutons
pas de diagnostics
pas de contrôles d'édition
pas de messages techniques
```

#### Impression Grille

But :

```text
quadrillage compact type Excel
1 case = 1 mesure
nom de bloc visible
notation Chordstation conservée
police suffisamment grande
```

Le modèle visuel reste inspiré du classeur fourni :

```text
La fille du Père Noël - Jacques Dutronc.xlsx
```

#### Impression Paroles + accords

But :

```text
police monospace
accords très lisibles
paroles très lisibles
alignement horizontal conservé
noms de blocs visibles
retours à la ligne édités respectés
```

---

### 2. Player synchronisé

Le player générique Streamlit a été supprimé.

À implémenter séparément pour :

```text
Grille
Paroles + accords
```

Le bouton existe déjà dans l'UX :

```text
▶ Jouer
```

#### Player Grille

Synchronisation cible :

```text
audio
mesure courante
accord courant
bloc courant
```

Comportement attendu :

```text
la cellule de mesure courante est mise en évidence
le changement suit le temps audio
le bloc courant reste identifiable
```

#### Player Paroles + accords

Synchronisation cible :

```text
audio
accord courant
vers courant
mot / syllabe courant si possible
bloc courant
```

Le moteur d'alignement existant doit servir de base :

```text
timestamps accords
+
timestamps Whisper
+
corrections de paroles persistées
```

La présentation exacte du player sera définie avec l'utilisateur avant implémentation détaillée.

---

### 3. UX / Surface d'affichage

Continuer à optimiser la surface utile.

Contrat actuel :

```text
Titre — Auteur / Interprète        · Version N · statut
Tempo | Signature | Tonalité | Capo | Mesures
Strumming
```

Éditeur :

```text
dans la sidebar / marge
```

Modes :

```text
Grille
→ Vue / Éditer / Jouer

Paroles + accords
→ Vue / Éditer / Jouer

Blocs
→ Vue / Éditer
```

Principe :

```text
Vue = lecture
Éditer = modification
Jouer = lecture synchronisée
```

Éviter toute duplication d'entête ou de contrôles.

---

### 4. Gestion des versions

À conserver strictement :

```text
une version = snapshot complet de partition
```

Contenu :

```text
analyse
paramètres
titre
artiste
éditeur
capo
strumming
blocs
corrections de grille
corrections de paroles
```

Depuis le Répertoire :

```text
choisir version
voir
modifier
supprimer
```

Aucune ouverture de version ne doit relancer :

```text
Demucs
Whisper
analyse harmonique
```

---

### 5. Persistance

À surveiller pendant les prochaines évolutions :

```text
capo
paramètres avancés
éditeur
strumming
blocs
grille
paroles
version active
```

L'ouverture d'un morceau doit toujours restaurer son état sans réanalyse implicite.

---

### 6. Contrat musical inchangé

```text
Interpréter le signal audio, ne pas inventer une progression.
```

La grille, le parolier, l'impression et le player doivent tous utiliser les mêmes données musicales persistées.

---

### 7. Base de reprise

Base Python courante :

```text
chordstation_v40_compact_surface_play_modes.py
```

Handoff courant :

```text
ChordStation_v40_README_HANDOFF.md
```

Prochaine étape recommandée :

```text
1. définir précisément l'impression Grille
2. définir précisément l'impression Paroles + accords
3. implémenter impression
4. définir UX player Grille
5. définir UX player Paroles + accords
6. implémenter synchronisation
```

## V41 — Impression Grille / Paroles + accords

### Implémenté

Ajout du mode :

```text
🖨 Imprimer
```

pour :

```text
Grille
Paroles + accords
```

Le mode `Blocs` reste sans impression dédiée pour l'instant.

### Grille

Format d'impression :

```text
A4 paysage
```

Contenu imprimé :

```text
Titre — Auteur / Interprète
Version
Statut Analyse auto / Analyse auto + corrections / Version éditée
Éditeur
Tempo
Signature
Tonalité réelle
Capo
Mesures
Strumming principal
Strumming alternatif
Blocs
Grille 1 case = 1 mesure
```

La grille utilise :

```text
4 mesures par ligne
notation Chordstation
noms de blocs
corrections persistées
capo courant
```

### Paroles + accords

Format d'impression :

```text
A4 portrait
```

Le rendu conserve :

```text
police monospace
accords au-dessus
paroles dessous
alignement horizontal
blocs
retours à la ligne corrigés
capo courant
version active
```

### Impression navigateur

Le bouton :

```text
🖨 Ouvrir l’impression
```

ouvre la boîte d'impression du navigateur.

Le CSS `@media print` masque tout sauf la partition dédiée :

```text
sidebar
navigation
boutons
diagnostics
widgets
contrôles d'édition
```

### TODO suivant — Player

Le player générique reste supprimé.

Les modes existent déjà :

```text
Grille -> ▶ Jouer
Paroles + accords -> ▶ Jouer
```

Prochaine étape :

```text
définir avec l'utilisateur la présentation du player Grille
définir avec l'utilisateur la présentation du player Paroles + accords
implémenter une timeline audio unique
synchroniser mesure / accord / bloc
synchroniser paroles / mots si souhaité
```

Ne pas imposer encore l'UX du player avant validation visuelle par l'utilisateur.

## V42 — Impression A4 portrait + icône compacte

### Corrections après test PDF

Les PDF de test ont montré deux points à corriger :

```text
1. la grille ne doit jamais passer en paysage
2. le mode Imprimer séparé consomme inutilement de la surface
```

Décision V42 :

```text
toutes les impressions = A4 portrait
```

### UX

Suppression du mode :

```text
🖨 Imprimer
```

Dans les vues :

```text
Grille
Paroles + accords
```

l'impression est maintenant déclenchée par une simple icône :

```text
🖨️
```

visible uniquement lorsque le mode courant est :

```text
👁 Vue
```

Les modes restent donc :

```text
👁 Vue
✏️ Éditer
▶ Jouer
```

### Grille papier

Toujours :

```text
4 mesures par ligne
1 case = 1 mesure
nom du bloc à gauche
notation Chordstation conservée
```

mais le gabarit est recalculé pour tenir sur A4 portrait :

```text
marge bloc réduite
cellules en largeur proportionnelle
police papier légèrement réduite
```

### Correction page blanche / pagination

L'ancien CSS utilisait `visibility:hidden`, ce qui pouvait laisser la mise en page Streamlit occuper de la place lors de la pagination navigateur.

V42 utilise une feuille papier cachée à l'écran :

```text
.print-sheet { display:none; }
```

puis rend uniquement cette feuille pendant l'impression.

Objectif :

```text
aucune page blanche initiale
aucune réservation de place par l'interface Streamlit
pagination plus prévisible
```

### Paroles + accords

A4 portrait inchangé dans le principe.

La feuille papier reste distincte de la vue écran afin que :

```text
la taille écran reste grande et lisible
la taille papier puisse être optimisée indépendamment
```

### TODO

```text
1. valider le nouveau PDF Grille
2. valider le nouveau PDF Paroles + accords
3. régler marges / tailles si nécessaire
4. attaquer le player synchronisé
```

## V47 — Validation explicite + indicateur en marge

### Objectif

Éviter toute ambiguïté entre :

```text
modification saisie
modification validée
modification versionnée
```

Le vocabulaire `Enregistrer` est abandonné pour les éditions musicales qui créent une nouvelle version.

### Libellés de validation

Paroles :

```text
✅ Valider ces paroles
```

Grille :

```text
✅ Valider <Nom du bloc>
```

Exemple :

```text
✅ Valider Couplet 1
```

Structure :

```text
✅ Valider ce découpage
```

Chaque validation :

```text
persiste la modification
crée une nouvelle version de partition
met à jour la version active
ne relance ni Demucs ni Whisper
ne relance pas l'analyse harmonique
```

### Indicateur en marge gauche

Dès qu'au moins une modification validée est présente pour le morceau, la sidebar affiche :

```text
✓ Modifications validées
```

avec un résumé :

```text
Grille : N
Paroles : N
Blocs : N
```

Exemple :

```text
✓ Modifications validées
Grille : 3 · Paroles : 2 · Blocs : 1
```

S'il n'existe aucune correction validée :

```text
○ Aucune correction validée
```

### Définition d'une modification validée

Sont comptées uniquement les modifications déjà persistées :

```text
measure_edits
lyric_block_edits
structure_blocks modifiés
```

Pour la structure, sont considérés comme modifiés :

```text
nom personnalisé
frontière déplacée
bloc ajouté manuellement
```

Les valeurs encore présentes uniquement dans les widgets d'édition ne sont pas considérées comme validées.

### Contrat de version

Une validation explicite crée une nouvelle version complète :

```text
analyse
paramètres
titre
artiste
éditeur
capo
strumming
structure
corrections grille
corrections paroles
```

Le message utilisateur doit rester explicite :

```text
Paroles validées — nouvelle version Vn créée.
Découpage validé — nouvelle version Vn créée.
<Bloc> validé — nouvelle version Vn créée.
```

---

## Impression — état retenu

La base d'impression à conserver reste celle de V43 :

```text
fenêtre HTML dédiée
A4 portrait
marges 9 mm
pas de masquage du DOM Streamlit
icône 🖨️ uniquement en mode Vue
```

V44 a été rejetée car les marges latérales étaient trop rognées.

V45 conserve les marges V43 et ajoute uniquement des règles de pagination plus prudentes :

```text
éviter les coupures internes de blocs de grille
éviter un titre de bloc isolé
ne jamais couper une ligne accords/paroles
garder autant que possible titre + première ligne
```

Ne pas réduire davantage les marges sans validation visuelle.

---

## Parolier — contrat d'édition

Le parolier doit permettre :

```text
1 vers saisi = 1 ligne voulue
accords fixes par rapport à la timeline
paroles ajustées sous les accords
retours à la ligne manuels conservés
```

Le bouton de validation est désormais :

```text
✅ Valider ces paroles
```

afin d'éviter de croire qu'une saisie non validée est déjà sauvegardée.

---

## TODO prioritaire

### 1. Détection de modifications non validées

À implémenter :

```text
dirty state par vue
```

au minimum pour :

```text
Grille
Paroles + accords
Blocs
Métadonnées / strumming
```

Dès qu'un widget diffère du dernier état validé :

```text
afficher un indicateur "Modifications non validées"
```

et avant de :

```text
changer de vue
changer de morceau
changer de version
quitter le mode Édition
```

proposer explicitement :

```text
Valider
Ignorer
Annuler
```

Objectif :

```text
aucune modification utilisateur ne doit pouvoir être perdue silencieusement
```

### 2. Player synchronisé

Le player générique reste supprimé.

Modes existants :

```text
Grille -> ▶ Jouer
Paroles + accords -> ▶ Jouer
```

À définir avec l'utilisateur avant implémentation finale.

Synchronisation cible :

```text
audio
mesure courante
accord courant
bloc courant
parole / vers courant
mot courant si pertinent
```

### 3. Impression

Conserver :

```text
A4 portrait
V43 comme référence visuelle
marges 9 mm
icône 🖨️ en Vue
```

Continuer seulement sur :

```text
pagination
césures
répartition sur 2 pages max si possible
```

sans dégrader les marges validées.

---

## Base de reprise

Script courant :

```text
chordstation_v47_validated_indicator.py
```

README/HANDOFF courant :

```text
ChordStation_v47_README_HANDOFF.md
```

## V48 — Éditeur de blocs ergonomique

### Objectif

Le découpage du morceau est séquentiel.

L'éditeur doit donc fonctionner comme une chaîne continue :

```text
bloc 1
→ bloc 2
→ bloc 3
→ ...
```

et non comme une collection indépendante de bornes.

### Édition live

Le tableau conserve :

```text
Nom
Début
Fin
Nb mesures
＋
🗑
```

Règles :

```text
Début = calculé automatiquement
Fin = éditable
Nb mesures = calculé automatiquement
Nom = éditable
```

Quand `Fin` est modifiée puis validée par :

```text
Entrée
ou
clic dans une autre cellule
```

le tableau est recalculé immédiatement.

Le bouton `Valider ce découpage` ne sert plus à faire les calculs.

Il sert uniquement à :

```text
persister le brouillon visible
créer une nouvelle version
```

### Recalcul séquentiel

Lorsqu'une frontière change :

```text
Fin du bloc N
→ Début du bloc N+1 = Fin N + 1
```

Les blocs suivants sont décalés en conservant leur durée précédente autant que possible.

Garanties :

```text
premier Début = 1
dernier Fin = dernière mesure du morceau
aucun trou
aucun chevauchement
au moins 1 mesure par bloc
```

### Actions par ligne

Deux colonnes d'action sont ajoutées :

```text
＋
🗑
```

#### `＋`

Insère un nouveau bloc juste après la ligne.

Comportement initial :

```text
le bloc courant cède sa dernière mesure
le nouveau bloc reçoit cette mesure
Nom = Nouveau bloc
```

L'utilisateur ajuste ensuite la frontière en modifiant `Fin`.

#### `🗑`

Supprime le bloc courant.

La séquence est refermée automatiquement.

Règle :

```text
si premier bloc supprimé
→ le suivant absorbe sa plage

sinon
→ le bloc précédent absorbe sa plage
```

Le dernier bloc restant ne peut pas être supprimé.

### Ajouter un bloc en fin

Bouton :

```text
＋ Ajouter un bloc en fin
```

Le nouveau bloc final reçoit initialement une mesure.

L'utilisateur peut ensuite agrandir ce bloc en réduisant la `Fin` du bloc précédent.

### Brouillon non validé

Toute modification live reste uniquement en mémoire tant que l'utilisateur n'a pas cliqué :

```text
✅ Valider ce découpage
```

Un indicateur est affiché :

```text
● Modifications non validées
```

dans :

```text
éditeur de blocs
sidebar / marge gauche
```

Le tableau visible représente donc exactement le brouillon qui sera validé.

### Couverture du morceau

Le tableau affiche un contrôle explicite :

```text
✓ 175 / 175 mesures affectées — séquence continue.
```

En cas d'incohérence :

```text
⚠ N / 175 mesures affectées.
```

L'objectif normal reste toujours :

```text
100 % des mesures affectées
0 trou
0 chevauchement
```

### Validation

Bouton :

```text
✅ Valider ce découpage
```

désactivé si le brouillon est identique à la dernière version persistée.

Lors de la validation :

```text
structure_blocks est mis à jour
une nouvelle version complète est créée
active_analysis_version_no est mis à jour
```

Aucune nouvelle analyse audio n'est exécutée.

### Annulation

Bouton :

```text
↩ Annuler les changements
```

revient au dernier découpage validé sans toucher à l'analyse.

### Réinitialisation analyse

L'action reste disponible dans un contrôle secondaire :

```text
⚙ Réinitialiser depuis l’analyse
```

Cette action :

```text
supprime uniquement la structure manuelle
conserve Demucs
conserve Whisper
conserve corrections de grille
```

### UX retenue

Le flux devient :

```text
modifier
↓
recalcul immédiat
↓
voir exactement le résultat
↓
indicateur non validé
↓
Valider ce découpage
↓
nouvelle version
```

Principe :

```text
aucun calcul structurel important ne doit attendre le bouton Valider
```

---

## TODO après V48

### 1. Alerte globale modifications non validées

Étendre le même modèle de brouillon à :

```text
Paroles + accords
Grille
Métadonnées / strumming
```

Avant :

```text
changement de morceau
changement de version
sortie du mode Édition
```

proposer :

```text
Valider
Ignorer
Annuler
```

### 2. Player synchronisé

Toujours prévu après stabilisation complète des éditions.

### 3. Impression

Conserver la base visuelle validée :

```text
V43
A4 portrait
marges 9 mm
fenêtre HTML dédiée
```

---

## Base de reprise

Script :

```text
chordstation_v48_block_editor.py
```

Handoff :

```text
ChordStation_v48_README_HANDOFF.md
```

## V49 — Multi-suppression blocs + warnings Streamlit

### Gestion des suppressions

Le comportement V48 avec une action immédiate par case cochée est abandonné.

Problème :

```text
cocher une case
→ rerun immédiat
→ tableau reconstruit
→ sélections perdues
```

V49 passe à une logique de sélection multiple.

Le tableau contient maintenant :

```text
Nom
Début
Fin
Nb mesures
🗑
```

La colonne `🗑` est une sélection uniquement.

On peut cocher plusieurs blocs avant toute action.

Exemple :

```text
Couplet 3     ☑
Refrain 3     ☑
Couplet 4     ☐
```

Puis :

```text
🗑 Supprimer (2)
```

La suppression est alors appliquée en une seule opération.

### Règles de suppression

Après suppression multiple :

```text
aucun trou
aucun chevauchement
ordre séquentiel conservé
dernier bloc termine à la dernière mesure
```

Les blocs survivants absorbent automatiquement les plages supprimées.

Il est interdit de supprimer tous les blocs :

```text
au moins un bloc doit rester
```

### Stabilité du tableau

Les cases cochées ne déclenchent plus d'action immédiate.

Le tableau ne doit donc plus se réinitialiser à chaque clic.

Les changements de :

```text
Nom
Fin
```

continuent à déclencher le recalcul live de :

```text
Début
Nb mesures
```

mais sans changement de clé du tableau pour une simple modification de cellule.

Principe :

```text
sélection = préparer une action
bouton = exécuter l'action
```

### Ajout de bloc

Le bouton reste :

```text
＋ Ajouter un bloc en fin
```

Il crée un nouveau bloc final d'une mesure.

### Validation

Le contrat reste :

```text
✅ Valider ce découpage
```

Le bouton ne calcule pas le tableau.

Il persiste uniquement le brouillon déjà visible et crée une nouvelle version.

---

## Warnings Streamlit corrigés

Warning observé :

```text
The widget with key "setting_analyse_sr" was created with a default value
but also had its value set via the Session State API.
```

Cause :

```text
widget avec index/value explicite
+
même clé déjà restaurée dans st.session_state
```

V49 initialise les valeurs par défaut uniquement si la clé n'existe pas déjà :

```text
if key not in st.session_state:
    st.session_state[key] = default
```

Puis les widgets utilisent leur `key` sans fournir une seconde valeur par défaut explicite.

Réglages concernés :

```text
capo_live
setting_signature_mode
setting_analyse_sr
setting_hop_length
setting_silence_rms
setting_silence_chroma
setting_poids_fondamentale
setting_fermata_enabled
setting_fermata_gap
setting_sections_enabled
setting_section_block_measures
setting_section_similarity
```

Objectif :

```text
0 warning Session State / default value
```

tout en conservant la restauration des préférences par chanson.

---

## TODO

### Brouillons non validés

Étendre la même robustesse à :

```text
Grille
Paroles
Métadonnées
Strumming
```

avec protection avant changement de :

```text
vue
morceau
version
```

### Player

Toujours prévu après stabilisation complète de l'édition.

---

## Base de reprise

Script :

```text
chordstation_v49_block_multiselect_warnings.py
```

Handoff :

```text
ChordStation_v49_README_HANDOFF.md
```

## V50 — Migration vers st.iframe

### Warning Streamlit corrigé

Warning observé :

```text
Please replace `st.components.v1.html` with `st.iframe`.

`st.components.v1.html` will be removed after 2026-06-01.
```

La cause était le bouton d'impression compact, qui utilisait encore :

```python
st.components.v1.html(...)
```

V50 remplace cette API dépréciée par :

```python
st.iframe(...)
```

L'HTML du bouton d'impression reste exécuté dans une iframe dédiée.

### Impression

Le comportement reste inchangé :

```text
icône 🖨️
→ ouverture d'une fenêtre HTML autonome
→ impression A4 portrait
```

La fenêtre d'impression conserve :

```text
marges 9 mm
mise en page V43 validée
grille 4 mesures par ligne
paroles + accords monospace
```

### Nettoyage

L'import :

```python
import streamlit.components.v1 as components
```

est supprimé.

Objectif :

```text
0 warning de dépréciation components.v1.html
```

---

## Base de reprise

Script :

```text
chordstation_v50_streamlit_iframe.py
```

Handoff :

```text
ChordStation_v50_README_HANDOFF.md
```

## V50 — Introduction du templating SCORE modulaire

### Décision d'architecture

La préparation d'une migration future vers PHP/OPUS commence uniquement par la séparation de la représentation.

Le métier, la persistance et l'orchestration Streamlit restent dans `EZScore.py` pour le moment.

```text
EZScore.py
= application / Streamlit / métier / SQLite / analyse audio

EZScoreTemplate.py
= moteur de rendu .score, autonome et sans dépendance métier

EZScore.score
= layout HTML générique, actuellement utilisé pour les documents autonomes d'impression

ezscore_templates/
= templates de régions et de vues
```

Aucune couche `service`, `repository`, `domain` ou équivalent n'est introduite à cette étape.

### Moteur `EZScoreTemplate.py`

Le moteur est volontairement proche du vocabulaire SCORE d'OPUS et ne dépend pas de Jinja.

Syntaxe supportée :

```text
{{ value }}
{{ object.value }}
{{{ raw_html }}}

[[ if: condition ]]
...
[[ endif ]]

[[ foreach: collection as item ]]
...
[[ endforeach ]]

[[ include: path/to/file.score ]]
```

Règles :

```text
{{ ... }} = HTML échappé
{{{ ... }}} = HTML brut explicitement fourni par le contrôleur
pas d'expression Python
pas d'appel de fonction depuis le template
pas d'accès SQLite
pas d'accès Streamlit
pas de logique musicale
```

### Layout et templates par zone

Arborescence retenue :

```text
EZScore.score                       layout document
EZScoreTemplate.py                 renderer SCORE Python

ezscore_templates/
├─ header.score                    entête chanson
├─ left-panel.score                informations de marge / sidebar
└─ views/
   ├─ grid.score                   vue Grille
   ├─ lyrics.score                 vue Paroles + accords
   ├─ blocks.score                 vue Blocs
   └─ analytic.score               zone Analyse
```

Le layout principal et les fragments sont séparés afin que la future migration OPUS/PHP puisse conserver le même découpage de représentation.

Streamlit reste responsable du placement physique de ses widgets : colonne principale, sidebar, dataframes, graphiques et formulaires. Les templates ne doivent pas essayer de piloter ces widgets.

### État de migration du rendu

Dans ce lot :

```text
header.score
-> rendu réel de l'entête compact

left-panel.score
-> rendu réel des indicateurs Éditeur / modifications validées / découpage non validé

grid.score
-> rendu réel du tableau HTML d'une grille en mode Vue

lyrics.score
-> enveloppe réelle du parolier HTML

blocks.score
-> entête de la vue structurelle ; le dataframe reste Streamlit

analytic.score
-> entête de la zone d'analyse ; les métriques/graphes restent Streamlit

EZScore.score
-> layout réel de la fenêtre HTML autonome d'impression
```

La migration est volontairement progressive : aucune logique d'analyse ou de persistance n'est déplacée pour « remplir » artificiellement les templates.

### Impression — correctif du même lot

Deux défauts observés après V50 sont corrigés :

```text
1. icône d'impression rendue de façon étrange dans l'iframe
2. première page blanche possible dans la grille imprimée
```

Correctifs :

```text
emoji imprimante remplacé par une icône SVG
iframe d'icône fixée à 40 x 40, sans scrollbar
fenêtre autonome conservée
A4 portrait et marges 9 mm conservés
un bloc complet de grille n'est plus forcé sur une seule page
une ligne de quatre mesures reste insécable
```

Le but est d'éviter qu'un grand bloc structurel soit repoussé intégralement sur la page suivante, cause possible d'une première page vide.

### Contrat de non-régression

L'introduction du templating ne doit modifier aucun de ces éléments :

```text
Demucs
Whisper
analyse harmonique
tonalité
signature
capodastre
SQLite
versions de partition
corrections de grille
corrections de paroles
découpage structurel
Session State
navigation principale
```

Le contrat musical reste :

> **Interpréter le signal audio, ne pas inventer une progression.**

### Suite

La prochaine extraction de représentation doit continuer vue par vue, sans modulariser le métier tant que ce chantier n'est pas explicitement décidé.

