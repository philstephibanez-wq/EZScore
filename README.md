# EZScore R29 — shell produit, profil latéral et administration utilisateurs

R29 poursuit la séparation front-office / back-office et remplace la sidebar technique permanente par une présentation de type application musicale.

## Entête

L'entête affiche désormais :
- logo EZScore ;
- zone de recherche visuelle ;
- identité et rôle de l'utilisateur connecté.

L'objectif est de rapprocher l'ergonomie d'une application musicale moderne sans recopier l'interface d'un service tiers.

## Left panel / sidebar

Sur le Répertoire, le panneau gauche devient un panneau profil/navigation :
- avatar initial ;
- nom ;
- rôle ;
- Répertoire ;
- Mon profil ;
- Mes éditions pour editor/admin ;
- Importer pour editor/admin ;
- Utilisateurs & droits pour admin ;
- Déconnexion.

Pour un visiteur :
- Répertoire ;
- Connexion / inscription.

## Réglages techniques contextuels

Les informations GPU / CUDA / Demucs, le capodastre et les Réglages avancés ne sont plus affichés sur l'accueil.

Ils sont visibles uniquement :
- dans Import ;
- dans Chanson lorsque le morceau actif est en mode Édition.

En Vue, Répertoire et Compte, le panneau gauche reste orienté utilisateur/profil.

## Administration utilisateurs

L'administrateur peut :
- ajouter un utilisateur ;
- attribuer reader / editor / admin ;
- activer / désactiver ;
- réinitialiser le mot de passe ;
- supprimer un utilisateur et ses identités SSO liées.

Le dernier administrateur actif reste protégé contre rétrogradation, désactivation ou suppression.

## Récupération d'un administrateur après restauration BDD

Si une BDD restaurée contient des utilisateurs mais plus aucun rôle admin, définir explicitement :

```powershell
$env:EZSCORE_ADMIN_EMAIL="votre-email"
$env:EZSCORE_ADMIN_PASSWORD="votre-mot-de-passe"
$env:EZSCORE_ADMIN_NAME="Steve"
```

puis relancer EZScore.

R29 détecte désormais un compte existant avec cet e-mail et le promeut en admin actif au lieu d'essayer de créer un doublon.

## Google / compte local

Les identités Google continuent d'être liées par e-mail vérifié au compte EZScore existant. Les droits restent stockés dans EZScore : Google authentifie l'identité, il ne décide jamais du rôle.

## Responsive

Le header se replie sur tablette. Les boutons du panneau profil restent tactiles et le comportement responsive existant reste actif sur smartphone.

## Fichiers R29

Le livrable contient uniquement :
- `EZScore.py`
- `readme.md`
- `ezscore/ui/app_shell.py`
- `ezscore/auth/storage.py`
- `ezscore/auth/ui.py`
