# EZScore_v1 — PLAN DE RECETTE FONCTIONNELLE AVANT RÉINTÉGRATION PYTHON

Objectif :
Valider l’ensemble du socle Symfony / métier / droits / persistance / UI avant de reconnecter les analyseurs Python via REST.

Convention :
[ ] Non testé
[x] OK
[!] KO
[~] À revoir

Pour chaque KO, noter :
- Profil utilisé
- URL
- Action
- Résultat obtenu
- Résultat attendu
- Capture éventuelle
- Extrait de log Monolog éventuel


============================================================
1. ENVIRONNEMENT / DÉMARRAGE
============================================================

[ ] Le site démarre sans erreur PHP
[ ] Le cache Symfony se vide correctement
[ ] Le profiler fonctionne en environnement dev
[ ] Monolog crée bien var/log/dev.log
[ ] Aucune erreur bloquante au chargement de la page d’accueil
[ ] Les routes Symfony sont toutes disponibles
[ ] Les traductions YAML passent lint:yaml
[ ] Les templates passent lint:twig
[ ] Doctrine mapping OK
[ ] Doctrine schema synchronisé
[ ] doctrine:schema:update --dump-sql ne propose aucun SQL

Commandes de contrôle :

php bin\console lint:yaml translations
php bin\console lint:twig templates
php bin\console debug:router
php bin\console doctrine:schema:validate
php bin\console doctrine:schema:update --dump-sql


============================================================
2. PAGE D’ACCUEIL / RÉPERTOIRE PUBLIC
============================================================

[ ] La page d’accueil est bien le Répertoire
[ ] Le Répertoire est accessible sans connexion
[ ] Le header public est correctement affiché
[ ] Le bouton Connexion est visible
[ ] Le bouton Inscription est visible
[ ] Le bandeau présentant les avantages de l’inscription est visible
[ ] Le texte indique clairement que l’inscription est gratuite
[ ] Le Répertoire public n’affiche que les chansons publiées
[ ] Les chansons Importées ne sont pas visibles publiquement
[ ] Les chansons Analysées non publiées ne sont pas visibles publiquement
[ ] Les chansons En édition ne sont pas visibles publiquement
[ ] Une chanson dépubliée disparaît immédiatement du Répertoire public
[ ] Une chanson publiée apparaît immédiatement dans le Répertoire public


============================================================
3. LANGUES / I18N
============================================================

[ ] La listbox de langue est visible
[ ] Le drapeau français est affiché
[ ] Le drapeau anglais est affiché
[ ] Le libellé Français est correct
[ ] Le libellé English est correct
[ ] Passage FR → EN fonctionnel
[ ] Passage EN → FR fonctionnel
[ ] La page courante est conservée après changement de langue
[ ] Le changement de langue fonctionne depuis le Répertoire
[ ] Le changement de langue fonctionne depuis une chanson
[ ] Le changement de langue fonctionne depuis Import
[ ] Le changement de langue fonctionne depuis Édition
[ ] Le changement de langue fonctionne depuis Groupes
[ ] Le changement de langue fonctionne depuis Playlists
[ ] Le changement de langue fonctionne depuis Profil
[ ] Aucune clé brute du type catalog.xxx n’apparaît
[ ] Aucune clé brute du type song.xxx n’apparaît
[ ] Aucun texte anglais résiduel dans l’interface FR
[ ] Aucun texte français résiduel dans l’interface EN


============================================================
4. RÉPERTOIRE — AFFICHAGE
============================================================

[ ] Les vignettes sont suffisamment compactes
[ ] Plusieurs chansons tiennent à l’écran sans gaspillage vertical
[ ] Les pochettes s’affichent correctement
[ ] Placeholder correct si aucune pochette
[ ] Le titre est lisible
[ ] L’interprète est lisible
[ ] Le statut est visible pour Admin/Éditeur
[ ] Le nom de l’éditeur est visible quand prévu
[ ] Le commentaire éditeur est visible quand prévu
[ ] La notation est visible
[ ] Les titres longs ne cassent pas la mise en page
[ ] Les noms d’interprètes longs ne cassent pas la mise en page
[ ] Les caractères accentués sont corrects
[ ] Les apostrophes sont correctes
[ ] Les guillemets sont corrects
[ ] Les caractères spéciaux sont corrects


============================================================
5. RÉPERTOIRE — TRI
============================================================

