# EZScore_v1 — PLAN DE RECETTE FONCTIONNELLE

Version de référence : R30 — recette Workflow Labs / ChordsLab.

Convention :

- `[ ]` non testé
- `[x]` OK
- `[!]` KO
- `[~]` à revoir

Pour chaque KO noter : profil, URL, action, obtenu, attendu, capture et extrait de log.

## 1. Socle

- [ ] site démarre sans erreur
- [ ] `lint:yaml` OK
- [ ] `lint:twig` OK
- [ ] tous les PHP passent `php -l`
- [ ] `doctrine:migrations:status` cohérent
- [ ] migration R18 exécutée
- [ ] migration R19 exécutée
- [ ] `doctrine:schema:validate` OK
- [ ] `doctrine:schema:update --dump-sql` vide
- [ ] aucune utilisation de `schema:update --force`

## 2. Rôles globaux

### Lecteur

- [ ] peut créer une playlist personnelle
- [ ] peut inviter des utilisateurs inscrits à sa playlist
- [ ] ne peut pas créer de groupe
- [ ] ne peut pas importer ou éditer une chanson
- [ ] peut créer un Session personnelle

### Éditeur

- [ ] hérite des droits Lecteur
- [ ] peut créer un groupe
- [ ] peut gérer ses groupes
- [ ] peut affecter ses playlists à ses groupes
- [ ] peut créer un Session pour un groupe qu'il gère

### Admin

- [ ] peut tout administrer
- [ ] voit groupes, propriétaires, playlists et attributs dans le back-office

## 3. Groupes

- [ ] création réservée Éditeur/Admin
- [ ] créateur devient `owner`
- [ ] ajout de plusieurs membres via popup
- [ ] retrait de plusieurs membres via popup
- [ ] filtres utilisateurs fonctionnent
- [ ] rôle contextuel `member`
- [ ] rôle contextuel `manager`
- [ ] rôle contextuel `owner`
- [ ] dernier owner impossible à retirer
- [ ] groupe conserve au moins un owner
- [ ] suppression du groupe ne supprime pas les playlists

## 4. Playlists et groupes

- [ ] une playlist garde toujours un propriétaire humain
- [ ] une playlist peut être affectée à un groupe
- [ ] une playlist peut être affectée à plusieurs groupes
- [ ] affectation de plusieurs playlists via popup
- [ ] retrait groupé des playlists
- [ ] retrait du groupe ne supprime pas la playlist
- [ ] membre du groupe voit automatiquement les playlists affectées
- [ ] aucune invitation playlist demandée pour cet accès
- [ ] retrait du membre retire immédiatement cet accès hérité

## 5. Playlists personnelles

- [ ] Lecteur crée sa playlist
- [ ] ajout de plusieurs chansons via popup
- [ ] retrait de plusieurs chansons via popup
- [ ] ordre des chansons conservé
- [ ] invitation personnelle possible
- [ ] invitation en attente ne donne pas accès
- [ ] invitation acceptée donne accès
- [ ] refus ne donne pas accès
- [ ] retrait du partage retire l'accès
- [ ] invité peut quitter le partage

## 6. Sélecteur modal générique

- [ ] recherche instantanée
- [ ] pagination serveur 25 résultats
- [ ] sélection multiple par checkbox
- [ ] sélectionner la page courante
- [ ] sélection conservée en changeant de page
- [ ] mode simple pour groupe/playlist d'un événement
- [ ] mode multiple pour participants
- [ ] aucune listbox volumineuse pour users/chansons/playlists

## 7. Sessions — création

- [ ] entrée Sessions visible dans le menu
- [ ] création avec titre
- [ ] date/heure de début obligatoire
- [ ] date/heure de fin facultative
- [ ] mode Présentiel
- [ ] mode À distance
- [ ] mode Hybride
- [ ] lieu persistant
- [ ] URL distante persistante
- [ ] description persistante
- [ ] créateur de la Session ajouté comme participant `accepted`

