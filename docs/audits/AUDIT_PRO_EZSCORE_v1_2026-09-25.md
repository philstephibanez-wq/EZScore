# AUDIT PRO — EZScore_v1

**Périmètre audité :** dépôt GitHub `philstephibanez-wq/EZScore_v1`, branche `master`  
**Révision de référence :** `033d1cccf840e36f9154eb5e0792aaeaa6b9d440` (`fichier recette`)  
**Date :** 2026-09-25  
**Nature :** audit statique du dépôt GitHub, architecture, sécurité, qualité, données, Git, dette technique et préparation production.

> Important : cet audit porte sur le contenu du dépôt. Il ne remplace pas l'exécution locale de `composer audit`, des tests, du lint PHP/Twig/YAML, des migrations sur une base vierge et existante, ni une recette navigateur multi-profils.

---

## 1. Synthèse exécutive

Le dépôt est désormais suffisamment structuré pour continuer le développement, mais **il n'est pas encore au niveau “production propre”**.

Les points forts sont clairs :

- architecture Symfony séparée de l'analyse Python ;
- domaine organisé par sous-répertoires (`Song`, `User`, `Group`, `Playlist`, `Analysis`) ;
- routes localisées ;
- contrôles CSRF présents sur les mutations principales ;
- contrôle d'accès généralement explicite ;
- audio privé sous `var/storage/audio` ;
- modèle de jobs d'analyse séparé du statut métier de la chanson ;
- contrat JSON versionné pour le worker ;
- Monolog en place ;
- migrations Doctrine suivies ;
- `recette.md` fournit maintenant une vraie base de recette fonctionnelle.

Mais plusieurs corrections doivent être faites avant de considérer le socle comme stabilisé :

### Bloquants / priorité P0

1. **Secret Symfony versionné dans `.env.dev` sur un dépôt public.**
2. **Création des groupes incohérente avec le métier : actuellement réservée à l'Admin et aucun membership `owner` n'est créé à la création.**
3. **Les playlists ne contiennent encore aucune relation vers les chansons.** Le CRUD “playlist” existe, mais pas le contenu musical d'une playlist.
4. **Aucun test automatisé et aucune CI visible dans le dépôt.**
5. **Le mécanisme de claim des jobs d'analyse n'est pas atomique** et peut attribuer le même job à deux workers concurrents.

### Priorité P1

6. Média runtime (`public/uploads/covers/...jpg`) versionné par erreur.
7. README principal remplacé par des notes de livraison R13.2 au lieu d'être une documentation projet.
8. Répertoires/fichiers manifestement historiques ou morts (`assets/`, `.gitignore` vides dans des dossiers, traductions `messages.r741.*`, JS potentiellement dupliqué).
9. Pas de throttling explicite login/inscription/renvoi activation.
10. Modèle Playlist `ownerType + ownerId` sans FK : intégrité référentielle fragile.
11. Pipeline Python uniquement squelette `/health`; aucun worker réel dans `analysis/`.
12. Contrat d'analyse incomplet côté cycle de vie : pas de lease, retry, timeout, tentative, cancellation HTTP exposée.
13. CSS/JS accumulent des patches de versions (`R10.x`, `R13`, inline styles, cache-busters manuels).

### Priorité P2

14. Pas de licence explicite à la racine malgré `license: proprietary`.
15. Pas de documentation architecture/API/déploiement/backup.
16. Pas de stratégie d'assets formalisée ; jQuery CDN alors que le code est majoritairement vanilla JS.
17. SQLite et stockage disque local devront être réévalués avant montée en charge / édition multi-utilisateur hébergée.

---

## 2. Sécurité

### P0 — `.env.dev` contient un APP_SECRET réel

Fichier :

`/.env.dev`

Contenu actuellement versionné :

```env
APP_SECRET=a195f2e19b98458f8a416f88e7d49b0e
```

Le dépôt est public. Ce secret doit donc être considéré comme compromis.

Même s'il est présenté comme secret de développement, un `APP_SECRET` Symfony participe notamment à des mécanismes cryptographiques de l'application. Il ne doit pas être partagé entre environnements ni être exposé publiquement.

