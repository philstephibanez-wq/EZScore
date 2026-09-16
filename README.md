# EZScore — STEM pipeline R9 / workflow 4 étapes + watchdog MIDI chant

## Contrat

Comme MAESTRO :

- aucune erreur masquée ;
- aucun fallback silencieux ;
- si une étape bloque, on identifie le point exact et on l'arrête explicitement ;
- l'audio original reste l'horloge maître ;
- aucun glissement temporel.

## Workflow Analyse

```text
1 — STEM
    séparation Demucs
    → lecteur STEM immédiatement

2 — Paroles
    Whisper small sur audio original
    → même lecteur STEM + paroles synchronisées

3 — Blocs / structure
    mesures + accords + répétitions + paroles
    → segmentation visuelle en blocs

4 — MIDI
    Chant + Accords + Batterie
    → lecteur Audio original + MIDI uniquement quand les 3 pistes sont terminées
```

Le lecteur STEM n'est plus déplacé à la fin du workflow : il apparaît dès que
les stems sont prêts. Après les paroles, ce même lecteur reçoit les mots
horodatés et affiche leur défilement synchronisé.

## Blocage MIDI chant : correction

Le problème venait de l'appel monolithique `librosa.pyin()` sur toute la piste
vocale : aucune progression observable à l'intérieur de cet appel, donc le
worker pouvait rester indéfiniment sur le même état.

R9 applique deux protections réelles :

### pYIN segmenté

La piste vocale est analysée par segments bornés de 20 secondes.
Après chaque segment :

- progression écrite ;
- index `segment n/N` écrit ;
- timestamps absolus conservés.

### Watchdog externe

L'analyse vocale tourne dans un processus enfant dédié.

Le worker superviseur :

- lit `vocal_progress.json` ;
- publie `job_status.json` ;
- tue le processus vocal si aucun progrès n'est constaté pendant 120 s ;
- tue le processus si la durée totale dépasse 900 s ;
- écrit l'erreur réelle dans `job.log` et `job_status.json`.

Il ne continue jamais avec un MIDI chant absent.

## Diagnostics

```text
data/analysis/stem_lab/<hash>/midi/
  job_status.json
  job.log
  vocal_progress.json
  vocal_analysis.json
  vocal.mid
  chords.mid
  drums.mid
  stem_mix.mid
  stem_midi.json
```

## Player MIDI

Instruments modifiables en temps réel :

- Chant : Piano, Voice Oohs, Choir, Strings, Sax, Flute, Synth...
- Accords : Piano, guitares, Strings...
- Batterie : Standard, Room, Power, Electronic, TR-808, Jazz, Brush, Orchestra.

## Validation locale

```powershell
cd H:\EZScore

python -m py_compile .\ezscore\analysis\stem_midi.py
python -m py_compile .\ezscore\analysis\stem_vocal_worker.py
python -m py_compile .\ezscore\analysis\stem_midi_worker.py
python -m py_compile .\ezscore\midi\stem_sync_player.py
python -m py_compile .\ezscore\player\stem_webaudio.py
python -m py_compile .\ezscore\player\media_url.py
python -m py_compile .\ezscore\ui\stem_lab_analysis.py
python -m py_compile .\ezscore\ui\app_shell.py
```

Ne pas ajouter au commit :

- `data/EZScore.sqlite3`
- `data/logs/ezscore_perf.log`
- `data/analysis/`

L'utilisateur effectue commit/push lui-même.


## Job bloqué / worker mort

`load_stem_midi_job()` vérifie maintenant que le PID déclaré `running`
existe réellement. Si le worker a disparu sans mettre à jour le statut,
le job passe explicitement en erreur `worker_dead`.

Aucun état `running` fantôme n'est conservé indéfiniment.


## R9.1 — ergonomie lecteurs et blocs

- Sélecteurs MIDI : thème sombre explicite, texte clair, numéro GM.
- Lecteur STEM : hauteur adaptée pour éviter le scroll interne.
- Blocs : minimum structurel de 4 mesures, sans découpage fixe en groupes de 4.
- Anciennes structures avec blocs de 1–3 mesures normalisées à l'ouverture.
- Aucun timestamp canonique de beat, mesure, accord ou parole n'est déplacé.


