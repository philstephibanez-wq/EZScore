# EZScore_v1 — Cahier des charges fonctionnel

Version de référence : R30 — Workflow Labs / ChordsLab.

## Rôles globaux

Les rôles sont définis par Symfony :

- `ROLE_READER`
- `ROLE_EDITOR`
- `ROLE_ADMIN`

L'attribution d'un rôle à un utilisateur est persistée dans `users.roles`.

Hiérarchie :

```text
ROLE_ADMIN
  -> ROLE_EDITOR
       -> ROLE_READER
```

## Lecteur

Un Lecteur crée des playlists personnelles.

Une playlist personnelle :

- appartient toujours à un utilisateur humain ;
- contient une collection ordonnée de chansons ;
- peut être partagée avec d'autres utilisateurs déjà inscrits ;
- le partage personnel exige une invitation ;
- l'invité doit accepter ou refuser ;
- aucune visibilité n'est accordée tant que l'invitation reste en attente ;
- une invitation acceptée donne un accès en lecture ;
- le propriétaire peut retirer le partage ;
- l'invité peut quitter le partage.

La sélection des utilisateurs se fait par nom affiché. L'identifiant persistant est `user_id`.

## Éditeur et groupes musicaux

Un Éditeur hérite des droits du Lecteur et peut créer un ou plusieurs groupes.

Cas d'usage principal : un Éditeur est chef de formation d'un ou plusieurs groupes musicaux.

Exemple :

```text
Groupe : Formation A
Membres :
- Alice
- Bob
- Chloé

Playlist : Répétition samedi 30/08/2026
1. Chanson A
2. Chanson B
...
n. Chanson N
```

Le chef de formation :

- crée le groupe ;
- compose la collection de membres ;
- crée ou possède des playlists ;
- affecte une ou plusieurs playlists au groupe ;
- peut retirer une playlist du groupe sans la supprimer.

## Accès automatique par groupe

Une playlist affectée à un groupe est visible automatiquement par tous les membres du groupe.

Aucune invitation playlist n'est créée et aucune confirmation n'est demandée.

```text
Partage personnel
= PlaylistInvitation
= acceptation requise

Partage par groupe
= GroupMember + PlaylistGroup
= accès automatique
= aucune invitation
```

Retirer un utilisateur du groupe retire immédiatement son accès hérité.

Retirer une playlist du groupe retire l'accès hérité mais conserve la playlist.

## Collections métier

```text
UserGroup
  -> collection de GroupMember
  -> collection de Playlist via PlaylistGroup

Playlist
  -> owner User
  -> collection de PlaylistGroup
  -> collection ordonnée de Song via PlaylistItem
  -> collection de PlaylistInvitation pour le partage personnel
```

Une playlist peut être affectée à plusieurs groupes.

## Propriété d'une playlist

Une playlist possède toujours un propriétaire humain `owner_user_id`.

Le rattachement à un groupe est une association, pas une propriété.

Le modèle historique `owner_type / owner_id` est supprimé.

## ACL

Symfony Security est l'unique moteur d'autorisation.

Les règles passent par :

- `PlaylistVoter`
- `GroupVoter`
- `SongVoter`

Les contrôleurs utilisent `denyAccessUnlessGranted()`.
Les templates utilisent `is_granted()`.

Le partage d'une playlist ne contourne jamais les droits propres aux chansons.

## Ergonomie des collections

Les listbox volumineuses sont remplacées par un sélecteur modal générique avec :

- recherche ;
- filtres métier ;
- pagination serveur ;
- cases à cocher ;
- sélection multiple ;
- sélection de la page courante ;
- ajout groupé ;
- retrait groupé.

### Groupe > Membres

Filtres :

- nom affiché ;
- rôle global ;
- actif / inactif ;
- présent / absent selon l'action.

Actions :

- ajouter plusieurs membres ;
- retirer plusieurs membres ;
- changer le rôle contextuel `member / manager / owner`.

Le groupe doit toujours conserver au moins un `owner`.

### Groupe > Playlists

Filtres :

- nom ;
- visibilité ;
- déjà affectée / non affectée.

Actions :

- affecter plusieurs playlists ;
- retirer plusieurs playlists.

Un Éditeur ne peut affecter que les playlists qu'il peut modifier. L'Admin peut tout administrer.

### Playlist > Chansons

Filtres :

- titre / artiste ;
- statut ;
- déjà présente / absente.

Actions :

- ajouter plusieurs chansons ;
- retirer plusieurs chansons ;
- conserver l'ordre explicite.

### Playlist > Partage personnel

Filtres :

- nom affiché ;
- rôle global ;
- état du compte ;
- déjà invité / non invité.

Actions :

- inviter plusieurs utilisateurs ;
- retirer plusieurs invitations ou partages.

## Back-office Admin

Pour chaque groupe :

- propriétaires ;
- gestionnaires ;
- nombre de membres ;
- nombre de playlists ;
- date ;
- description.

Pour chaque playlist :