### Action recommandée

- retirer la valeur réelle du dépôt ;
- mettre une valeur factice dans `.env.example` uniquement ;
- générer une nouvelle valeur locale dans `.env.local` / environnement système ;
- vérifier que la valeur exposée n'a jamais été utilisée en production ;
- si oui, la faire tourner immédiatement.

Exemple :

```env
APP_SECRET=CHANGE_ME
```

dans un exemple, et vraie valeur uniquement hors Git.

---

### P1 — absence de throttling explicite

`config/packages/security.yaml` configure `form_login`, mais pas de `login_throttling`.

L'inscription et surtout `/activation/resend` ne montrent pas non plus de limite applicative.

### Risques

- brute force login ;
- spam d'e-mails d'activation ;
- consommation inutile de ressources/API Resend.

### Action recommandée

Ajouter Symfony RateLimiter :

- login ;
- inscription ;
- renvoi activation ;
- éventuellement endpoints internes d'analyse.

---

### P1 — API worker : authentification correcte mais trop monolithique

`AnalysisWorkerTokenGuard` :

- accepte `X-EZScore-Analysis-Token` ou Bearer ;
- utilise `hash_equals` ;
- refuse proprement si le token serveur est absent.

C'est une bonne base.

Limites :

- un seul token partagé pour tous les workers ;
- pas d'identité worker ;
- pas de rotation intégrée ;
- pas de scopes ;
- pas de rate limit ;
- pas de mécanisme de lease.

Pour un worker local unique, c'est acceptable. Pour plusieurs workers ou un déploiement distant, il faudra renforcer.

---

### P1 — jQuery externe sans SRI

`templates/base.html.twig` charge :

```html
https://code.jquery.com/jquery-3.7.1.min.js
```

Le dépôt contient déjà beaucoup de JavaScript vanilla.

Recommandation :

- supprimer jQuery si possible ;
- sinon l'héberger localement ou ajouter SRI + politique CSP adaptée.

Cela réduit une dépendance réseau et simplifie la future politique CSP.

---

## 3. Droits et métier

### P0 — création de groupe incompatible avec la règle métier

Dans `GroupController::index()` :

```php
if ($request->isMethod('POST')) {
    $this->denyAccessUnlessGranted('ROLE_ADMIN');
```

Donc **seul un Admin peut créer un groupe**.

Or le métier actuellement retenu est :

- tout utilisateur enregistré peut créer son groupe ;
- le créateur devient propriétaire/administrateur du groupe.

Deuxième problème : après création de `UserGroup`, le contrôleur ne crée aucun `GroupMember` avec rôle `owner`.

Conséquence :

- un groupe créé n'a pas de propriétaire métier enregistré ;
- un utilisateur non-admin ne peut pas créer de groupe ;
- le système de délégation owner/manager/member part sur une base incohérente.

### Correction recommandée

Dans une transaction :

1. créer le `UserGroup`;
2. créer immédiatement un `GroupMember` pour le créateur ;
3. rôle = `owner`;
4. persister les deux ;
5. flush unique.

L'Admin global doit rester capable de tout administrer sans être nécessairement membre.

---

### P0 — playlist sans chansons

Le dépôt contient :

`src/Domain/Playlist/Playlist.php`

mais aucune entité du type :

- `PlaylistSong`
- `PlaylistItem`
- relation ManyToMany Playlist ↔ Song
- position/ordre de chanson dans playlist.

Le contrôleur gère actuellement :

- création ;
- modification ;
- suppression ;
- visibilité ;
- propriété user/groupe.

Il **ne gère pas le contenu de la playlist**.

Pour le produit EZScore, c'est une fonctionnalité structurelle manquante.

### Modèle recommandé

Préférer une entité explicite :

```text
PlaylistItem
- id
- playlist_id FK
- song_id FK
- position
- added_by
- created_at
```

plutôt qu'un ManyToMany brut, car l'ordre des chansons est métier.

Contraintes recommandées :

```text
UNIQUE(playlist_id, song_id)
INDEX(playlist_id, position)
```

---