## 8. Sessions — groupe

- [ ] association d'un groupe via popup en sélection simple
- [ ] seuls les groupes administrables sont proposés à un non-Admin
- [ ] association du groupe ajoute ses membres actifs comme participants
- [ ] créateur reste `accepted`
- [ ] autres membres commencent `invited`
- [ ] aucune `PlaylistInvitation` individuelle créée
- [ ] un membre du groupe peut voir la Session
- [ ] un non-membre non invité ne peut pas voir la Session

## 9. Sessions — playlist

- [ ] association d'une playlist via popup
- [ ] un Éditeur ne voit que les playlists qu'il peut modifier
- [ ] si groupe + playlist et droits suffisants, `PlaylistGroup` est créé automatiquement
- [ ] les membres du groupe ont donc accès à la playlist sans invitation
- [ ] la Session ne contourne jamais les droits chanson

## 10. Sessions — hors groupe

- [ ] Session sans groupe possible
- [ ] playlist facultative
- [ ] si playlist associée, seuls les users ayant déjà accès sont proposés
- [ ] propriétaire playlist éligible
- [ ] invité playlist accepté éligible
- [ ] membre d'un groupe ayant la playlist éligible
- [ ] user sans accès playlist non éligible

## 11. Participants et RSVP

- [ ] ajout multiple de participants
- [ ] retrait multiple de participants
- [ ] créateur impossible à retirer via bulk remove
- [ ] statut `invited`
- [ ] réponse `accepted`
- [ ] réponse `declined`
- [ ] réponse `maybe`
- [ ] réponse persistée après reconnexion

## 12. Notifications EZScore / email

- [ ] les invitations apparaissent dans `Mes invitations`
- [ ] ouverture de l'invitation affiche l'événement
- [ ] email envoyé quand SMTP est configuré
- [ ] lien email mène au bon événement
- [ ] locale du destinataire utilisée dans l'email
- [ ] échec SMTP n'annule pas l'invitation persistée
- [ ] `email_notified_at` renseigné uniquement après envoi réussi

## 13. Partage réseaux sociaux

- [ ] bouton WhatsApp présent
- [ ] WhatsApp ouvre un message prérempli avec titre/date/lien
- [ ] bouton Facebook présent
- [ ] Facebook partage l'URL de l'événement
- [ ] bouton X présent
- [ ] X prépare titre + URL
- [ ] aucun numéro de téléphone requis
- [ ] aucun SMS envoyé

## 14. Web Push / connecteurs futurs

Non implémentés en R19, à ne pas considérer comme disponibles.

- [ ] futur Web Push avec VAPID + Service Worker + consentement
- [ ] futur connecteur Telegram Bot optionnel
- [ ] futur connecteur Discord Webhook optionnel

## 15. Modification / cycle de vie Session

- [ ] modification titre
- [ ] modification horaires
- [ ] modification mode
- [ ] modification lieu
- [ ] modification lien distant
- [ ] statut Brouillon
- [ ] statut Planifié
- [ ] statut Annulé
- [ ] statut Terminé
- [ ] suppression Session cascade sur participants

## 16. I18N

- [ ] interface événement FR
- [ ] interface événement EN
- [ ] email événement FR
- [ ] email événement EN
- [ ] aucune clé brute `event.xxx`

## 17. Volume

- [ ] 100+ utilisateurs dans picker sans page HTML énorme
- [ ] 500+ chansons dans picker sans listbox
- [ ] 100+ playlists dans picker
- [ ] pagination et recherche restent réactives
- [ ] ajout/retrait groupé reste stable

## 18. Validation finale

- [ ] aucun bug bloquant
- [ ] ACL groupe/playlist cohérentes
- [ ] Sessions cohérentes
- [ ] invitations personnelles cohérentes
- [ ] accès automatique groupe cohérent
- [ ] Doctrine synchronisé
- [ ] recette validée