[ ] Affichage simple "Trier par: Titre Interprète"
[ ] Titre est sélectionné par défaut
[ ] Tri par Titre croissant fonctionnel
[ ] Tri par Interprète croissant fonctionnel
[ ] Le choix actif est visuellement identifiable
[ ] Le tri est insensible à la casse
[ ] Les accents ne provoquent pas d’ordre incohérent majeur
[ ] En tri Titre, le second critère est l’interprète
[ ] En tri Interprète, le second critère est le titre


============================================================
6. RÉPERTOIRE — FILTRE ALPHABÉTIQUE
============================================================

[ ] Barre Tous A B C ... Z visible
[ ] "Tous" affiche toutes les chansons accessibles
[ ] A filtre correctement
[ ] B filtre correctement
[ ] Tester au moins 5 lettres différentes
[ ] Une lettre sans résultat affiche proprement "aucun résultat"
[ ] En tri Titre, la lettre filtre sur le titre
[ ] En tri Interprète, la lettre filtre sur l’interprète
[ ] Changer de tri conserve correctement la logique du filtre
[ ] Retour à Tous fonctionne


============================================================
7. RÉPERTOIRE — RECHERCHE
============================================================

[ ] Recherche par titre
[ ] Recherche par interprète
[ ] Recherche par auteur/parolier
[ ] Recherche par compositeur
[ ] Recherche par nom d’éditeur si prévu
[ ] Recherche partielle
[ ] Recherche insensible à la casse
[ ] Recherche avec accents
[ ] Recherche sans résultat
[ ] Effacer la recherche fonctionne
[ ] Recherche + tri Titre
[ ] Recherche + tri Interprète
[ ] Recherche + lettre alphabétique
[ ] Recherche + tri + lettre simultanément


============================================================
8. INSCRIPTION UTILISATEUR
============================================================

[ ] Inscription accessible publiquement
[ ] Nom obligatoire
[ ] E-mail obligatoire
[ ] E-mail invalide refusé
[ ] E-mail déjà existant refusé
[ ] Mot de passe trop court refusé
[ ] Confirmation différente refusée
[ ] Création utilisateur réussie
[ ] E-mail d’activation envoyé si SMTP configuré
[ ] Activation par lien fonctionne
[ ] Lien d’activation invalide refusé
[ ] Lien expiré géré correctement
[ ] Renvoi de mail d’activation fonctionne


============================================================
9. CONNEXION / SESSION
============================================================

[ ] Connexion locale valide
[ ] Mauvais mot de passe refusé
[ ] Utilisateur désactivé refusé
[ ] Déconnexion fonctionnelle
[ ] Case "Se souvenir de moi" visible
[ ] "Se souvenir de moi" fonctionne après fermeture/réouverture navigateur
[ ] Connexion Google fonctionne si configurée
[ ] Avatar Google récupéré si disponible
[ ] Nom affiché correct après connexion
[ ] Rôle utilisateur affiché correctement


============================================================
10. PROFIL LECTEUR
============================================================

[ ] Lecteur voit uniquement les chansons publiées
[ ] Lecteur ne voit aucune chanson privée
[ ] Lecteur peut ouvrir une chanson publiée
[ ] Lecteur peut écouter l’audio complet
[ ] Lecteur peut utiliser le karaoké complet
[ ] Lecteur ne voit pas Import
[ ] Lecteur ne peut pas accéder à /import par URL directe
[ ] Lecteur ne voit pas Modifier
[ ] Lecteur ne peut pas accéder à /song/{id}/edit par URL directe
[ ] Lecteur ne peut pas publier/dépublier
[ ] Lecteur peut noter une chanson
[ ] Lecteur peut créer un groupe
[ ] Lecteur peut créer une playlist


============================================================
11. PUBLIC NON CONNECTÉ
============================================================

[ ] Public voit uniquement les chansons publiées
[ ] Public ne peut pas écouter l’audio complet
[ ] Public a uniquement la démo karaoké prévue
[ ] Durée de démo conforme
[ ] Public ne peut pas noter
[ ] Public ne peut pas créer de playlist
[ ] Public ne peut pas créer de groupe
[ ] Public ne peut pas importer
[ ] Public ne peut pas éditer
[ ] Accès direct à une chanson privée refusé
[ ] Accès direct à /import refusé
[ ] Accès direct à /song/{id}/edit refusé


============================================================
12. PROFIL ÉDITEUR — VISIBILITÉ
============================================================