- propriétaire humain ;
- groupes associés ;
- créateur ;
- visibilité ;
- nombre de chansons ;
- états de partage ;
- date.

## Doctrine

Toutes les modifications de structure passent par des migrations.

Ne jamais utiliser :

```text
doctrine:schema:update --force
```

Après migration, `doctrine:schema:validate` doit être vert et
`doctrine:schema:update --dump-sql` ne doit proposer aucun SQL.


## 11. Événements et type Session

`Event` reste le concept technique générique. L'interface expose actuellement un seul type métier : `Session`.

```text
Event
└─ type = session
```

D'autres types pourront être ajoutés ultérieurement sans remettre en cause le modèle.

Une Session organise un rendez-vous musical autour d'une date, d'un groupe, d'une playlist et de participants.

Cas d'usage :

```text
Session : Répétition du 30/10/2026
Groupe : Formation A
Playlist : Répétition 30/10/2026
Mode : présentiel / à distance / hybride
Participants : membres du groupe
```

Un `Event` de type `session` possède :

- un titre ;
- une description ;
- une date/heure de début ;
- une date/heure de fin facultative ;
- un mode `onsite`, `remote` ou `hybrid` ;
- un lieu facultatif ;
- une URL de session distante facultative ;
- un statut `draft`, `scheduled`, `cancelled` ou `completed` ;
- un créateur ;
- zéro ou un groupe ;
- zéro ou une playlist ;
- une collection de participants.

### 11.1 RSVP

La participation à une Session est indépendante de l'accès à la playlist.

États :

```text
invited
accepted
declined
maybe
```

L'appartenance à un groupe donne l'accès automatique aux playlists du groupe, mais une invitation à un événement peut demander une confirmation de présence.

### 11.2 Session associée à un groupe

Lorsqu'un groupe est associé à la Session :

- les membres actifs du groupe deviennent participants de l'événement ;
- aucune invitation de playlist n'est créée ;
- ils reçoivent l'invitation de Session ;
- la réponse RSVP reste individuelle.

Si une playlist est associée à l'événement et n'est pas encore affectée au groupe, EZScore peut créer l'association `PlaylistGroup` lorsque l'organisateur possède les droits nécessaires.

### 11.3 Session hors groupe

Une Session peut être organisée sans groupe.

Lorsqu'une playlist est associée, les participants proposés doivent déjà avoir accès à cette playlist :

- propriétaire ;
- partage personnel accepté ;
- accès hérité via un groupe ;
- ou playlist publique.

La Session ne doit pas servir à contourner l'ACL playlist.

## 12. Notifications d'événement

Canaux retenus :

```text
EZScore / in-app
Email
Partage utilisateur WhatsApp
Partage utilisateur Facebook
Partage utilisateur X
```

Le SMS n'est pas retenu.

### 12.1 Notification interne

Une invitation persistée dans `EventParticipant` apparaît dans la liste des invitations EZScore de l'utilisateur.

### 12.2 Email

L'ajout d'un participant déclenche un email d'invitation lorsque le transport mail est disponible.

L'échec du transport mail ne doit pas annuler la création de l'invitation persistée.

### 12.3 Réseaux sociaux

WhatsApp, Facebook et X sont des boutons de partage explicites déclenchés par l'utilisateur.

Ils ne constituent pas le canal métier principal et ne doivent pas être nécessaires au fonctionnement de l'événement.

Aucun numéro de téléphone n'est requis dans EZScore.

### 12.4 Web Push

Le Web Push/PWA reste le prochain canal automatique gratuit à ajouter.

Il devra utiliser :

- consentement explicite de l'utilisateur ;
- abonnement navigateur persistant ;
- VAPID ;
- Service Worker ;
- possibilité de désinscription.

Aucun faux push local ne doit être présenté comme un Web Push.

### 12.5 Telegram / Discord

Telegram Bot et Discord Webhook restent des connecteurs automatiques optionnels futurs par groupe.

Ils ne doivent pas modifier le cœur du modèle `Event`.

## 13. Ergonomie des événements

La même ergonomie de sélecteur modal utilisée pour les collections R18 est réutilisée :

- associer un groupe : sélection simple ;
- associer une playlist : sélection simple ;
- gérer les participants : sélection multiple avec checkbox ;
- recherche ;
- pagination serveur ;
- ajout/retrait groupés.

Le sélecteur générique doit donc supporter les modes `single` et `multiple`.


## 14. Scalabilité globale des listes et écrans de gestion

EZScore doit rester exploitable avec des centaines ou milliers d'entités.

Aucune page de gestion ne doit reposer sur un scroll continu de toutes les lignes ou cartes disponibles.

### 14.1 Principe général

Les écrans suivants utilisent systématiquement :

- recherche texte serveur ;
- index alphabétique A-Z ;
- filtres métier contextuels ;
- pagination serveur ;
- compteur de résultats ;
- conservation des filtres pendant la navigation ;
- aperçu limité pour les collections imbriquées volumineuses ;
- sélecteur modal paginé pour les ajouts/retraits massifs.