Date :
Version / commit :
Testeur :
Commentaires :


## 19. Scalabilité / filtres globaux R20

### Administration Utilisateurs

- [ ] recherche par nom
- [ ] recherche par e-mail
- [ ] index A-Z
- [ ] filtre rôle Reader / Editor / Admin
- [ ] filtre actif / inactif
- [ ] filtre Google lié / local
- [ ] pagination serveur
- [ ] modification conserve filtres + page
- [ ] suppression conserve filtres + page
- [ ] 500 utilisateurs ne produisent pas une page HTML géante

### Administration Groupes

- [ ] recherche groupe par nom / description
- [ ] recherche par membre
- [ ] recherche par e-mail membre
- [ ] filtre owner / manager / member
- [ ] index A-Z
- [ ] pagination indépendante des groupes
- [ ] filtre groupes ne réinitialise pas les filtres playlists du back-office
- [ ] compteur exact de groupes

### Administration Playlists

- [ ] recherche par nom / description
- [ ] recherche propriétaire
- [ ] recherche groupe associé
- [ ] filtre publique / privée
- [ ] index A-Z
- [ ] pagination indépendante des playlists
- [ ] compteur exact de playlists

### Page Groupes utilisateur

- [ ] recherche groupe
- [ ] index A-Z
- [ ] recherche membre
- [ ] recherche playlist liée
- [ ] pagination serveur
- [ ] aperçu membres limité hors recherche
- [ ] aperçu playlists limité hors recherche
- [ ] nombre total membres visible
- [ ] nombre total playlists visible
- [ ] ajout/retrait complet toujours disponible par picker

### Page Playlists utilisateur

- [ ] recherche nom / description / propriétaire / groupe
- [ ] index A-Z
- [ ] filtre Mes playlists
- [ ] filtre Via mes groupes
- [ ] filtre Partagées
- [ ] filtre Publiques
- [ ] recherche chanson contenue
- [ ] pagination serveur
- [ ] aperçu chansons limité hors recherche
- [ ] nombre total de chansons visible
- [ ] partages affichés sous forme de compteurs
- [ ] gestion complète des partages via picker
- [ ] les ACL restent identiques à R18

### Sessions

- [ ] recherche titre / groupe / playlist / créateur
- [ ] index A-Z
- [ ] filtre statut
- [ ] filtre mode
- [ ] filtre période
- [ ] pagination serveur
- [ ] invitations personnelles affichées en aperçu borné
- [ ] participants d'une session recherchables
- [ ] index A-Z participants
- [ ] filtre RSVP participants
- [ ] pagination participants
- [ ] 500 participants ne créent pas un scroll massif

### Performance

- [ ] aucune page testée ne charge toutes les entités avant filtrage PHP
- [ ] pagination appliquée avant hydratation des lignes principales
- [ ] les jointures utilisent un comptage distinct
- [ ] les collections imbriquées sont bornées
- [ ] aucune régression ACL
- [ ] `doctrine:schema:validate` OK
- [ ] `doctrine:schema:update --dump-sql` vide


## 20. Back-office Répertoire / Profil / pochette R21

### Statut des chansons

- [ ] un Admin peut passer `En édition` -> `Importée`
- [ ] un Admin peut passer `Publiée` -> `Importée`
- [ ] un Éditeur propriétaire peut utiliser `Remettre en Importée` dans le workspace
- [ ] la remise en Importée met `published_at` à NULL
- [ ] `Analysée` ne peut pas être fabriqué manuellement si le morceau ne l'est pas déjà
- [ ] un morceau déjà Analysé peut conserver ce statut

### Répertoire Admin