### P1 — modèle propriétaire Playlist fragile

Actuellement :

```text
ownerType = user|group
ownerId = integer
```

Il n'existe donc aucune FK entre `ownerId` et `users` ou `user_groups`.

Avantage : simple.

Inconvénients :

- propriétaire orphelin possible ;
- intégrité uniquement assurée par le code ;
- requêtes et suppressions plus difficiles ;
- migrations futures plus risquées.

### Recommandation

Avant production, remplacer par :

```text
owner_user_id nullable FK
owner_group_id nullable FK
```

avec une contrainte logique “exactement un des deux”.

---

## 4. Analyse / Worker Python

### Ce qui est bien

La séparation est saine :

```text
Symfony = orchestration / sécurité / persistance / métier
Python  = calcul musical
```

Le dépôt contient :

- `AnalysisJob`
- `AnalysisJobStatus`
- `AnalysisJobRepository`
- `AnalysisJobManager`
- `AnalysisPayloadContract`
- `AnalysisWorkerController`
- `AnalysisWorkerTokenGuard`

Le contrat est versionné :

```text
ezscore.analysis.v1
```

C'est une bonne décision architecturale.

---

### P0 — claim non atomique

`claimNextQueued()` fait :

1. SELECT du premier job `queued`;
2. modification objet ;
3. flush.

Deux workers simultanés peuvent lire le même job avant le premier flush.

### Correction recommandée

Faire un claim atomique.

Approches possibles :

- transaction + verrou pessimiste si DB le supporte ;
- UPDATE conditionnel `WHERE id=? AND status='queued'`;
- ajout d'un `claimed_at`, `claimed_by`, `lease_until`.

Avec SQLite, il faudra être particulièrement prudent sur la concurrence.

---

### P1 — cycle de vie de job incomplet

L'entité possède :

```php
cancel()
```

mais le contrôleur exposé ne possède pas de route `/cancel`.

Il manque également :

- `attempt`;
- `claimed_at`;
- `claimed_by`;
- `heartbeat_at`;
- `lease_until`;
- stratégie retry ;
- expiration des jobs `running` abandonnés ;
- message d'erreur humain / détails techniques séparés.

Avant connexion réelle des gros analyseurs, ce point doit être traité.

---

### P1 — aucun producteur de job visible

`AnalysisJobManager::createQueued()` existe, mais l'audit du dépôt ne trouve pas de workflow utilisateur réellement branché à cette création.

Le contrat existe donc avant le branchement métier, ce qui est cohérent avec l'étape actuelle, mais le pipeline n'est pas encore complet.

---

### P1 — service Python encore squelette

`analysis/app/main.py` expose uniquement :

```text
GET /health
```

Il n'y a pas encore :

- boucle worker ;
- récupération d'un job Symfony ;
- téléchargement/résolution audio ;
- progression ;
- completion ;
- failure ;
- cancellation.

C'est cohérent avec la décision “recette Symfony d'abord”, mais il ne faut pas considérer `analysis/` comme service fonctionnel aujourd'hui.

---

### Incohérence de configuration à nettoyer

`.env.example` contient :

```env
EZ_ANALYSIS_URL="http://127.0.0.1:8502"
```

alors que l'architecture présente dans le code est surtout un worker qui appelle Symfony via `/internal/analysis/...`.

Il faut décider clairement entre :

**Push Symfony → Python**

ou

**Pull Python → Symfony**

Le code actuel est principalement un modèle **pull worker**.

Documenter ce choix et supprimer les paramètres devenus inutiles.

---

## 5. Import audio / fichiers

### Bonnes pratiques actuelles

- audio hors `public/`;
- SHA-256 ;
- whitelist extensions ;
- MIME ;
- stockage dédupliqué par hash ;
- historique de remplacement ;
- pré-écoute locale navigateur ;
- changement de source séparé de l'édition métadonnées.

---

### P1 — média runtime versionné dans Git

Le dépôt contient :

```text
public/uploads/covers/386a4a4b2114af0e503a8fe6fbcfc533.jpg
```

C'est typiquement un fichier généré par l'application, pas un asset source.