Le catalogue Chansons sert de référence ergonomique pour la recherche et l'index alphabétique.

### 14.2 Administration des utilisateurs

Le back-office Utilisateurs doit filtrer par :

- nom affiché ;
- e-mail ;
- lettre initiale ;
- rôle global ;
- compte actif / inactif ;
- compte Google lié / local ;
- langue.

La liste est paginée côté serveur.

Une modification ou suppression d'un utilisateur conserve le contexte de filtre et la page courante.

### 14.3 Administration des groupes

Le back-office global des groupes doit permettre :

- recherche par nom ou description ;
- recherche par membre ;
- recherche par e-mail de membre ;
- filtre par rôle contextuel `owner / manager / member` ;
- index alphabétique ;
- pagination serveur.

La page Groupes accessible aux utilisateurs autorisés doit aussi être paginée.

Pour éviter une page gigantesque, chaque carte groupe n'affiche qu'un aperçu des membres et playlists lorsque aucun filtre précis n'est actif.

Les collections complètes continuent à être administrées via le sélecteur modal paginé.

### 14.4 Administration des playlists

Les playlists sont filtrables par :

- nom ;
- description ;
- propriétaire ;
- groupe lié ;
- lettre initiale ;
- portée : mes playlists / via mes groupes / partagées / publiques ;
- chanson contenue par titre ou interprète.

La liste principale est paginée côté serveur.

Les chansons d'une playlist sont présentées sous forme d'aperçu limité lorsqu'aucune recherche chanson n'est active.

Les partages personnels sont présentés par compteurs, pas par une liste illimitée de noms. Leur gestion complète se fait via le sélecteur modal.

### 14.5 Sessions

La liste des Sessions est filtrable par :

- titre ;
- groupe ;
- playlist ;
- créateur ;
- lettre initiale ;
- statut ;
- mode présentiel / distant / hybride ;
- période à venir / passée / toutes.

La liste est paginée côté serveur.

La liste des participants d'une Session possède sa propre recherche, son index alphabétique, son filtre RSVP et sa pagination serveur.

### 14.6 Collections imbriquées

Une collection imbriquée ne doit jamais provoquer un scroll de plusieurs centaines de lignes dans une carte.

Règle :

```text
Liste principale -> pagination serveur
Collection imbriquée -> aperçu borné
Gestion complète -> recherche + picker/pagination
```

L'interface doit toujours afficher le nombre total d'éléments afin que l'utilisateur sache qu'il voit un aperçu.

### 14.7 Performance

Les contrôleurs ne doivent pas charger toutes les entités en mémoire pour ensuite les filtrer en PHP lorsqu'une requête Doctrine peut appliquer les ACL et filtres côté serveur.

Les requêtes de liste doivent :

- filtrer en SQL/DQL ;
- utiliser `COUNT(DISTINCT ...)` pour les jointures ;
- limiter les résultats avant hydratation ;
- éviter les listes HTML de centaines d'options ;
- ne charger les collections associées que pour la page courante.


## 15. Répertoire administrateur et ergonomie personnelle

### 15.1 Répertoire = back-office chansons pour l'Admin

Lorsqu'un Admin consulte le Répertoire, il dispose d'outils de back-office directement sur les morceaux.

Fonctions obligatoires :

- recherche par titre, interprète, auteur, compositeur ou éditeur ;
- tri par titre ou interprète ;
- index alphabétique ;
- filtre par statut ;
- filtre par éditeur ;
- pagination serveur ;
- changement de statut ;
- réattribution à un autre Éditeur actif ;
- suppression d'un morceau ;
- conservation du contexte de recherche/filtres après une action.

Le back-office doit permettre notamment de revenir explicitement au statut :

```text
Imported
```

depuis `Editing`, `Published` ou `Analyzed`.

Le statut `Analyzed` reste réservé à la chaîne d'analyse : il peut être conservé lorsqu'il existe déjà, mais ne doit pas être fabriqué manuellement par le back-office.

Une remise à `Imported` signifie fonctionnellement que le morceau doit pouvoir repasser par la chaîne d'analyse. Elle remet également `published_at` à `NULL`.

### 15.2 Modération du répertoire

La modération R21 s'appuie sur les états métier existants :

```text
Imported
Analyzed
Editing
Published
```

et sur la responsabilité éditoriale :

```text
Song.editor
```

Aucun état de modération parallèle n'est créé à ce stade.

L'Admin peut donc :

- dépublier ;
- repasser en édition ;
- remettre en importé ;
- publier ;
- changer l'Éditeur responsable ;
- supprimer.

### 15.3 Suppression

La suppression d'un morceau est réservée à l'Admin.

Les associations Doctrine configurées en cascade, notamment notes, jobs d'analyse et éléments de playlist, suivent leurs règles de suppression.

La suppression de fichiers physiques mutualisés par hash ne doit pas être faite aveuglément lors de cette action.

### 15.4 Profil personnel