- [ ] la recherche porte sur titre
- [ ] la recherche porte sur interprète
- [ ] la recherche porte sur auteur
- [ ] la recherche porte sur compositeur
- [ ] la recherche porte sur éditeur
- [ ] filtre statut
- [ ] filtre éditeur
- [ ] index A-Z conserve statut et éditeur
- [ ] tri titre/interprète conserve statut et éditeur
- [ ] pagination serveur 50 morceaux
- [ ] modification conserve la page et les filtres
- [ ] réattribution à un autre Éditeur actif
- [ ] changement de statut inline
- [ ] suppression Admin disponible
- [ ] suppression demande confirmation
- [ ] les associations Doctrine en cascade ne bloquent pas la suppression

### Profil

- [ ] `Profil` n'apparaît plus entre Sessions et Administration
- [ ] la carte utilisateur en bas du menu ouvre le Profil personnel
- [ ] comportement identique pour Reader / Editor / Admin
- [ ] la section Administration ne contient que des fonctions administratives

### Pochette

- [ ] import : choisir JPEG affiche immédiatement l'aperçu
- [ ] import : choisir PNG affiche immédiatement l'aperçu
- [ ] import : choisir WEBP affiche immédiatement l'aperçu
- [ ] aucun upload n'est effectué avant validation du formulaire
- [ ] édition : nouvelle pochette remplace immédiatement l'aperçu de l'ancienne
- [ ] annulation/rechargement ne persiste pas un aperçu non validé

### Validation

- [ ] `php -l` OK
- [ ] `lint:yaml` OK
- [ ] `lint:twig` OK
- [ ] `doctrine:schema:validate` OK
- [ ] `doctrine:schema:update --dump-sql` vide


## 21. Mailing nouvelle chanson publiée — à implémenter

- [ ] publication d'une nouvelle chanson crée un événement de notification
- [ ] aucune notification n'est envoyée avant la validation de la publication
- [ ] une modification d'une chanson déjà publiée ne renvoie pas le mailing
- [ ] un retry technique ne produit pas de doublon
- [ ] l'email contient titre, interprète et lien vers la chanson
- [ ] la locale du destinataire est respectée
- [ ] le désabonnement aux annonces de nouvelles chansons est respecté
- [ ] un échec mail ne remet pas la chanson en non-publiée
- [ ] comportement de dépublication/republication validé explicitement avant mise en production


## 22. Mailing nouvelle chanson publiée — R22

### Préférences

- [ ] profil : option nouvelles chansons cochée par défaut
- [ ] désactiver l'option persiste après reconnexion
- [ ] utilisateur inactif non destinataire
- [ ] e-mail non vérifié non destinataire

### Publication

- [ ] passage `Editing` -> `Published` déclenche le mailing
- [ ] passage `Imported` -> `Published` via Admin déclenche le mailing
- [ ] simple modification d'un morceau déjà publié ne déclenche rien
- [ ] dépublication seule ne déclenche rien
- [ ] un destinataire ayant déjà `sent_at` n'est pas envoyé deux fois
- [ ] erreur mail n'annule pas le statut Published
- [ ] erreur mail écrit `failed_at`
- [ ] erreur mail écrit `last_error`
- [ ] le message contient titre
- [ ] le message contient interprète
- [ ] le message contient lien absolu vers la chanson
- [ ] le message contient lien vers les préférences Profil
- [ ] locale FR respectée
- [ ] locale EN respectée

### Doctrine

- [ ] migration `Version20260925230000` exécutée
- [ ] colonne `users.notify_new_songs` présente
- [ ] table `song_publication_notifications` présente
- [ ] contrainte unique `(song_id, user_id)` présente
- [ ] `doctrine:schema:validate` OK
- [ ] `doctrine:schema:update --dump-sql` vide


## 23. Mailing asynchrone R22.1