`.gitignore` ne protège pas `public/uploads/`.

### Correction recommandée

Ajouter :

```gitignore
/public/uploads/*
!/public/uploads/.gitkeep
```

et retirer la pochette déjà trackée de l'index Git.

Ne pas perdre le fichier local si tu souhaites le conserver pour les données de recette.

---

### P1 — validation audio trop permissive sans `fileinfo`

`SongImportStorage` accepte `application/octet-stream` si `fileinfo` n'est pas disponible, tant que l'extension est autorisée.

C'était utile pour débloquer Windows, mais pour une mise en ligne publique ce fallback doit être revu.

Recommandation production :

- rendre `ext-fileinfo` obligatoire ;
- vérifier aussi le conteneur avec FFprobe avant analyse ;
- limite de taille métier indépendante de `php.ini`.

---

### P2 — fichiers orphelins

Lors du remplacement de pochette :

- l'ancienne image n'est pas nettoyée.

Lors de remplacement audio :

- les fichiers sont conservés par design pour l'historique ;
- aucun garbage collector n'existe.

Prévoir une politique explicite :

```text
active
archived
orphan
deleted
```

et une commande d'entretien plus tard.

---

## 6. Doctrine / migrations

### Conclusion

**Ne pas supprimer `migrations/` maintenant.**

Le dossier contient l'historique nécessaire pour reconstruire le schéma actuel.

Il contient notamment l'évolution :

- Users / Groups / Playlists ;
- locale ;
- Songs ;
- Analysis jobs ;
- activation email ;
- publication ;
- ratings ;
- import audio ;
- correction SQLite du default `status`.

---

### Dette de migration normale pour une phase de construction

Les migrations R10 puis R10.1 montrent un aller-retour :

```text
status DEFAULT 'editing'
```

puis reconstruction de table pour enlever ce default.

Ce n'est pas beau, mais c'est un historique valide.

### Stratégie recommandée

**Maintenant :**
garder toutes les migrations.

**Juste avant première production**, si toutes les bases actuelles sont jetables :

1. sauvegarder ;
2. figer le mapping ;
3. générer une baseline propre ;
4. tester base vierge ;
5. tester restauration ;
6. seulement ensuite archiver/squasher l'ancien historique si souhaité.

Ne pas faire ce nettoyage pendant la recette fonctionnelle.

---

### P1 — migrations SQLite partiellement irréversibles

Plusieurs `down()` lèvent volontairement une exception.

Ce n'est pas bloquant, mais cela signifie :

- rollback automatique non garanti ;
- il faut tester les migrations vers l'avant ;
- sauvegarde obligatoire avant migration réelle.

---

## 7. Tests / CI

### P0 — aucun test automatisé visible

Le `composer.json` contient :

```json
"autoload-dev": {
  "psr-4": {
    "App\\Tests\\": "tests/"
  }
}
```

mais aucun répertoire `tests/` n'est présent dans l'arbre audité.

Il n'y a pas non plus de dépendance PHPUnit visible.

### Minimum recommandé

Tests unitaires :

- `Song`;
- `SongStatus`;
- `SongRating`;
- `User`;
- permissions groupes/playlists ;
- `AnalysisPayloadContract`;
- `AnalysisJob` transitions.

Tests fonctionnels :

- public catalog ;
- login ;
- import droits ;
- édition droits ;
- publication ;
- group owner/manager/member ;
- playlist ;
- rating ;
- worker token.

---

### P0/P1 — aucune CI visible dans l'arbre

Pas de `.github/workflows/...`.

Créer une CI GitHub Actions minimale :

```text
composer validate
composer install
php -l src/**
lint:yaml
lint:twig
doctrine:schema:validate
tests
composer audit
```

Une base SQLite temporaire convient parfaitement à la CI.

---

## 8. Git / hygiène du dépôt

### Points positifs

- une seule branche visible : `master`;
- dépôt compact ;
- `composer.lock` versionné ;
- `symfony.lock` versionné ;
- `var/` ignoré ;
- DB SQLite ignorée ;
- venv et pycache ignorés.

---

### P1 — travail directement sur master