`Profil` n'est pas une rubrique d'administration.

Il représente le compte de l'utilisateur connecté, y compris pour un Admin.

Dans le menu latéral :

- `Profil` est retiré de la navigation métier principale ;
- la carte d'identité de l'utilisateur dans le pied du menu devient le point d'accès à son Profil ;
- la section `Administration` reste réservée aux fonctions de back-office.

### 15.5 Aperçu de pochette

Lors de l'import ou de l'édition d'un morceau, le choix d'une pochette doit produire un aperçu local immédiat avant validation.

L'aperçu :

- utilise le fichier sélectionné dans le navigateur ;
- ne déclenche aucun upload avant soumission ;
- accepte JPEG, PNG et WEBP conformément aux règles backend ;
- remplace visuellement le placeholder ou l'ancienne pochette dans la fiche d'édition.


## 16. Mailing « nouvelle chanson disponible »

Lorsqu'une chanson passe effectivement au statut `Published`, EZScore doit pouvoir déclencher un mailing annonçant qu'une nouvelle chanson est disponible.

Le mailing doit être lié à la transition métier de publication, pas à l'affichage du Répertoire.

Principes :

- déclenchement lors d'une transition vers `Published` ;
- envoi uniquement après persistance réussie de la publication ;
- aucun envoi lors d'une simple modification d'une chanson déjà publiée ;
- protection contre les doublons en cas de retry ou de rafraîchissement ;
- lien direct vers la fiche publiée ;
- titre, interprète et pochette utilisables dans le message ;
- respect de la langue du destinataire ;
- possibilité pour l'utilisateur de ne plus recevoir ces annonces ;
- échec d'envoi non bloquant pour la publication elle-même.

La population destinataire et les règles exactes de ré-envoi après dépublication/republication seront fixées avant implémentation.

Architecture cible recommandée :

```text
Song -> transition Published
     -> événement métier SongPublished
     -> file de notification / traitement asynchrone
     -> email aux destinataires éligibles
     -> journal d'envoi anti-doublon
```

Cette fonctionnalité doit utiliser la couche mail existante et ne pas être couplée au contrôleur de publication.


## 17. Implémentation R22 — mailing de publication

R22 implémente le mailing « nouvelle chanson disponible ».

Population éligible :

- utilisateur actif ;
- adresse e-mail vérifiée ;
- préférence `notify_new_songs = true`.

Déclenchement :

- uniquement lors d'une transition réelle de non-publié vers `Published` ;
- depuis le bouton Publier du workspace ;
- depuis le back-office Répertoire Admin lorsqu'un statut passe à `Published`.

Anti-doublon :

```text
song_publication_notifications
UNIQUE(song_id, user_id)
```

Un destinataire déjà marqué `sent_at` n'est pas renvoyé.

Un destinataire en échec reste journalisé avec :

- `failed_at`
- `last_error`

et pourra être retenté lors d'une future transition de publication.

La préférence est modifiable dans le Profil personnel.

R22 utilise le Mailer Symfony existant et le transport configuré par `MAILER_DSN`.

### 17.1 Envoi asynchrone R22.1

L'envoi des e-mails est asynchrone.

La requête HTTP de publication ne parcourt pas les destinataires et n'envoie aucun e-mail. Elle ajoute uniquement un job persistant :

```text
song_publication_mail_jobs
```

Un worker séparé traite ensuite le job :

```text
php bin/console app:mailing:worker
```

Le worker :

- réclame un seul job à la fois avec un token de claim ;
- considère un claim comme abandonné après 15 minutes ;
- reprend un job abandonné ;
- sélectionne les destinataires éligibles ;
- s'appuie sur `song_publication_notifications` pour éviter les doublons ;
- reprend uniquement les destinataires non envoyés après un incident ;
- applique un backoff progressif après erreur ;
- n'empêche jamais la publication du morceau.

Cette première file asynchrone est implémentée directement sur Doctrine/SQLite afin de ne pas ajouter de dépendance runtime supplémentaire. Elle pourra ultérieurement être remplacée par Symfony Messenger sans modifier le contrat métier de publication.


## 18. Pipeline musical — Étape 1 uniquement : STEMS

R23 ouvre le nouveau pipeline musical avec un périmètre volontairement strict.

### 18.1 Entrée

La source est exclusivement l'audio original persistant du morceau.

Formats importés déjà supportés par EZScore :

```text
MP3
WAV
FLAC
M4A
OGG
AAC
```

La normalisation technique en WAV est autorisée uniquement pour alimenter les moteurs de séparation. L'audio original reste la référence temporelle.

### 18.2 Sorties persistées

R23 utilise la stratégie qualité de l'ancienne version EZScore :

```text
BS-RoFormer
├─ vocals
├─ drums
├─ bass
├─ guitar
├─ piano
└─ other

vocals
└─ MelBand-RoFormer karaoke
   ├─ lead_vocals
   └─ backing_vocals
```

Les STEMS persistés sont donc :

```text
vocals
lead_vocals
backing_vocals
drums
bass
guitar
piano
other
```

