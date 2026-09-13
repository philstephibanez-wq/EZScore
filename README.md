# EZScore R22 — pochette, ruban continu et accords guitare

R22 transforme le player d’édition en prévisualisation du futur player de lecture, tout en poursuivant la modularisation de l’application.

## Back-office / front-office

Le mode **Édition** est le back-office de EZScore : analyse, correction, structure, métadonnées, voicings, contrôle MP3 + MIDI, validation et publication.

Le futur **front-office Lecture** utilisera le même principe visuel et le même transport MP3, mais sans synthèse MIDI. Il pourra être public, authentifié ou réservé à des utilisateurs / abonnés selon les permissions. Admin et éditeur accèdent au back-office ; lecteur et anonyme restent côté front selon leurs droits.

## Ruban accords + paroles

Le player d’édition intègre maintenant un bandeau temporel continu :

- déplacement automatique de droite vers gauche ;
- repère central = instant courant ;
- passé visible à gauche ;
- accords et paroles à venir visibles à droite pour anticipation ;
- pas de pagination pendant la lecture ;
- pas de scroll horizontal utilisateur ;
- synchronisation sur `audio.currentTime` du MP3 maître ;
- comportement responsive tablette / smartphone.

Le ruban est isolé dans `ezscore/player/ribbon.py`.

## Pochette

La pochette est une donnée du morceau déjà persistée par EZScore et visible dans le répertoire / back-office. R22 ajoute `ezscore/player/cover.py` pour fournir cette même pochette au composant player.

Le player d’édition affiche maintenant :

- la pochette si elle existe ;
- le titre ;
- l’artiste ;
- puis le transport MP3 + MIDI et le ruban synchronisé.

Cette identité visuelle sera réutilisée côté front-office.

## Diagrammes guitare optionnels

Nouveau sous-système `ezscore/guitar/` :

- symbole harmonique et voicing séparés ;
- positions ouvertes, barrées et simplifiées ;
- rendu SVG vectoriel responsive ;
- cordes ouvertes / étouffées ;
- numéros de doigts ;
- représentation des barrés ;
- choix persistant par morceau et par symbole d’accord ;
- activation / désactivation persistante de l’affichage des diagrammes.

En mode Édition, l’expander **Diagrammes guitare (optionnel)** permet de choisir la position voulue pour chaque accord reconnu du morceau. Exemple : un `Am` reste musicalement `Am`, mais peut être affiché / joué visuellement en position ouverte ou barrée case V.

Si l’option est active, le diagramme sélectionné apparaît au centre du bandeau pendant la lecture.

Les choix sont enregistrés dans SQLite par `ezscore/guitar/storage.py` sans modifier la timeline harmonique ni les corrections de grille.

## Catalogue initial de voicings

R22 initialise les accords courants suivants avec plusieurs positions lorsque pertinent :

- A / Am
- C
- D / Dm
- E / Em
- F
- G

Le catalogue est volontairement modulaire et extensible. Les accords non encore décrits continuent à fonctionner normalement dans la grille et le player ; ils sont simplement affichés sans diagramme jusqu’à ajout d’un voicing.

## Responsive

Le contrat responsive R21 reste appliqué :

- desktop : largeur complète et anticipation maximale ;
- tablette : contrôles adaptés au tactile ;
- smartphone : bandeau compact, typographies réduites et diagramme redimensionné ;
- aucune fonction critique ne dépend du survol souris ;
- aucune barre de scroll horizontale ne doit être nécessaire pour suivre la lecture.

## Modularisation R22

Fichiers ajoutés :

- `ezscore/player/ribbon.py`
- `ezscore/player/cover.py`
- `ezscore/guitar/voicings.py`
- `ezscore/guitar/storage.py`

Fichiers adaptés :

- `EZScore.py`
- `ezscore/backoffice/player.py`
- `ezscore/midi/web_player.py`
- `ezscore/player/__init__.py`
- `ezscore/guitar/__init__.py`

Principe maintenu : **`EZScore.py` orchestre ; les nouvelles responsabilités vont dans des modules dédiés.**

## Authentification / accès — contrat conservé

La fondation R21 reste en place :

- `admin` : tous les droits ;
- `editor` : import, analyse, édition, validation et publication ;
- `reader` : lecture autorisée ;
- `anonymous` : uniquement le contenu explicitement accessible sans compte.

Le front pourra être protégé par authentification e-mail / OAuth-OIDC (Google et fournisseurs sociaux) et, ultérieurement, par des droits liés à une offre payante. Authentification, autorisation et facturation resteront séparées.

## Livrable R22

Le ZIP contient uniquement les fichiers modifiés ou ajoutés par R22 :

- `EZScore.py`
- `readme.md`
- `ezscore/backoffice/player.py`
- `ezscore/midi/web_player.py`
- `ezscore/player/__init__.py`
- `ezscore/player/ribbon.py`
- `ezscore/player/cover.py`
- `ezscore/guitar/__init__.py`
- `ezscore/guitar/voicings.py`
- `ezscore/guitar/storage.py`

Dézipper dans `H:\EZScore` en conservant l’arborescence.