Pour un projet solo cela peut fonctionner, mais vu la fréquence des livraisons et régressions récentes, une protection légère serait utile :

```text
master = état validé
feature/* ou fix/* = travaux
tag = jalons stables
```

Pas besoin d'un workflow Git lourd.

---

### P1 — commits historiques “KO”

L'historique contient des commits explicitement marqués `ko` et un ancien CRUD rejeté.

Ce n'est pas un problème fonctionnel, mais l'historique est bruité.

Ne pas réécrire l'historique maintenant sans raison forte.

À partir de maintenant :

- commit seulement après contrôles minimum ;
- taguer les jalons réellement stables ;
- ne pas pousser les ZIPs de livraison dans le repo.

---

## 9. Nettoyage de fichiers candidat

### Suppression très probablement sûre après vérification locale

#### Répertoires squelette vides

```text
src/Controller/.gitignore
src/Entity/.gitignore
src/Repository/.gitignore
translations/.gitignore
migrations/.gitignore
```

Les trois premiers reflètent le squelette Symfony historique ; le code métier est désormais sous `src/Domain`.

`src/Entity` et `src/Repository` n'ont plus d'utilité si rien ne les référence.

---

### `assets/` racine probablement obsolète

Le dépôt contient à la fois :

```text
assets/css/app.css
assets/js/app.js
```

et

```text
public/assets/...
```

Les templates actuels chargent `/assets/...`, donc les fichiers réellement servis sont dans `public/assets`.

Le `composer.json` ne montre pas de chaîne AssetMapper/Encore/Vite utilisant le dossier racine `assets/`.

**Candidat sérieux à suppression**, après recherche finale de références.

---

### `public/assets/js/interaction-feedback.js`

La logique d'interaction/hover est déjà présente dans :

```text
public/assets/js/app.js
```

Le fichier séparé semble être un vestige d'une livraison précédente.

Candidat à suppression si aucune référence template ne subsiste.

---

### `translations/messages.r741.fr.yaml`
### `translations/messages.r741.en.yaml`

Ces domaines versionnés semblent être des reliquats de développement.

Ils doivent être supprimés si aucune clé n'est appelée explicitement avec le domaine `messages.r741`.

---

### `public/uploads/covers/*.jpg`

À retirer du suivi Git, mais pas forcément à effacer du disque utilisateur.

---

## 10. Front-end / dette UI

Le front est fonctionnel mais porte clairement les traces des patchs successifs.

Exemples :

- `catalog.css` volumineux avec blocs R9/R10/R10.2/R10.4 ;
- `catalog-r13.css` ajouté en surcharge ;
- `import-cta.css` séparé ;
- style inline du bouton Import ;
- numéros de release dans les query strings CSS/JS ;
- logique langue inline dans `base.html.twig`;
- jQuery + vanilla JS en parallèle.

### Recommandation

Après recette, faire **une seule passe de consolidation front**, sans changement visuel :

```text
base.css
layout.css
catalog.css
song.css
forms.css
```

et :

```text
app.js
song-import.js
```

Objectif : supprimer uniquement les couches mortes/dupliquées.

Ne pas le faire avant d'avoir fini la recette visuelle, sinon risque de régression inutile.

---

## 11. Documentation

### P1 — README principal insuffisant

`readme.md` est actuellement la documentation de la livraison R13.2.

Un README principal devrait décrire :

- ce qu'est EZScore ;
- stack ;
- prérequis ;
- installation ;
- configuration ;
- démarrage ;
- base ;
- sécurité/secrets ;
- stockage ;
- architecture Symfony/Python ;
- commandes de vérification ;
- liens vers recette et docs.

Les notes R13.2 doivent aller dans :

```text
CHANGELOG.md
```

ou dans `docs/releases/`.

---

### Documents recommandés

```text
README.md
CHANGELOG.md
recette.md
docs/
  architecture.md
  analysis-api.md
  deployment.md
  backup-restore.md
```

---

## 12. Production / infrastructure

### SQLite

SQLite est adapté pour :

- développement ;
- recette locale ;
- petite instance mono-serveur.

À réévaluer pour :