`vocals` est volontairement conservé en plus de `lead_vocals` et `backing_vocals` afin de préserver la sortie brute de première séparation.

### 18.3 Périmètre interdit à R23

R23 NE DOIT PAS lancer :

- Whisper ;
- paroles ;
- phonèmes ;
- accords ;
- tempo ;
- beats ;
- mesures ;
- structure / blocs ;
- MIDI ;
- conducteur ;
- karaoké.

Le manifeste R23 porte explicitement `scope = stems_only`.

### 18.4 Persistance / réanalyse

Les STEMS sont stockés hors de la base, sous :

```text
var/storage/stems/song-{id}/{audio_sha256}/
```

Chaque exécution réussie produit un run immuable.

Un pointeur `current.json` désigne le run courant.

Une réanalyse :

- produit d'abord un nouveau run complet ;
- ne remplace le pointeur courant qu'après réussite ;
- conserve au maximum les deux derniers runs ;
- ne détruit donc jamais la version courante en cas d'échec.

### 18.5 Worker asynchrone

La séparation n'est jamais exécutée dans la requête HTTP.

Le bouton STEMS crée un `AnalysisJob` de type :

```text
kind = stems
```

Le worker dédié est :

```text
php bin/console app:stems:worker
```

Le claim est conditionnel en base afin d'éviter qu'un même job soit pris simultanément par deux workers.

### 18.6 Vérification à l'oreille

La page STEMS permet d'écouter séparément chaque fichier persistant :

- voix globale ;
- chant principal ;
- chœurs ;
- batterie ;
- basse ;
- guitare ;
- piano / claviers ;
- autres instruments.

Il ne s'agit PAS encore de la future table de mixage.

### 18.7 Suppression / changement d'audio

La suppression d'une chanson supprime également son répertoire physique de STEMS.

Un remplacement de l'audio source change son SHA-256 : les anciens STEMS ne peuvent donc plus être considérés comme courants pour le nouvel audio.

### 18.8 Étapes futures déjà décidées mais non implémentées en R23

Le futur lecteur utilisera les STEMS avec :

```text
mix par défaut de Playlist
+ surcharge persistante par User
```

Mute / activation / volume seront modifiables en temps réel.

Ce mixer n'est PAS implémenté en R23.

De même, le verrou empêchant un utilisateur non Admin de publier un morceau tant que le workflow n'est pas terminé jusqu'au karaoké reste une exigence future. Il sera activé lorsque les critères de complétude des étapes suivantes auront été définis.

## 30. Workflow Labs et ChordsLab

### 30.1 Workflow chanson de référence

Le workflow fonctionnel de la chanson devient :

```text
Import
Analyse
Édition
StemsLab
ChordsLab
LyricsLab
Publication
```

Nomenclature :

- `StemsLab` remplace l'intitulé historique `STEMS` dans l'interface ;
- `ChordsLab` est l'espace d'édition et de lecture harmonique synchronisée ;
- `LyricsLab` est l'espace dédié aux paroles, phonèmes, alignements et corrections textuelles ;
- `Publication` reste l'étape de finalisation éditoriale.

Les trois espaces `StemsLab`, `ChordsLab` et `LyricsLab` doivent conserver une identité visuelle cohérente et une navigation homogène.

### 30.2 Ergonomie multi-écran obligatoire

Toutes les fonctions Labs sont conçues dès l'origine pour :

- PC ;
- tablette ;
- smartphone.

Aucun écran ne doit être conçu uniquement pour le desktop puis adapté a posteriori.

Règles :

- aucun scroll horizontal global imposé ;
- composants fluides ;
- contrôles tactiles utilisables au doigt ;
- informations principales visibles avant les fonctions secondaires ;
- réduction de hauteur verticale lorsque cela améliore la lisibilité ;
- panneaux secondaires repliables ;
- maintien des fonctions essentielles sur les petits écrans.

Sur smartphone, les contrôles peuvent passer sur plusieurs lignes, mais l'ordre fonctionnel et la lisibilité doivent rester constants.

## 31. Source de vérité temporelle

### 31.1 Timeline canonique

La timeline est la source de vérité de ChordsLab.

Les représentations graphiques d'accords, mesures et beats ne sont jamais la donnée canonique.

Principe :

```text
Audio / temps courant
        ↓
Timeline canonique
        ↓
Mesures / beats / subdivisions
        ↓
Accords ancrés temporellement
        ↓
Overrides manuels
        ↓
Transformation d'affichage
        ↓
Prompteur ChordsLab
```

La chaîne compacte affichée, par exemple :

```text
[ Em--- ] [ Am-A. ] [ C--- ]
```

est un rendu calculé depuis la timeline.

Elle ne doit jamais devenir la source primaire des données harmoniques.

### 31.2 Continuité harmonique entre mesures

Si un accord reste actif à la mesure suivante, il doit être réaffiché explicitement dans cette nouvelle mesure.

Exemple :