[ ] Éditeur voit ses propres chansons quel que soit leur statut
[ ] Éditeur voit les chansons publiées des autres
[ ] Éditeur ne voit pas les chansons privées des autres éditeurs
[ ] Éditeur peut ouvrir ses chansons
[ ] Éditeur peut ouvrir les chansons publiées des autres
[ ] Éditeur ne peut pas ouvrir une chanson privée d’un autre par URL directe
[ ] Éditeur peut éditer ses chansons
[ ] Éditeur ne peut pas éditer les chansons des autres
[ ] Éditeur ne peut pas changer l’éditeur d’une chanson
[ ] Éditeur peut publier ses chansons
[ ] Éditeur peut dépublier ses chansons


============================================================
13. PROFIL ADMIN
============================================================

[ ] Admin voit toutes les chansons
[ ] Admin voit tous les statuts
[ ] Admin peut ouvrir toutes les chansons
[ ] Admin peut éditer toutes les chansons
[ ] Admin peut publier toutes les chansons
[ ] Admin peut dépublier toutes les chansons
[ ] Admin peut changer l’éditeur d’une chanson
[ ] Admin peut remplacer n’importe quel audio
[ ] Admin voit tous les utilisateurs
[ ] Admin peut gérer tous les groupes
[ ] Admin peut gérer toutes les playlists


============================================================
14. IMPORT — ACCÈS
============================================================

[ ] Bouton Import visible Admin
[ ] Bouton Import visible Éditeur
[ ] Bouton Import absent Lecteur
[ ] Bouton Import absent Public
[ ] Route /fr/import accessible Admin
[ ] Route /fr/import accessible Éditeur
[ ] Route /fr/import refusée Lecteur
[ ] Route /fr/import refusée Public


============================================================
15. IMPORT — AUDIO
============================================================

[ ] MP3 accepté
[ ] WAV accepté
[ ] FLAC accepté
[ ] M4A accepté
[ ] OGG accepté
[ ] AAC accepté
[ ] Format non autorisé refusé
[ ] Fichier vide refusé
[ ] Fichier trop volumineux géré proprement
[ ] Nom de fichier très long accepté ou géré proprement
[ ] Nom avec accents
[ ] Nom avec espaces
[ ] Nom avec apostrophe
[ ] Nom avec caractères spéciaux raisonnables
[ ] SHA-256 calculé
[ ] Audio stocké sous var/storage/audio
[ ] Audio non accessible publiquement directement
[ ] Double import du même fichier testé


============================================================
16. IMPORT — PRÉ-ÉCOUTE AUDIO
============================================================

[ ] Le lecteur apparaît après sélection du fichier
[ ] Le nom du fichier est affiché
[ ] Lecture fonctionne
[ ] Pause fonctionne
[ ] Curseur de lecture fonctionne
[ ] Volume navigateur fonctionne
[ ] Changement de fichier remplace correctement la pré-écoute
[ ] Le précédent object URL est libéré
[ ] Pré-écoute MP3
[ ] Pré-écoute WAV
[ ] Pré-écoute FLAC si navigateur compatible
[ ] Pré-écoute M4A si navigateur compatible
[ ] La pré-écoute n’envoie pas le fichier au serveur
[ ] Le fichier n’est importé qu’après validation du formulaire


============================================================
17. IMPORT — FICHE CHANSON
============================================================

[ ] Titre obligatoire
[ ] Interprète obligatoire
[ ] Auteur facultatif
[ ] Compositeur facultatif
[ ] Pochette facultative
[ ] Éditeur correct
[ ] Statut correct
[ ] Signature correcte
[ ] Capo correct
[ ] Strumming principal
[ ] Strumming alternatif
[ ] Commentaire éditeur
[ ] Champs persistés après import


============================================================
18. SIGNATURE RYTHMIQUE
============================================================

[ ] Auto disponible
[ ] Auto sélectionné par défaut
[ ] 2/4 disponible
[ ] 3/4 disponible
[ ] 4/4 disponible
[ ] 5/4 disponible
[ ] 6/8 disponible
[ ] 9/8 disponible
[ ] 12/8 disponible
[ ] Valeur sélectionnée persistée
[ ] Auto affiché correctement dans la fiche
[ ] Aucune autre valeur invalide acceptée


============================================================
19. CAPO / STRUMMING
============================================================