- [ ] Publier une chanson répond immédiatement sans attendre les e-mails
- [ ] la publication crée une ligne `song_publication_mail_jobs`
- [ ] aucun e-mail n'est envoyé tant que le worker n'est pas lancé
- [ ] `php bin\console app:mailing:worker --once` traite un job
- [ ] le job terminé reçoit `completed_at`
- [ ] un worker continu traite automatiquement les jobs suivants
- [ ] deux workers ne peuvent pas réclamer simultanément le même job
- [ ] un claim abandonné depuis plus de 15 minutes peut être repris
- [ ] un échec libère le job avec `last_error`
- [ ] un échec planifie `next_attempt_at`
- [ ] le backoff évite une boucle de retry immédiate
- [ ] les destinataires déjà `sent_at` ne sont pas renvoyés lors d'un retry
- [ ] la publication reste `Published` même si le worker ou SMTP échoue


## 24. STEMS ONLY — R23

### Périmètre

- [ ] aucune parole produite
- [ ] aucun phonème produit
- [ ] aucun accord produit
- [ ] aucun beat / tempo produit
- [ ] aucune mesure produite
- [ ] aucun bloc / structure produit
- [ ] aucun MIDI produit
- [ ] aucun karaoké produit

### Génération

- [ ] bouton STEMS crée un job `kind=stems`
- [ ] la requête HTTP revient immédiatement
- [ ] worker `app:stems:worker` traite le job
- [ ] progression visible
- [ ] `vocals.wav` présent
- [ ] `lead_vocals.wav` présent
- [ ] `backing_vocals.wav` présent
- [ ] `drums.wav` présent
- [ ] `bass.wav` présent
- [ ] `guitar.wav` présent
- [ ] `piano.wav` présent
- [ ] `other.wav` présent
- [ ] manifeste `scope=stems_only`
- [ ] aucun changement automatique de `Song.status`

### Persistance

- [ ] rechargement de page conserve les STEMS
- [ ] redémarrage Symfony conserve les STEMS
- [ ] réanalyse produit un nouveau run
- [ ] version courante remplacée uniquement après réussite
- [ ] échec de réanalyse conserve l'ancienne version écoutable
- [ ] au maximum deux runs sont conservés

### Audio / sécurité

- [ ] lecteur individuel fonctionne pour chaque STEM
- [ ] routes STEM refusées aux Readers et visiteurs
- [ ] Éditeur propriétaire autorisé
- [ ] Admin autorisé
- [ ] autre Éditeur refusé

### Suppression

- [ ] suppression chanson supprime ses lignes Doctrine par cascade
- [ ] suppression chanson supprime aussi `var/storage/stems/song-{id}`
- [ ] changement de source audio n'utilise jamais les STEMS de l'ancien SHA-256

### Runtime

- [ ] FFmpeg disponible
- [ ] `bs-roformer-infer` disponible dans le Python STEM
- [ ] `melband-roformer-infer` disponible dans le Python STEM
- [ ] `BS_ROFORMER_MODELS_PATH` hors C:
- [ ] device CUDA configuré

## 30. Recette ChordsLab / Labs

### 30.1 Workflow et nomenclature

- [ ] le workflow affiche `Import`
- [ ] le workflow affiche `Analyse`
- [ ] le workflow affiche `Édition`
- [ ] l'ancien intitulé `STEMS` est remplacé par `StemsLab`
- [ ] le workflow affiche `ChordsLab`
- [ ] le workflow affiche `LyricsLab`
- [ ] le workflow affiche `Publication`
- [ ] l'ordre est strictement `Import → Analyse → Édition → StemsLab → ChordsLab → LyricsLab → Publication`
- [ ] aucun ancien libellé contradictoire ne subsiste dans le workflow principal

### 30.2 Timeline comme source de vérité

- [ ] le prompteur est construit depuis la timeline
- [ ] la chaîne compacte affichée n'est pas persistée comme source canonique
- [ ] le seek du player repositionne correctement la mesure active
- [ ] la lecture met à jour le beat/subdivision actif
- [ ] modifier la signature rythmique ne modifie pas les timestamps harmoniques
- [ ] modifier le capo ne modifie pas les timestamps harmoniques
- [ ] modifier le capo ne modifie pas les accords réels stockés