```text
[ Em--- ] [ Em--- ]
```

et non :

```text
[ Em--- ] [ ---- ]
```

Aucune mesure ne doit dépendre visuellement d'un accord implicite provenant de la mesure précédente.

### 31.3 Notation compacte

Le renderer ChordsLab utilise la notation compacte existante :

```text
Em---   = accord Em tenu sur la mesure
Em-A.   = représentation compacte selon les positions temporelles
.       = absence de nouvel accord / silence selon la timeline
-       = prolongation de l'accord actif
```

Le rendu doit toujours être dérivé des événements de timeline et de la signature rythmique courante.

## 32. ChordsLab

### 32.1 Player partagé

ChordsLab réutilise le player audio/STEMS existant.

Il ne doit pas introduire un second moteur audio.

Sont réutilisés :

- play ;
- pause ;
- stop ;
- seek ;
- vitesse ;
- horloge courante ;
- synchronisation des STEMS ;
- mixage existant ;
- chaîne d'effets master existante.

Le prompteur écoute la même horloge que le player.

### 32.2 Prompteur synchronisé

Le prompteur affiche les mesures et accords synchronisés avec la lecture.

Il doit fournir :

- mesure courante ;
- beat ou subdivision courante ;
- accord courant ;
- mise en évidence du beat/subdivision actif ;
- défilement automatique ;
- possibilité de sélectionner une mesure ou un accord pour déplacer le player au bon instant.

La navigation visuelle doit rester stable afin d'éviter les sauts de mise en page pendant la lecture.

### 32.3 Diagramme de l'accord courant

Une case à cocher permet d'afficher ou masquer le diagramme d'accord.

Règle de placement :

```text
Diagramme
    ↓
accord courant dans le prompteur
```

Le diagramme est affiché directement au-dessus de l'accord courant, et non dans un panneau latéral permanent.

Il suit l'accord actif pendant la lecture.

Lorsque l'option est désactivée, la zone disparaît complètement afin de préserver la hauteur utile.

### 32.4 Modification en place

Un accord affiché dans le prompteur doit être modifiable directement en place.

Le modèle doit conserver séparément :

```text
accord issu de l'analyse
override manuel éventuel
```

Valeur effective :

```text
chord_effective = chord_override ?? chord_original
```

Une correction ne doit pas détruire la valeur initialement produite par l'analyse.

La correction est persistée.

### 32.5 Reset des accords

ChordsLab fournit un bouton :

```text
Réinitialiser les accords
```

L'action demande confirmation.

Elle supprime les overrides manuels et restaure le résultat de l'analyse.

Une évolution peut proposer :

- reset de la mesure courante ;
- reset de tous les accords.

Le reset global reste obligatoire.

## 33. Capo EZScore

### 33.1 Sémantique produit

Dans EZScore, le capo est volontairement utilisé comme un outil de simplification des formes d'accords à la guitare.

Il ne modifie pas :

- la tonalité réelle ;
- la timeline harmonique ;
- la hauteur audio ;
- le résultat canonique de l'analyse.

Exemple :

```text
Tonalité réelle : Cm
Accord réel     : Cm
Capo EZScore    : 3
Forme affichée  : Am
```

La tonalité reste `Cm`.

### 33.2 Temps réel et persistance

Le capo :

- est modifiable sans réanalyse ;
- met immédiatement à jour les formes d'accords affichées ;
- met immédiatement à jour le diagramme courant ;
- est persistant au niveau éditorial de la chanson/version.

La transformation capo intervient uniquement dans la couche de rendu.

## 34. Tonalité et future transposition

### 34.1 Tonalité dans le cartouche

Le cartouche de la chanson affiche la tonalité réelle du morceau.

Exemple :

```text
Titre     : La Bohème
Artiste   : Charles Aznavour
Tonalité  : Cm
Mesure    : 6/8
Capo      : 3
```

Le capo n'altère jamais cette tonalité affichée.

### 34.2 Transposition future

La transposition est distincte du capo.

Architecture prévue :

```text
timeline canonique
→ transposition réelle éventuelle
→ nouvelle tonalité
→ simplification éventuelle par capo
→ rendu ChordsLab
```

La transposition n'est pas définie fonctionnellement dans la présente version et fera l'objet d'une étude séparée.

## 35. Signature rythmique

### 35.1 Liste exhaustive et modèle extensible

ChordsLab fournit une liste déroulante de signatures rythmiques courantes et composées, notamment :

```text
2/2
2/4
3/2
3/4
3/8
4/2
4/4
4/8
5/4
5/8
6/4
6/8
7/4
7/8
9/8
10/8
11/8
12/8
12/16
13/8
15/8
```

Le modèle ne doit pas dépendre d'une liste fermée.

La signature est stockée sous forme :

```text
numerator
denominator
```

afin de supporter également des signatures telles que `13/16` sans modification du renderer.

### 35.2 Recomposition temps réel

Changer la signature rythmique ne relance pas l'analyse audio.

Le renderer regroupe les événements existants de la timeline dans de nouvelles mesures.