[ ] Capo 0
[ ] Capo 1
[ ] Tester un capo intermédiaire
[ ] Capo 11
[ ] Valeur > 11 refusée
[ ] Valeur négative refusée
[ ] Strumming principal persiste
[ ] Strumming alternatif persiste
[ ] Strumming vide accepté


============================================================
20. POCHETTES
============================================================

[ ] JPEG accepté
[ ] PNG accepté
[ ] WEBP accepté
[ ] Format invalide refusé
[ ] Pochette visible dans le Répertoire
[ ] Pochette visible dans la fiche
[ ] Remplacement de pochette fonctionne
[ ] Laisser vide en édition conserve l’ancienne pochette
[ ] Chanson sans pochette affiche le placeholder


============================================================
21. STATUTS CHANSON
============================================================

[ ] Importée
[ ] Analysée
[ ] En édition
[ ] Publiée
[ ] "Analysée" non sélectionnable manuellement à l’import
[ ] "Analysée" non attribuable manuellement si non déjà analysée
[ ] Publication met published_at
[ ] Dépublication retire published_at ou état cohérent
[ ] Remplacement audio repasse la chanson à Importée
[ ] Chanson Importée non visible publiquement
[ ] Chanson En édition non visible publiquement
[ ] Chanson Publiée visible publiquement


============================================================
22. WORKSPACE CHANSON
============================================================

[ ] La fiche chanson s’affiche
[ ] Titre correct
[ ] Interprète correct
[ ] Auteur correct
[ ] Compositeur correct
[ ] Éditeur correct
[ ] Signature correcte
[ ] Capo correct
[ ] Strummings corrects
[ ] Commentaire visible seulement aux personnes autorisées
[ ] Statut visible
[ ] Note moyenne visible
[ ] Bouton Modifier visible uniquement si autorisé
[ ] Bouton Publier/Dépublier visible uniquement si autorisé


============================================================
23. ÉDITION CHANSON
============================================================

[ ] Route /song/{id}/edit accessible Admin
[ ] Route accessible à l’éditeur propriétaire
[ ] Route refusée aux autres éditeurs
[ ] Route refusée au Lecteur
[ ] Route refusée au Public
[ ] Modification titre
[ ] Modification interprète
[ ] Modification auteur
[ ] Modification compositeur
[ ] Modification pochette
[ ] Modification signature
[ ] Modification capo
[ ] Modification strumming principal
[ ] Modification strumming alternatif
[ ] Modification commentaire
[ ] Modification statut
[ ] Modification éditeur par Admin
[ ] Sauvegarde fonctionne
[ ] Retour au workspace fonctionne
[ ] Réouverture montre les nouvelles valeurs
[ ] Aucune modification ne nécessite de réimport audio


============================================================
24. REMPLACEMENT AUDIO
============================================================

[ ] Bouton Remplacer audio visible uniquement aux personnes autorisées
[ ] MP3 de remplacement
[ ] WAV de remplacement
[ ] FLAC de remplacement
[ ] M4A de remplacement
[ ] OGG de remplacement
[ ] AAC de remplacement
[ ] Nouveau fichier actif après remplacement
[ ] Nouveau SHA-256 calculé
[ ] Nom original mis à jour
[ ] Taille mise à jour
[ ] MIME mis à jour
[ ] imported_at mis à jour
[ ] Statut repasse à Importée
[ ] Ancienne chanson conserve le même ID
[ ] Notes conservées
[ ] Playlists conservées
[ ] Groupes conservés
[ ] Métadonnées conservées
[ ] Ancien fichier non supprimé immédiatement
[ ] Historique écrit dans var/storage/audio/history/song-{id}.jsonl


============================================================
25. NOTATION
============================================================

[ ] Note 1 étoile
[ ] Note 2 étoiles
[ ] Note 3 étoiles
[ ] Note 4 étoiles
[ ] Note 5 étoiles
[ ] Modification d’une note existante
[ ] Une seule note par user/chanson
[ ] Suppression de note
[ ] Moyenne recalculée
[ ] Nombre de notes recalculé
[ ] Note persistante après reconnexion
[ ] Public ne peut pas noter
[ ] Édition chanson ne supprime pas les notes
[ ] Remplacement audio ne supprime pas les notes


============================================================
26. GROUPES — CRÉATION
============================================================