## R9.2 — MIDI bloqué à l'étape 1/2

Cause trouvée dans le code : R9 protégeait le chant avec un watchdog, mais
`analyze_drum_beats(drums.wav)` restait exécuté directement dans le worker
principal, sans watchdog ni heartbeat. Si `librosa.onset.onset_strength()` ou
`librosa.beat.beat_track()` se bloque, l'UI reste donc éternellement sur
`Étape MIDI 1/2 : batterie + accords` avec le même temps écoulé.

R9.2 isole aussi la batterie/tempo dans un processus dédié.

Sous-étapes visibles :
- chargement drums.wav ;
- enveloppe d'attaque ;
- détection tempo / beats ;
- post-traitement ;
- écriture accords + batterie ;
- pYIN chant segmenté ;
- finalisation MIDI.

Watchdogs :
- batterie : 90 s sans progrès, 300 s total ;
- chant : 120 s sans progrès, 900 s total ;
- superviseur : statut figé 150 s -> arrêt explicite `worker_stalled`.

Aucun fallback et aucun traitement lourd MIDI n'est désormais hors watchdog.


## R10 — métrique, MIDI rapide, progression automatique, chant amélioré

- Signature toujours visible : 2/4, 3/4, 4/4, 6/8.
- Changer la signature regroupe la beat_timeline et change les accents forts/faibles MIDI sans déplacer les beats audio.
- beat_timeline persistée dans structure_analysis.json.
- Recalcul signature/blocs sans refaire le beat tracking quand la timeline existe.
- MIDI Accords+Batterie généré directement depuis la structure : plus de second beat tracking.
- vocal_analysis.json et vocal.mid préservés lors d'un changement de signature.
- Progression MIDI auto-refresh chaque seconde via st.fragment(run_every=1.0).
- Chant : moteur mature vocal.py réutilisé, pYIN chunké avec 1 s de recouvrement, segmentation globale anti-vibrato.


## R11 — 4 onglets + nettoyage des fausses notes chant

### Navigation

La vue Analyse est maintenant organisée en quatre onglets :
1. STEM
2. Paroles
3. Blocs / structure
4. MIDI

Le but est d'éliminer les scrolls verticaux permanents entre les étapes.

### MIDI chant

Le moteur R10 conservait encore trop de micro-transitions d'un demi-ton sur
certains chants, notamment les vibratos.

R11 renforce uniquement la segmentation MIDI (pas la timeline F0 brute) :
- médiane : 9 frames ;
- hystérésis : 90 cents ;
- changement stable : 140 ms ;
- suppression conservatrice des excursions ±1 demi-ton très courtes
  lorsqu'elles sont entourées par la même note stable.

Exemple traité :
`A -> A# (120 ms) -> A` devient `A` continu.

Une vraie transition chromatique soutenue n'est pas supprimée.


## R11.1 — régénération MIDI explicite

Dans `4 · MIDI`, un résultat terminé peut maintenant être relancé.

- `Régénérer métrique` conserve le chant analysé et recrée accords, batterie et combiné.
- `Régénérer tout le MIDI` supprime aussi `vocal_analysis.json`,
  `vocal_progress.json` et `vocal.mid`, puis relance l'analyse du chant.

Pour Aline et le nouveau nettoyage des faux demi-tons de R11 :
utiliser `Régénérer tout le MIDI`.


## R11.2 — correction PermissionError Windows sur job_status.json

Sous Windows, le fragment Streamlit relit `job_status.json` chaque seconde
pendant que le worker le remplace atomiquement. Une très courte fenêtre de
partage de fichier peut provoquer :

`PermissionError: [Errno 13] Permission denied: ...\job_status.json`

Correction :
- lecture JSON partagée avec retry borné ;
- 12 tentatives espacées de 25 ms ;
- uniquement pour `PermissionError`, `FileNotFoundError` transitoire et
  `JSONDecodeError` transitoire pendant remplacement ;
- si la contention persiste, une `RuntimeError` explicite est levée avec le
  chemin et l'exception réelle ;
- aucun fallback silencieux ;
- écritures atomiques via `os.replace`.

