# EZScore R30 — paroles par blocs, éditeurs, login et avatars

R30 part du dernier push utilisateur `e0f937f` (FIX8).

## Paroles : déplacement entre blocs

La validation des paroles devient atomique pour l'ensemble des blocs visibles.

Quand un vers est coupé d'un bloc puis collé dans le suivant :
- l'ancien bloc est enregistré avec son nouveau contenu ;
- le bloc cible est enregistré avec son nouveau contenu ;
- les anciennes corrections de découpage sont supprimées dans la même transaction ;
- un bloc peut être explicitement vidé : il ne reprend pas automatiquement le texte Whisper au rerun ;
- les retours à la ligne saisis restent conservés.

`Blocs > Édition` reste la source canonique des paroles.

## Attribution réelle de l'éditeur

Une chanson peut maintenant être assignée à un utilisateur EZScore réel.

La persistance conserve :
- `user_id` de l'éditeur assigné ;
- nom affiché au moment de l'attribution comme snapshot lisible.

En mode Édition :
- un admin peut sélectionner un utilisateur actif de rôle `editor` ou `admin` ;
- un non-admin voit l'éditeur assigné sans pouvoir le changer.

Le champ historique `songs.editor` reste alimenté pour compatibilité avec le répertoire, les versions et l'impression.

## Nom affiché = login

Il n'y a pas de champ username séparé.

Le `display_name` :
- est obligatoire ;
- est unique sans distinction de casse ;
- est le nom visible ;
- peut être utilisé pour la connexion locale à la place de l'e-mail.

La page de connexion accepte donc : **Nom affiché ou e-mail**.

Les comptes existants dont le nom est vide ou dupliqué sont normalisés automatiquement lors de la migration.

## Photo de profil Google / SSO

Le claim OIDC `picture` est récupéré lors du login Google/SSO et mémorisé avec l'identité liée.

Le profil permet :
- d'afficher la photo Google/SSO ;
- d'importer une photo locale JPG/PNG/WebP ;
- de remplacer la photo ;
- de revenir à la photo du fournisseur.

Une photo locale a priorité sur la photo distante.

Le left panel utilise également l'avatar du compte lorsqu'il existe.

## Administration utilisateurs

L'admin peut toujours :
- créer / supprimer ;
- modifier rôle et état actif ;
- réinitialiser un mot de passe ;
- modifier le nom affiché / login.

La fiche utilisateur affiche aussi le nombre de morceaux actuellement assignés.

## Fichiers du livrable

- `EZScore.py`
- `readme.md`
- `ezscore/persistence.py`
- `ezscore/auth/storage.py`
- `ezscore/auth/session.py`
- `ezscore/auth/ui.py`
- `ezscore/ui/app_shell.py`