[ ] Lecteur connecté peut créer un groupe
[ ] Éditeur peut créer un groupe
[ ] Admin peut créer un groupe
[ ] Public ne peut pas créer un groupe
[ ] Créateur devient propriétaire / administrateur du groupe
[ ] Nom obligatoire
[ ] Description facultative
[ ] Groupe persistant après reconnexion


============================================================
27. GROUPES — MEMBRES
============================================================

[ ] Ajouter un membre existant
[ ] Utilisateur inexistant refusé
[ ] Retirer un membre
[ ] Rôle Propriétaire
[ ] Rôle Gestionnaire
[ ] Rôle Membre
[ ] Changement de rôle
[ ] Délégation à un Gestionnaire
[ ] Membre simple ne peut pas administrer
[ ] Gestionnaire peut effectuer uniquement les opérations prévues
[ ] Propriétaire peut tout gérer dans son groupe
[ ] Admin global peut tout gérer


============================================================
28. PLAYLISTS PERSONNELLES
============================================================

[ ] Création playlist personnelle
[ ] Modification playlist personnelle
[ ] Suppression playlist personnelle
[ ] Ajout chanson
[ ] Retrait chanson
[ ] Playlist privée
[ ] Playlist publique si prévu
[ ] Persistance après reconnexion
[ ] Autre utilisateur ne peut pas modifier la playlist


============================================================
29. PLAYLISTS DE GROUPE
============================================================

[ ] Création playlist de groupe
[ ] Tous les membres héritent de la playlist du groupe
[ ] Propriétaire peut modifier
[ ] Gestionnaire délégué peut modifier
[ ] Membre simple ne peut pas modifier
[ ] Ajout chanson dans playlist
[ ] Retrait chanson
[ ] Suppression playlist
[ ] Retirer un utilisateur du groupe retire son accès
[ ] Admin global peut tout gérer


============================================================
30. DÉLÉGATION
============================================================

[ ] Propriétaire de groupe peut déléguer des droits
[ ] Délégation playlist fonctionne
[ ] Délégation gestion membres fonctionne si prévue
[ ] Délégation chanson fonctionne si prévue
[ ] Un droit non délégué reste interdit
[ ] Retrait de délégation prend effet immédiatement
[ ] Un membre simple ne peut pas s’auto-promouvoir


============================================================
31. ADMINISTRATION UTILISATEURS
============================================================

[ ] Liste utilisateurs
[ ] Création utilisateur
[ ] Modification utilisateur
[ ] Changement rôle Lecteur
[ ] Changement rôle Éditeur
[ ] Changement rôle Admin
[ ] Activation/désactivation
[ ] Suppression selon règles
[ ] Admin ne peut pas supprimer son propre compte si interdit
[ ] Dernier admin actif protégé
[ ] Utilisateur ayant historique d’analyse protégé selon règle


============================================================
32. SÉCURITÉ — URL DIRECTES
============================================================

[ ] Lecteur → /import refusé
[ ] Lecteur → /song/{id}/edit refusé
[ ] Public → /import refusé
[ ] Public → /song/{id}/edit refusé
[ ] Éditeur A → édition chanson Éditeur B refusée
[ ] Éditeur A → audio replace chanson Éditeur B refusé
[ ] Lecteur → publication refusée
[ ] Public → publication refusée
[ ] Utilisateur non membre → gestion groupe refusée
[ ] Utilisateur non autorisé → playlist privée refusée


============================================================
33. MONOLOG / DIAGNOSTIC
============================================================

[ ] var/log/dev.log existe
[ ] Erreur volontaire correctement loggée
[ ] Erreur Import correctement loggée
[ ] Erreur remplacement audio correctement loggée
[ ] Les logs donnent classe d’exception
[ ] Les logs donnent message
[ ] Les logs donnent fichier
[ ] Les logs donnent ligne
[ ] Les logs ne sont pas versionnés Git
[ ] var/log est bien ignoré par Git


============================================================
34. STOCKAGE FICHIERS
============================================================

[ ] var/storage/audio existe après premier import réussi
[ ] Les audios sont hors public/
[ ] Les noms stockés sont basés sur SHA-256
[ ] Les extensions sont conservées
[ ] Les pochettes sont sous public/uploads/covers
[ ] Les audios ne sont pas poussés dans Git
[ ] L’historique audio n’est pas poussé dans Git
[ ] Les logs ne sont pas poussés dans Git


============================================================
35. PERSISTANCE
============================================================