### 30.3 Prompteur harmonique

- [ ] les mesures sont affichées sous forme compacte
- [ ] le beat/subdivision courant est clairement surligné
- [ ] la mesure courante est identifiable sans ambiguïté
- [ ] le défilement suit la lecture sans sauts visuels excessifs
- [ ] un clic sur une mesure/position déplace le player au bon instant
- [ ] un accord prolongé sur la mesure suivante est réaffiché explicitement
- [ ] aucune mesure suivante n'est vide uniquement parce que l'accord précédent continue
- [ ] le rendu `[Em---]` est cohérent avec quatre positions en 4/4
- [ ] le rendu reste déterministe après rechargement

### 30.4 Diagramme courant

- [ ] option `Afficher le diagramme` présente
- [ ] option décochée masque complètement la zone diagramme
- [ ] option cochée affiche le diagramme
- [ ] le diagramme est placé directement au-dessus de l'accord courant
- [ ] le diagramme suit le changement d'accord pendant la lecture
- [ ] le diagramme suit immédiatement une modification manuelle d'accord
- [ ] le diagramme suit immédiatement le changement de capo

### 30.5 Édition d'accord en place

- [ ] un accord du prompteur peut être modifié en place
- [ ] la validation persiste la correction
- [ ] un rechargement conserve la correction
- [ ] la valeur issue de l'analyse reste disponible en arrière-plan
- [ ] la correction est stockée comme override et non comme destruction de l'original
- [ ] les autres mesures ne sont pas modifiées par erreur
- [ ] l'édition d'un accord ne décale pas la timeline

### 30.6 Reset des accords

- [ ] bouton `Réinitialiser les accords` présent
- [ ] confirmation demandée avant reset global
- [ ] reset supprime les overrides manuels
- [ ] reset restaure les accords issus de l'analyse
- [ ] reset ne modifie pas les timestamps
- [ ] reset ne modifie pas le capo
- [ ] reset ne modifie pas la signature rythmique
- [ ] reset ne modifie pas le niveau d'analyse sélectionné

### 30.7 Capo EZScore

- [ ] capo persistant
- [ ] changement de capo sans réanalyse
- [ ] changement visible immédiatement dans le prompteur
- [ ] changement visible immédiatement dans le diagramme
- [ ] tonalité réelle du morceau inchangée
- [ ] accord harmonique canonique inchangé
- [ ] audio inchangé
- [ ] exemple de référence : `Cm` avec capo 3 peut s'afficher comme forme `Am`
- [ ] retour capo 0 restaure la forme correspondant à l'accord réel

### 30.8 Tonalité

- [ ] le cartouche chanson affiche la tonalité réelle
- [ ] la tonalité reste visible en PC
- [ ] la tonalité reste lisible en tablette
- [ ] la tonalité reste lisible en smartphone
- [ ] changer le capo ne change pas la tonalité affichée
- [ ] aucune fonction de transposition réelle n'est présentée comme disponible tant qu'elle n'est pas implémentée

### 30.9 Signature rythmique

- [ ] la signature est persistante
- [ ] la liste contient `2/4`
- [ ] la liste contient `3/4`
- [ ] la liste contient `4/4`
- [ ] la liste contient `5/4`
- [ ] la liste contient `6/8`
- [ ] la liste contient `7/4`
- [ ] la liste contient `7/8`
- [ ] la liste contient `9/8`
- [ ] la liste contient `11/8`
- [ ] la liste contient `12/8`
- [ ] la liste supporte une signature non triviale telle que `13/16`
- [ ] stockage distinct numerator / denominator
- [ ] passage 4/4 → 2/4 recompose les mesures sans réanalyse
- [ ] `[Em---]` en 4/4 devient deux mesures cohérentes `[Em-] [Em-]` en 2/4 si les timestamps couvrent quatre pulsations
- [ ] passage vers 6/8 conserve six subdivisions de croche
- [ ] changement de signature ne crée aucun trou harmonique
- [ ] rechargement conserve la signature choisie