La même protection est utilisée par le superviseur MIDI pour lire les fichiers
de progression du processus vocal.


## R12 — modes de travail + onglets contextuels

La navigation du morceau est simplifiée sans supprimer les éditeurs existants.

### Barre latérale

Pour un utilisateur ayant `song.edit` :
- Analyse
- Édition
- Player

Pour un utilisateur sans droit d'édition :
- Player uniquement

Le capodastre reste immédiatement accessible sous le mode de travail.

### Zone principale

`Analyse` conserve les quatre onglets déjà validés :
- STEM
- Paroles
- Blocs / structure
- MIDI

`Édition` propose en haut de page :
- Blocs
- Paroles + accords
- Grille

Ces trois entrées réutilisent exactement les éditeurs persistants déjà présents
dans `EZScore.py`. Il n'y a pas de second moteur d'édition.

`Player` propose :
- Karaoké
- Paroles + accords
- Grille

Le mode Karaoké utilise le chemin éprouvé `Paroles + accords` avec le player
audio/paroles synchronisé.

### Compatibilité

Le nouveau shell mappe les choix vers les anciennes valeurs internes
`song_view` / `song_mode`. Cela permet de conserver :
- édition des noms et bornes des blocs ;
- édition des paroles par bloc et sauts de ligne ;
- validation/persistance existantes ;
- édition de grille ;
- capo live ;
- lecteurs existants.

Aucune modification du MIDI vocal n'est faite dans R12.


## R12.1 — vrai basculement Édition / Player

R12 changeait le mode dans la sidebar mais, pour un morceau analysé uniquement
par STEM_LAB, l'ancien orchestrateur ne trouvait aucune ligne dans `analyses`.
Il affichait donc encore la page Analyse.

R12.1 ajoute un pont de compatibilité non destructif :
- beat_timeline STEM -> beats éditables ;
- mesures STEM -> mesures EZScore ;
- accords STEM -> grille ;
- Whisper small -> structure `segments[].words[]` attendue par l'éditeur ;
- blocs STEM -> initialisation de `structure_blocks` si aucun bloc utilisateur
  n'existe déjà.

Aucun modèle audio n'est relancé.
Aucun timestamp n'est déplacé.
Les blocs utilisateur déjà persistés ne sont jamais écrasés.

Résultat :
- `Édition` ouvre réellement `Blocs / Paroles + accords / Grille` ;
- `Player` utilise les mêmes données éditées ;
- `Analyse` reste la surface STEM_LAB ;
- MIDI vocal inchangé.


## R12.2 — éditeur Blocs master/detail

### Ergonomie

L'ancien écran Blocs utilisait deux colonnes permanentes :
- structure à gauche ;
- tous les textareas de paroles à droite.

Sur un morceau réel cela réduisait fortement le tableau et créait une page
très haute.

R12.2 conserve le moteur d'édition/persistance existant mais change uniquement
sa présentation :

1. le tableau des blocs occupe toute la largeur ;
2. un sélecteur `Paroles à éditer` choisit un bloc ;
3. sous le tableau, un seul textarea de paroles est rendu ;
4. les autres blocs restent en session et participent toujours à la
   transaction `Valider blocs + paroles`.

Le fonctionnement métier ne change pas :
- Nom et Fin restent éditables dans le tableau ;
- Début et Nb mesures sont recalculés ;
- ajout/suppression de blocs conservés ;
- sauts de ligne des paroles conservés ;
- validation structure + paroles reste atomique ;
- aucun timestamp canonique n'est déplacé.

### Portée

Cette adaptation est strictement limitée à `Édition > Blocs`.
Les autres appels `st.columns`, `st.data_editor`, `st.text_area` de l'application
restent inchangés.

Analyse, Player et MIDI vocal ne sont pas modifiés.


## R12.3 — sélection des paroles directement dans le tableau des blocs

Le sélecteur séparé sous le tableau est supprimé.

Une nouvelle colonne est ajoutée au tableau :

`✏️ Paroles`

Chaque ligne possède une case. La case sélectionne le bloc dont le textarea de
paroles est affiché sous le tableau.