[ ] Redémarrer serveur PHP
[ ] Chansons toujours présentes
[ ] Utilisateurs toujours présents
[ ] Groupes toujours présents
[ ] Playlists toujours présentes
[ ] Notes toujours présentes
[ ] Pochettes toujours présentes
[ ] Audios toujours présents
[ ] Statuts toujours corrects
[ ] Commentaires toujours présents
[ ] Préférence de langue toujours correcte


============================================================
36. TEST VOLUME
============================================================

[ ] Importer au moins 10 chansons
[ ] Importer au moins 20 chansons
[ ] Tester 30–50 chansons si possible
[ ] Plusieurs artistes différents
[ ] Plusieurs titres commençant par la même lettre
[ ] Plusieurs titres identiques par artistes différents
[ ] Plusieurs chansons d’un même artiste
[ ] Mélange Publiée / Importée / En édition
[ ] Mélange plusieurs éditeurs
[ ] Vérifier ergonomie du Répertoire avec volume réel


============================================================
37. TESTS FORMAT AUDIO
============================================================

[ ] MP3 court
[ ] MP3 long
[ ] MP3 gros fichier
[ ] WAV
[ ] FLAC
[ ] M4A
[ ] OGG
[ ] AAC
[ ] Fichier extension valide mais contenu invalide
[ ] Fichier audio corrompu
[ ] Pré-écoute navigateur pour chaque format compatible


============================================================
38. TESTS DONNÉES EXOTIQUES
============================================================

[ ] Titre avec apostrophe
[ ] Titre avec accents
[ ] Titre avec tiret
[ ] Titre avec parenthèses
[ ] Titre très long
[ ] Artiste avec accents
[ ] Auteur avec caractères spéciaux
[ ] Commentaire long
[ ] Nom fichier Unicode
[ ] Pochette avec nom Unicode


============================================================
39. DOCTRINE APRÈS RECETTE
============================================================

[ ] php bin\console doctrine:schema:validate

Résultat attendu :
[ ] Mapping OK
[ ] Database schema in sync

[ ] php bin\console doctrine:schema:update --dump-sql

Résultat attendu :
[ ] Aucun SQL proposé


============================================================
40. GIT AVANT VALIDATION
============================================================

[ ] git status propre ou modifications comprises
[ ] Aucun var/log suivi
[ ] Aucun var/cache suivi
[ ] Aucun var/storage/audio suivi
[ ] Aucun fichier SQLite runtime suivi si non souhaité
[ ] migrations/ conservé
[ ] src/ versionné
[ ] templates/ versionné
[ ] config/ versionné
[ ] public/assets/ versionné


============================================================
41. CRITÈRES DE FIN DE RECETTE SYMFONY
============================================================

[ ] Aucun bug bloquant
[ ] Aucun problème de droits connu
[ ] Aucun problème de visibilité connu
[ ] Aucun problème de persistance connu
[ ] Aucun problème Doctrine connu
[ ] Aucun problème i18n connu
[ ] Aucun problème d’import audio connu
[ ] Aucun problème d’édition chanson connu
[ ] Aucun problème Groupes / Playlists connu
[ ] Répertoire suffisamment ergonomique avec plusieurs dizaines de chansons
[ ] Logs exploitables
[ ] Base considérée stable pour branchement de l’analyse Python REST


============================================================
42. ANOMALIES TROUVÉES
============================================================

[ ] Anomalie 01 :
    Profil :
    URL :
    Action :
    Résultat obtenu :
    Résultat attendu :
    Log :
    Capture :

[ ] Anomalie 02 :
    Profil :
    URL :
    Action :
    Résultat obtenu :
    Résultat attendu :
    Log :
    Capture :

[ ] Anomalie 03 :
    Profil :
    URL :
    Action :
    Résultat obtenu :
    Résultat attendu :
    Log :
    Capture :

[ ] Anomalie 04 :
    Profil :
    URL :
    Action :
    Résultat obtenu :
    Résultat attendu :
    Log :
    Capture :

[ ] Anomalie 05 :
    Profil :
    URL :
    Action :
    Résultat obtenu :
    Résultat attendu :
    Log :
    Capture :


============================================================
43. VALIDATION FINALE
============================================================

[ ] RECETTE VALIDÉE
[ ] RECETTE VALIDÉE AVEC RÉSERVES
[ ] RECETTE REFUSÉE

Date :
Version / commit :
Testeur :
Commentaires :