Exemple :

```text
4/4
[ Em--- ]

→ 2/4

[ Em- ] [ Em- ]
```

La modification est persistée.

Les signatures composées, notamment `6/8`, doivent conserver leurs subdivisions réelles et permettre un marquage visuel adapté des pulsations ternaires.

## 36. Niveau d'analyse harmonique

ChordsLab propose un mode d'analyse persistant :

```text
Débutant
Intermédiaire
Expert
```

### Débutant

Objectif : simplicité et jouabilité.

- triades majeures et mineures prioritaires ;
- accords simples ;
- réduction des enrichissements ;
- changements harmoniques limités aux événements significatifs.

### Intermédiaire

Objectif : compromis entre lisibilité et fidélité.

- majeur / mineur ;
- 7 ;
- m7 ;
- maj7 ;
- sus2 / sus4 ;
- dim / aug lorsqu'ils sont suffisamment fiables ;
- changements harmoniques plus fins.

### Expert

Objectif : restitution harmonique maximale.

- extensions ;
- altérations ;
- slash chords ;
- accords enrichis ;
- changements plus fins ;
- substitutions détectées lorsque le moteur les estime suffisamment fiables.

Le niveau agit sur l'analyse harmonique, pas seulement sur l'affichage.

Un changement de niveau peut donc nécessiter une nouvelle analyse des accords.

## 37. StemsLab dans ChordsLab

### 37.1 Panneaux repliés par défaut

Dans ChordsLab :

```text
▸ Pistes
▸ Chaîne d'effets master
```

sont repliés par défaut.

Le transport principal reste visible.

Le prompteur reste la fonction prioritaire à l'écran.

L'état ouvert/fermé relève de la préférence d'interface utilisateur et ne constitue pas une donnée éditoriale de la chanson.

### 37.2 Chaîne audio existante

La chaîne existante est conservée :

```text
STEMS / Original
→ gains individuels
→ bus master
→ EQ master
→ compression
→ limiteur
→ gain master
→ sortie
```

ChordsLab ne duplique pas cette chaîne.

## 38. Responsive ChordsLab

### 38.1 PC

Sur PC :

- prompteur horizontal prioritaire ;
- plusieurs mesures visibles ;
- diagramme ancré au-dessus de l'accord actif ;
- transport toujours visible ;
- Pistes et Effets repliés par défaut ;
- réglages Capo / Signature / Niveau regroupés dans une barre compacte.

### 38.2 Tablette

Sur tablette :

- aucun scroll horizontal global ;
- plusieurs mesures restent visibles si l'espace le permet ;
- réglages répartis sur une ou deux lignes ;
- panneaux secondaires en accordéon ;
- diagramme toujours lié visuellement à l'accord actif ;
- boutons et sliders dimensionnés pour le tactile.

### 38.3 Smartphone

Sur smartphone :

- prompteur prioritaire ;
- nombre de mesures visibles réduit sans perte fonctionnelle ;
- défilement automatique centré autour de la mesure active ;
- diagramme affiché au-dessus de l'accord courant ;
- réglages Capo / Signature / Niveau empilables ;
- Pistes et Effets en accordéons pleine largeur ;
- transport tactile ;
- aucune largeur desktop imposée ;
- aucune perte de fonction essentielle.

Les cibles tactiles importantes doivent viser une hauteur d'environ 40 à 44 px sans imposer cette hauteur aux simples lignes de lecture.

## 39. Données persistées ChordsLab

Le modèle cible distingue au minimum :

```text
Timeline :
- start_time
- end_time ou durée
- measure_index
- beat/subdivision
- chord_original
- chord_override nullable

Paramètres éditoriaux :
- key_original
- capo
- time_signature_numerator
- time_signature_denominator
- chord_analysis_level
```

Les transformations de rendu ne doivent pas altérer les données canoniques.

Invariant :

```text
timeline = source de vérité
prompteur = projection visuelle
capo = transformation d'affichage
transposition = future transformation harmonique distincte
```

## 40. ChordsLab — analyse simplifiée type RiffStation et maintien écran

### 40.1 Analyse harmonique

ChordsLab privilégie la lisibilité et la stabilité : source harmonique prioritaire `bass + guitar + piano + other`, source rythmique prioritaire `drums`, audio original en fallback, priorité aux triades, pénalité aux changements trop fréquents, bonus tonal léger et enrichissements Intermédiaire conservés uniquement si leur preuve est nette. L’objectif est une lecture immédiatement exploitable à la guitare, proche de l’esprit RiffStation, avant correction manuelle éventuelle.

### 40.2 Prompteur centré

Pendant la lecture, le diagramme reste visuellement fixe et le beat/accord courant se déplace sous lui. Le centrage est piloté par l’horloge du player et reste identique sur PC, tablette et smartphone.

### 40.3 Maintien de l’écran allumé