Règles :
- un seul bloc de paroles actif à la fois ;
- le premier bloc est sélectionné par défaut ;
- cocher un autre bloc le rend immédiatement actif ;
- l'éditeur complet n'affiche que ce bloc ;
- les autres textes restent conservés en session et sont sauvegardés avec
  `Valider blocs + paroles`.

La colonne supplémentaire ne modifie pas le moteur de structure :
Nom, Début, Fin, Nb mesures et Suppression gardent leur comportement existant.

Aucun changement dans Analyse, Player ou le MIDI vocal.


## R12.4 — restauration stricte des paroles validées

R12.2/R12.3 devaient être des changements de présentation uniquement.
Le moteur de validation historique attend cependant la valeur de TOUS les
blocs, y compris ceux qui ne sont plus rendus sous forme de textarea.

R12.4 garantit explicitement ce contrat.

### Récupération

Pour chaque bloc :
1. recherche dans `lyric_block_edits` courant ;
2. si aucune correction courante ne correspond, recherche dans les snapshots
   `analysis_versions` ;
3. dans un snapshot, le bloc est identifié en priorité par son `block_id`,
   puis par son `order_index` ;
4. ses anciennes bornes de mesures sont converties avec le `music_json` de
   cette même version ;
5. la correction correspondante est restaurée en mémoire.

Cela permet de récupérer les paroles validées même si les timestamps des
mesures de la nouvelle analyse STEM diffèrent légèrement.

### Protection contre la régression

- aucun DELETE ;
- aucune écriture automatique dans la DB ;
- aucune correction existante non vide n'est écrasée ;
- les blocs non sélectionnés gardent leur texte en session ;
- `Valider blocs + paroles` reçoit toujours les textes de tous les blocs ;
- la présentation master/detail reste inchangée.

Une suppression volontaire effectuée après la récupération reste volontaire :
elle n'est pas restaurée en boucle.


## R12.5 — boutons réels pour sélectionner les paroles

La case à cocher introduite en R12.3 est supprimée.

Sous le tableau des blocs, EZScore affiche maintenant de vrais boutons :
- `✏️ Couplet 1 · 1–17`
- `✏️ Couplet 2 · 18–34`
- etc.

Le bouton du bloc actif est affiché en primaire avec `✓`.
Cliquer un autre bouton bascule immédiatement l'éditeur de paroles.

Le tableau reste dédié aux données de structure :
Nom, Début, Fin, Nb mesures, Supprimer.

La récupération anti-régression des paroles validées de R12.4 reste intacte.


## R12.6 — correction warning Streamlit Session State

Correction du warning :

`The widget with key "ez_work_mode_..." was created with a default value but also had its value set via the Session State API.`

Cause :
le mode `Analyse / Édition / Player` écrivait d'abord la clé dans
`st.session_state`, puis créait le `st.radio` avec `index=...`.

R12.6 :
- n'écrit plus la clé avant la création initiale du widget ;
- passe `index` uniquement lorsque la clé n'existe pas encore ;
- applique la même règle aux `segmented_control` Édition et Player ;
- ne change ni les données, ni les paroles, ni la persistance.

Aucun autre comportement fonctionnel n'est modifié.


## R12.7 — tous les blocs de paroles visibles + bouton Éditer + scroll

### Présentation

Sous la grille des blocs, tous les blocs de paroles sont désormais affichés
dans l'ordre du morceau.

Un seul bloc est éditable à la fois. Les autres restent visibles en lecture.

### Bouton demandé

Sous la grille des blocs, chaque bloc possède sa propre case d'action contenant
un vrai bouton :

`✏️ Éditer les paroles`

Le clic :
1. sélectionne ce bloc ;
2. relance Streamlit ;
3. utilise un composant Streamlit **v2** pour faire défiler la page jusqu'au
   bloc demandé ;
4. passe ce bloc en textarea éditable.

Aucun `st.components.v1.html` n'est utilisé.

### Recalage automatique des paroles

Modifier `Fin` d'un bloc recalcule automatiquement le contenu de TOUS les blocs
sur le brouillon courant.

Les timestamps Whisper restent immuables.

Si un bloc est étendu :
- les mots nouvellement inclus sont ajoutés depuis la timeline Whisper.