- plusieurs éditeurs simultanés ;
- workers d'analyse concurrents ;
- forte activité d'écriture.

Le principal risque sera le verrouillage d'écriture, notamment avec la file `analysis_jobs`.

### Stockage local

`var/storage/audio` convient au poste local.

Pour une version hébergée multi-instance :

- stockage objet ou volume persistant ;
- URL temporaire signée ;
- séparation fichier/source DB.

Cela correspond déjà à l'architecture envisagée.

---

## 13. Plan d'action recommandé

### Phase A — nettoyage immédiat, faible risque

1. rotation/retrait du `APP_SECRET` public ;
2. `.gitignore` pour `public/uploads/`;
3. retirer la pochette trackée ;
4. supprimer fichiers/dossiers squelettes inutiles après vérification ;
5. supprimer `messages.r741.*` si non référencés ;
6. supprimer assets racine morts si non référencés ;
7. supprimer JS dupliqué non chargé ;
8. reconstruire README projet et créer CHANGELOG.

### Phase B — corrections métier avant analyse Python

1. création de groupe ouverte aux utilisateurs connectés ;
2. création automatique du membership owner ;
3. relation PlaylistItem ↔ Song ;
4. intégrité propriétaire playlist ;
5. tests d'autorisation.

### Phase C — qualité automatisée

1. PHPUnit ;
2. tests fonctionnels ;
3. GitHub Actions ;
4. `composer audit`;
5. validation schéma sur base vierge.

### Phase D — analyse Python

1. claim atomique ;
2. lease/heartbeat ;
3. retry/timeout ;
4. cancel ;
5. audio source contract ;
6. worker Python ;
7. résultats persistés/versionnés ;
8. re-analysis/versioning.

### Phase E — pré-production

1. baseline migrations si souhaité et si bases jetables ;
2. politique secrets ;
3. CSP / headers ;
4. throttling ;
5. backup/restore ;
6. stratégie DB ;
7. stratégie stockage audio ;
8. monitoring/log rotation.

---

## 14. Commandes d'audit local recommandées

À exécuter sur `H:\EZScore_v1` pour compléter l'audit statique :

```powershell
cd H:\EZScore_v1

composer validate --strict
composer audit

php bin\console lint:yaml config translations
php bin\console lint:twig templates
php bin\console doctrine:schema:validate
php bin\console doctrine:schema:update --dump-sql
php bin\console debug:router
php bin\console debug:container --env-vars

Get-ChildItem src -Recurse -Filter *.php | ForEach-Object {
    php -l $_.FullName
}
```

Vérifier les fichiers suivis indésirables :

```powershell
git ls-files var
git ls-files public/uploads
git ls-files data
git ls-files | Select-String "__pycache__|\.pyc$|\.sqlite$|\.db$|dev\.log|prod\.log"
```

Rechercher les vestiges :

```powershell
git grep -n "messages.r741"
git grep -n "interaction-feedback.js"
git grep -n "assets/css/app.css"
git grep -n "assets/js/app.js"
git grep -n "TODO\|FIXME\|HACK"
```

Vérifier les secrets :

```powershell
git grep -n "APP_SECRET\|CLIENT_SECRET\|API_KEY\|TOKEN\|PASSWORD"
```

---

## 15. Conclusion

Le socle EZScore_v1 n'est pas désorganisé : l'architecture principale est plutôt saine pour un projet qui a évolué rapidement.

La dette actuelle est surtout concentrée dans quatre zones :

1. **hygiène/sécurité Git** ;
2. **groupes/playlists encore incomplets métier** ;
3. **absence de tests/CI** ;
4. **worker d'analyse encore au stade de contrat/squelette**.

Le nettoyage ne doit pas être un gros refactoring. La stratégie la plus sûre est :

```text
sécurité Git
→ nettoyage mort évident
→ correction groupes/playlists
→ tests/CI
→ recette
→ Python REST
```

Le point le plus urgent est la rotation du `APP_SECRET` versionné. Le point fonctionnel le plus important est la création/propriété des groupes. Le point architectural le plus important avant plusieurs workers est le claim atomique des jobs.