Option `Garder l’écran allumé pendant la lecture` via Screen Wake Lock lorsque disponible. Play demande le verrou ; Pause, Stop, page cachée ou quittée le libèrent ; si la lecture continue, le verrou est redemandé quand l’onglet redevient visible. La préférence est conservée localement sur l’appareil. Le navigateur et l’OS peuvent toujours refuser ou révoquer le verrou.


## 41. ChordsLab — analyse asynchrone et progression

L’analyse harmonique ChordsLab est exécutée comme un job du Worker Desktop.

Objectifs :

- ne jamais bloquer le serveur PHP local pendant l’analyse ;
- afficher le job dans EZScore Analysis Worker ;
- publier une progression 0–100 % ;
- afficher la même progression dans ChordsLab ;
- permettre au navigateur de rester réactif pendant tout le calcul.

Étapes indicatives :

```text
5%   chargement audio
18%  beats
32%  chroma
50%  reconnaissance des accords
68%  lissage temporel
84%  construction timeline
96%  écriture résultat
100% terminé
```

### 41.1 Niveaux d’analyse

Débutant : triades majeures/mineures uniquement, pénalité forte sur les changements.

Intermédiaire : triades prioritaires ; 7, m7, sus et dim seulement avec preuve harmonique suffisante.

Expert : enrichissements supplémentaires et pénalité de transition plus faible.

### 41.2 Alignement des mesures

Le moteur estime la phase de downbeat à partir des accents rythmiques.

Si la preuve est faible, le premier beat détecté reste beat 1.

Si la preuve est forte, les beats précédant le premier downbeat constituent une mesure de levée explicite ; la timeline conserve leurs vrais `measure_index` / `beat_index`.

Le renderer ChordsLab respecte ces positions canoniques pour la signature courante.

### 41.3 Reset et volume

Les confirmations destructives utilisent une modale EZScore responsive et non une popup native du navigateur.

Le transport expose un volume master compact immédiatement visible. Il pilote la même valeur master que la chaîne d’effets.


## 42. ChordsLab — trois profils harmoniques simultanés

Une analyse ChordsLab produit désormais simultanément trois couches harmoniques partageant la même timeline rythmique :

```text
Timeline canonique beats/mesures
        ├── Débutant
        ├── Intermédiaire
        └── Expert
```

Les traitements audio lourds (sources, beat tracking, downbeat, chroma, tonalité) ne sont exécutés qu’une fois.

Les trois profils sont ensuite dérivés à partir des mêmes observations harmoniques.

### 42.1 Richesse progressive

- Débutant : accords majeurs/mineurs simples, changements fortement lissés.
- Intermédiaire : ajoute notamment 7, m7, sus et dim lorsque suffisamment établis.
- Expert : autorise les enrichissements supplémentaires tels que maj7, 6, m6, add9 et une granularité plus fine.

Le passage d’un profil à l’autre ne déclenche aucune nouvelle analyse audio.

### 42.2 Éditions indépendantes

Chaque couche possède ses propres valeurs originales et ses propres overrides.

Une modification effectuée en Débutant ne modifie ni Intermédiaire ni Expert.

Le reset s’applique uniquement au profil courant.

### 42.3 Persistance du profil affiché

Le profil sélectionné est persisté comme préférence ChordsLab du morceau.

Changer de profil dans le prompteur est immédiat ; la préférence est enregistrée en arrière-plan.

### 42.4 Notation compacte mais standard

Une triade majeure simple est affichée sans suffixe redondant :

```text
C
D
E
```

et jamais :

```text
Cmaj
Dmaj
Emaj
```

Le suffixe `maj` reste conservé lorsqu’il apporte une information harmonique réelle, par exemple :

```text
Cmaj7
```

Les noms d’accords standards ne sont pas remplacés par des symboles jazz non universels.

Les slots du prompteur ont une largeur fixe ; les accords longs utilisent une réduction typographique locale sans modifier la donnée canonique.


## 43. ChordsLab — ergonomie profils et protection réanalyse

### 43.1 Réglages immédiats

Le bouton générique `Enregistrer` n’est plus affiché dans ChordsLab.

Les réglages Capo et Signature sont persistés immédiatement lors d’un changement.

Le profil Débutant / Intermédiaire / Expert est également persisté immédiatement et son changement ne déclenche aucun recalcul.

### 43.2 Chargement explicite des profils

Le changement de profil recharge explicitement depuis le serveur la couche d’accords correspondante.

L’interface affiche en permanence :

```text
Profil affiché : Intermédiaire · 56 accords
```

Ce compteur permet de vérifier immédiatement que la couche réellement affichée est celle demandée.

Aucun nouveau job n’est créé lors d’un changement de profil.

### 43.3 Protection contre une réanalyse accidentelle

`Réanalyser les accords` ouvre obligatoirement une modale EZScore de confirmation.

La modale précise que :

- le Worker va recalculer les trois profils ;
- l’opération peut prendre du temps ;
- les corrections manuelles existantes sont conservées profil par profil lorsqu’elles peuvent être réancrées.

Aucune popup native du navigateur n’est utilisée.