### 30.10 Niveau d'analyse harmonique

- [ ] choix `Débutant`
- [ ] choix `Intermédiaire`
- [ ] choix `Expert`
- [ ] choix persistant
- [ ] niveau Débutant simplifie effectivement les enrichissements
- [ ] niveau Intermédiaire conserve les accords usuels enrichis
- [ ] niveau Expert autorise une restitution plus détaillée
- [ ] changement de niveau ne se limite pas à masquer des suffixes d'accords
- [ ] si une réanalyse est nécessaire, l'interface l'indique clairement
- [ ] aucune réanalyse des STEMS n'est déclenchée inutilement pour un simple changement de niveau harmonique

### 30.11 Player partagé

- [ ] ChordsLab utilise le même moteur audio que StemsLab
- [ ] aucun second player audio concurrent n'est créé
- [ ] play synchronise le prompteur
- [ ] pause fige la position harmonique
- [ ] seek resynchronise immédiatement le prompteur
- [ ] changement de vitesse conserve la synchronisation
- [ ] sortie de page arrête proprement les médias en cours

### 30.12 Pistes et chaîne d'effets

- [ ] panneau `Pistes` replié par défaut
- [ ] panneau `Chaîne d'effets master` replié par défaut
- [ ] transport visible lorsque les panneaux sont repliés
- [ ] ouverture/fermeture n'interrompt pas la lecture
- [ ] ouverture/fermeture ne décale pas la timeline
- [ ] mixer conserve ses réglages persistés
- [ ] chaîne master conserve EQ / compression / limiteur / gain
- [ ] ChordsLab ne duplique pas la chaîne d'effets

### 30.13 Ergonomie PC

- [ ] aucune hauteur excessive par piste
- [ ] plusieurs mesures visibles simultanément
- [ ] prompteur prioritaire visuellement
- [ ] diagramme ancré au-dessus de l'accord actif
- [ ] réglages principaux accessibles sans ouvrir les panneaux secondaires
- [ ] aucun scroll horizontal global
- [ ] focus clavier visible sur les contrôles interactifs

### 30.14 Ergonomie tablette

- [ ] test paysage tablette
- [ ] test portrait tablette
- [ ] aucun scroll horizontal global
- [ ] contrôles Capo / Signature / Niveau restent accessibles
- [ ] sliders et boutons sont utilisables au doigt
- [ ] diagramme ne recouvre pas les mesures voisines
- [ ] panneaux repliables pleine largeur si nécessaire
- [ ] transport reste visible et utilisable

### 30.15 Ergonomie smartphone

- [ ] test largeur ~390 px
- [ ] test largeur ~360 px
- [ ] aucun contenu essentiel hors écran
- [ ] aucune largeur desktop forcée
- [ ] prompteur reste la zone principale
- [ ] mesure active reste visible pendant la lecture
- [ ] diagramme s'affiche au-dessus de l'accord actif
- [ ] Capo / Signature / Niveau peuvent s'empiler proprement
- [ ] Pistes et Effets s'ouvrent en accordéons pleine largeur
- [ ] play/pause/stop ont des cibles tactiles suffisantes
- [ ] édition d'accord reste utilisable au doigt
- [ ] confirmation de reset reste lisible et actionnable
- [ ] clavier virtuel ne masque pas définitivement l'accord en cours d'édition

### 30.16 Persistance

- [ ] capo persiste après reconnexion
- [ ] signature persiste après reconnexion
- [ ] niveau d'analyse persiste après reconnexion
- [ ] overrides d'accords persistent après reconnexion
- [ ] reset persiste après reconnexion
- [ ] tonalité canonique persiste
- [ ] les préférences d'ouverture des panneaux ne polluent pas les données éditoriales de la chanson

### 30.17 Non-régression