S'il est raccourci :
- les mots sortant de l'intervalle disparaissent de ce bloc et deviennent
  disponibles dans le bloc voisin.

Les corrections manuelles situées dans la zone temporelle commune sont
préservées autant que possible, ainsi que leur mise en forme interne.

Aucune commande supplémentaire de "recalage" n'est nécessaire.


## R12.8 — icône stylo dans la grille des blocs

La grille contient désormais directement la cellule d'action demandée :

`Nom | Début | Fin | Nb mesures | Supprimer | ✏️`

L'icône `✏️` est un vrai bouton Streamlit.

Son clic :
1. sélectionne le bloc correspondant ;
2. relance l'interface ;
3. scrolle jusqu'au bloc de paroles ;
4. passe ce bloc en mode édition.

Tous les blocs de paroles restent affichés sous la grille.

Le recalage automatique après modification des bornes, la récupération des
paroles validées et les timestamps canoniques restent inchangés.


## R12.9 — grille simplifiée : Début + Nb mesures

La colonne `Fin` n'est plus affichée.

La grille visible devient :

`Nom | Début | Nb mesures | 🗑 | ✏️`

Le moteur conserve néanmoins `Fin` en interne, dérivée automatiquement :

`Fin = Début + Nb mesures - 1`

Ainsi :
- l'utilisateur édite uniquement le nombre de mesures ;
- le début des blocs suivants se recalcule via la normalisation séquentielle ;
- aucun trou ni chevauchement n'est introduit ;
- le recalage automatique des paroles reste inchangé ;
- le bouton stylo + scroll restent inchangés.


## R12.10 — saisie libre des Nb mesures + validation du total

Suppression du blocage artificiel `max_value` qui réservait une mesure à tous
les blocs suivants.

Le modèle d'édition est maintenant strictement séquentiel :

- premier Début = 1 ;
- Début du bloc N = Fin du bloc N-1 + 1 ;
- Fin interne = Début + Nb mesures - 1.

Quand un `Nb mesures` change, tous les Début suivants sont immédiatement
recalculés.

Pendant l'édition, la somme peut être temporairement inférieure ou supérieure
au nombre total de mesures. La saisie n'est pas bloquée.

La seule règle de validation finale est :

`sum(Nb mesures) == total_measures`

Si la somme est trop petite ou trop grande, `Valider blocs + paroles` refuse la
persistance avec le nombre exact de mesures à ajouter/retirer.

Le recalage automatique des paroles suit les nouvelles bornes séquentielles.
Les timestamps Whisper restent inchangés.


## R13 — signatures métriques génériques sans déplacement de timeline

### Modèle

EZScore sépare désormais :
- la signature `N/D` ;
- le groupement métrique ;
- le nombre de pulsations détectées par mesure ;
- les accents MIDI.

Exemples pris en charge :
- `6/8` + `3+3` -> 2 temps métriques ;
- `9/8` + `3+3+3` -> 3 temps métriques ;
- `12/8` + `3+3+3+3` -> 4 temps métriques ;
- `5/8` + `2+3` -> 2 temps métriques ;
- `7/8` + `2+2+3` -> 3 temps métriques ;
- `5/4` + `3+2` -> 5 pulsations détectées par mesure, accents 1 et 4 ;
- `7/4` + `4+3` -> 7 pulsations détectées par mesure, accents 1 et 5.

La signature est saisie librement au format `N/D`; elle n'est plus limitée à
une liste fermée.

### Invariant temporel

`beat_timeline` reste la timeline canonique en secondes de l'audio original.
Un changement de signature ne déplace aucun timestamp.

Il recalcule seulement :
1. le regroupement des beats en mesures ;
2. le nombre total de mesures ;
3. les numéros de mesures ;
4. les blocs, remappés par leurs bornes temporelles absolues ;
5. les accents métriques MIDI ;
6. les MIDI accords/batterie dépendants de la métrique.

Le MIDI vocal n'est pas invalidé par une simple modification de signature.

### Aline

Avec `6/8` et groupement `3+3`, EZScore regroupe 2 pulsations détectées par
mesure au lieu de 6. Le nombre de mesures est donc recalculé à partir de la
même timeline audio, sans aucun glissement par rapport au MP3.
