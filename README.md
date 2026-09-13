# EZScore R26 — login, rôles et permissions serveur

R26 introduit le premier socle d'authentification et d'autorisation d'EZScore, avec une interface pensée dès maintenant pour ordinateur, tablette et smartphone.

## Rôles

Quatre rôles existent :

- `anonymous` : visiteur non connecté, accès uniquement aux contenus publiés ;
- `reader` : lecture front-office, y compris contenus privés selon l'autorisation du compte ;
- `editor` : lecture + import + analyse + modification + validation + publication + suppression ;
- `admin` : tous les droits, y compris gestion des utilisateurs.

Les permissions sont contrôlées côté serveur. Le fait de masquer un bouton n'est pas considéré comme une protection.

## Authentification locale

R26 fournit un premier login e-mail / mot de passe.

Les mots de passe ne sont jamais stockés en clair. Ils sont dérivés avec :

- PBKDF2-HMAC-SHA256 ;
- sel aléatoire par utilisateur ;
- 310 000 itérations.

La table SQLite `app_users` est créée automatiquement dans la base EZScore existante.

OAuth/OIDC (Google et autres fournisseurs) viendra ensuite et réutilisera le même modèle de compte et de permissions.

## Création du premier administrateur

Le premier administrateur n'est créé que si la base utilisateur est vide ET que les variables d'environnement explicites sont présentes.

PowerShell :

```powershell
cd H:\EZScore
$env:EZSCORE_ADMIN_EMAIL="votre-email@example.com"
$env:EZSCORE_ADMIN_PASSWORD="un-mot-de-passe-fort"
$env:EZSCORE_ADMIN_NAME="Steve"

python -m streamlit run EZScore.py --server.address 127.0.0.1 --server.port 8501 --server.headless true
```

Une fois le premier administrateur créé, ces variables ne créent plus d'autre compte.

Pour une installation permanente, elles devront ensuite être placées dans le mécanisme de démarrage du service plutôt que saisies manuellement à chaque lancement.

## Interface de connexion

Une barre de compte est affichée en haut de l'application afin de rester accessible sur téléphone sans dépendre du panneau latéral.

Visiteur :

- état « Visiteur · accès public » ;
- bouton `Connexion` ;
- formulaire e-mail / mot de passe.

Utilisateur connecté :

- nom ;
- rôle ;
- bouton `Déconnexion`.

L'administrateur dispose en plus du panneau `Utilisateurs et droits`.

## Administration des comptes

Un administrateur peut :

- créer un compte ;
- choisir `reader`, `editor` ou `admin` ;
- activer / désactiver un compte ;
- changer le rôle ;
- réinitialiser le mot de passe local.

EZScore refuse de désactiver ou rétrograder le dernier administrateur actif afin d'éviter un verrouillage complet du back-office.

## Contrôle d'accès

### Anonymous

Le visiteur non connecté :

- voit uniquement les chansons dont le workflow est `published` ;
- peut ouvrir les vues de lecture ;
- ne voit pas Import ;
- ne voit pas Modifier ;
- ne voit pas Supprimer ;
- ne peut pas passer en mode Édition ;
- ne voit pas les vues techniques Blocs / Analyse ;
- ne voit pas les diagnostics GPU / Demucs ni les réglages avancés.

### Reader

Le reader :

- dispose du front de lecture ;
- peut accéder aux contenus privés si son rôle le permet ;
- ne peut ni importer, ni modifier, ni publier.

### Editor

L'editor retrouve le back-office :

- Import ;
- Grille / Paroles + accords / Blocs / Analyse ;
- mode Édition ;
- contrôles d'analyse ;
- validation / publication ;
- suppression.

### Admin

L'admin possède les droits editor plus la gestion des utilisateurs.

## Ergonomie tablette / smartphone

R26 renforce le contrat responsive :

- cible tactile minimale de 44 px ;
- champs et sélecteurs tactiles agrandis ;
- radios repliables sur plusieurs lignes ;
- popover de connexion borné à la largeur de l'écran ;
- boutons pleine largeur sur téléphone ;
- uploader pleine largeur ;
- colonnes Streamlit empilées sur petit écran ;
- login accessible dans la zone principale et non uniquement dans la sidebar ;
- aucun contrôle essentiel ne dépend du hover.

## Sécurité actuelle et suite

R26 est un socle fonctionnel, pas encore la fin du chantier identité.

Étapes prévues :

1. validation du login local sur le site Cloudflare ;
2. séparation plus explicite front-office / back-office dans la navigation ;
3. OAuth/OIDC Google ;
4. éventuellement autres fournisseurs ;
5. permissions plus fines par chanson / publication ;
6. préparation des abonnements et droits premium.

Le tunnel Cloudflare reste :

`https://ezscore.logandplay.com` → `http://127.0.0.1:8501`

## Fichiers R26

Le livrable contient uniquement :

- `EZScore.py`
- `readme.md`
- `ezscore/auth/__init__.py`
- `ezscore/auth/roles.py`
- `ezscore/auth/storage.py`
- `ezscore/auth/session.py`
- `ezscore/auth/ui.py`
- `ezscore/ui/responsive.py`