- [ ] StemsLab continue de lire les proxies Opus existants
- [ ] mixer R29 reste fonctionnel
- [ ] chaîne d'effets master R29 reste fonctionnelle
- [ ] aucune régénération des STEMS pour capo
- [ ] aucune régénération des STEMS pour signature rythmique
- [ ] aucune régression ACL
- [ ] aucune régression publication
- [ ] `php -l` OK
- [ ] `lint:yaml` OK
- [ ] `lint:twig` OK
- [ ] `doctrine:schema:validate` OK
- [ ] `doctrine:schema:update --dump-sql` vide

## 31. Recette R33.1 — accords simplifiés / prompteur centré / wake lock

- [ ] les STEMS harmoniques sont utilisés en priorité lorsqu’ils existent ;
- [ ] `drums` sert prioritairement à la grille de beats ;
- [ ] l’audio original reste un fallback ;
- [ ] en Intermédiaire, les `maj7` et enrichissements faibles sont réduits ;
- [ ] les changements isolés d’un beat sont fortement réduits ;
- [ ] l’accord courant vient se placer sous le diagramme pendant la lecture ;
- [ ] le centrage suit également un seek ;
- [ ] le comportement reste utilisable sur tablette et smartphone ;
- [ ] l’option de maintien écran est visible ;
- [ ] Play demande le wake lock si supporté ;
- [ ] Pause et Stop libèrent le wake lock ;
- [ ] quitter la page libère le wake lock ;
- [ ] le choix persiste sur le terminal ;
- [ ] l’absence de Wake Lock ne bloque jamais la lecture.


## 32. Recette R33.2 — job accords / progression / UX

- [ ] Réanalyser crée un job `chords` ;
- [ ] le job apparaît dans EZScore Analysis Worker ;
- [ ] le serveur web reste répondant pendant l’analyse ;
- [ ] progression Worker 0–100 % ;
- [ ] barre de progression ChordsLab ;
- [ ] rechargement unique après succès ;
- [ ] reset via modale EZScore ;
- [ ] Annuler ne modifie rien ;
- [ ] Confirmer supprime uniquement les overrides ;
- [ ] volume rapide pilote le master existant ;
- [ ] Débutant = majeur/mineur uniquement ;
- [ ] Intermédiaire plus simple qu’Expert ;
- [ ] Expert autorise les enrichissements ;
- [ ] phase downbeat appliquée seulement si suffisamment fiable ;
- [ ] levée représentée explicitement ;
- [ ] renderer respecte les beat_index canoniques ;
- [ ] aucune migration Doctrine supplémentaire.


## 33. Recette R34 — profils Débutant / Intermédiaire / Expert

- [ ] une seule analyse produit les trois profils ;
- [ ] les beats et mesures sont strictement identiques entre les trois profils ;
- [ ] changer de profil ne déclenche aucun nouveau job ;
- [ ] Débutant contient uniquement des majeurs/mineurs simples ;
- [ ] Intermédiaire peut contenir 7, m7, sus et dim ;
- [ ] Expert peut contenir maj7, 6, m6, add9 et autres enrichissements prévus ;
- [ ] Expert est globalement au moins aussi riche qu’Intermédiaire ;
- [ ] une édition Débutant n’altère pas Intermédiaire ;
- [ ] une édition Débutant n’altère pas Expert ;
- [ ] le reset ne touche que le profil affiché ;
- [ ] le profil affiché est persisté ;
- [ ] `Cmaj` est normalisé en `C` ;
- [ ] `Cmaj7` reste `Cmaj7` ;
- [ ] les slots ont une largeur stable pendant le défilement ;
- [ ] les accords longs restent lisibles sans symbole jazz imposé ;
- [ ] le libellé Volume reste accolé à son composant ;
- [ ] la progression est visuellement plus forte et pleine largeur ;
- [ ] aucun traitement n’est spécifique à un titre, artiste ou identifiant de chanson ;
- [ ] aucune migration Doctrine n’est requise.
