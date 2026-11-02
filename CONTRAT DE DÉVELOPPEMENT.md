# CONTRAT DE DÉVELOPPEMENT — MÉTHODE SYSTÉMATIQUE ET OBLIGATOIRE

**Instruction permanente :** appliquer les règles suivantes à chaque intervention de développement, correction, refactorisation, migration ou livraison, sans exception implicite.

Le principe directeur est : **traiter la cause, préserver l'existant, réutiliser les solutions éprouvées et démontrer le résultat.**

## 1. Prise en compte des remontées

- Analyser intégralement les résultats, logs, erreurs et observations transmis.
- Distinguer systématiquement : faits démontrés, hypothèses, causes confirmées et points restant à vérifier.
- Rechercher la cause racine avant de proposer une correction.
- Ne jamais répéter un diagnostic déjà validé sans justification.
- Ne jamais déclarer une réussite lorsque des tests ont échoué.

## 2. Informations complémentaires

- Exploiter d'abord les informations déjà disponibles : conversation, GitHub, fichiers, rapports et contrats.
- Ne demander que les informations réellement indispensables.
- Regrouper les diagnostics nécessaires pour limiter les échanges.
- Éviter les cycles répétitifs de micro-commandes.
- Ne jamais faire répéter un test déjà concluant, sauf modification pertinente de l'environnement.

## 3. Audit GitHub transversal obligatoire

Avant toute modification :

- Consulter les sources actuelles des dépôts concernés, leurs branches et leurs versions.
- Lire `AGENTS.md`, les README, les contrats, les issues et les handoffs applicables.
- Examiner les dépendances et les impacts sur les autres composants de l'écosystème.
- Vérifier l'état Git, les changements récents et les éventuelles divergences entre GitHub et MAIN.
- Ne jamais écraser des modifications locales non publiées avec une version distante plus ancienne.

**GitHub est la référence du code publié ; les modifications locales non synchronisées doivent être identifiées et préservées.**

## 4. Traçabilité GitHub et contrats

- Actualiser directement les issues et handoffs concernés lorsque l'accès en écriture est disponible.
- Documenter les décisions techniques, les anomalies, les causes confirmées, les versions et les limites.
- Mettre à jour les contrats lorsque le comportement ou l'architecture évolue.
- Identifier les éléments legacy devenus obsolètes.
- Ne jamais déclarer une issue résolue sans preuve de validation.
- Distinguer les tests exécutés de ceux restant à effectuer.

## 5. Architecture, non-régression et hygiène

**Interdictions :**

- Aucun doublon fonctionnel.
- Aucun contournement provisoire intégré durablement.
- Aucun correctif masquant une erreur sans traiter sa cause.
- Aucun nouveau moteur parallèle sans justification architecturale explicite.
- Aucun changement non demandé dans un composant indépendant.
- Aucune suppression de données ou de fichiers d'état sans preuve de sécurité.

**Obligations :**

- Privilégier une solution simple, modulaire et maintenable.
- Préserver les contrats et fonctionnalités déjà validés.
- Identifier et nettoyer le legacy uniquement après démonstration de sa non-utilisation ou de sa couverture par le remplaçant.
- Garantir **UTF-8 sans BOM** pour tous les fichiers sources et scripts livrés.
- Vérifier l'absence de caractères corrompus et respecter les conventions de fins de ligne.
- Prévoir une restauration contrôlée pour les modifications sensibles.

### 5.1. Étude d'impacts obligatoire

**Avant toute modification ou activation**, analyser les conséquences directes et indirectes du changement, avec un niveau de détail proportionné au risque. Cette étude précède le code, les tests et l'installation ; elle ne doit pas se limiter au seul fichier modifié.

- **Technique et dépendances** : services, processus et enfants, ports, fichiers, configurations, données, journaux, tâches Windows, versions, contrats et appels entre composants.
- **Exploitation et ergonomie** : ordre de boot, démarrage et arrêt, compte et droits d'exécution, consoles et fenêtres visibles, prise de focus, rafraîchissements, fréquence de lancement, consommation CPU/GPU/mémoire et perturbations potentielles sur MAIN.
- **Isolation et sécurité** : séparation DEV/LAB/Assistant/PROD, instances Caddy distinctes, maintenance PROD, SSO et secrets, identité des processus et persistance des arrêts intentionnels.
- **Non-régression et déploiement** : comportements déjà validés, préconditions, compatibilité Windows/PowerShell/PHP/Symfony, sauvegarde, activation, restauration et retour arrière.

Pour chaque impact significatif, préciser **avant/après, risque, prévention, test ou preuve attendu et retour arrière**. Distinguer faits démontrés, hypothèses et points restant à vérifier. Une absence d'impact doit être argumentée, pas présumée.

**Critère bloquant :** ne pas activer un changement sensible si un impact majeur est non maîtrisé ou si sa restauration n'est pas définie. Une tâche planifiée qui ouvre une console noire toutes les minutes constitue un impact utilisateur qui doit être anticipé, même si son code retourne 0.

Cette étude doit rester concise pour un changement simple : elle sert à éviter les régressions et les allers-retours sur MAIN, non à ajouter une procédure bureaucratique.

## 6. Livraison obligatoire par ZIP

Pour toute modification de code :

- Fournir **un seul ZIP différentiel cohérent par livraison**.
- Inclure uniquement les fichiers nécessaires, à leurs chemins définitifs.
- Inclure les tests durables correspondants et la version du produit.
- Exclure les caches, logs, sauvegardes et fichiers temporaires.
- Vérifier réellement l'existence et l'intégrité du ZIP avant livraison.
- Fournir les commandes PowerShell complètes d'extraction, de préflight et d'application.
- Vérifier la version et les fichiers préexistants avant tout remplacement.
- Fournir les commandes de restauration si la modification est sensible.
- Ne pas committer ni pousser le code applicatif à la place du mainteneur.

Pour une intervention sans modification de code, ne pas créer de ZIP inutile. Fournir directement les contrôles nécessaires.

## 7. Tests et recette obligatoires

**Avant livraison :**

- Vérifier la syntaxe des fichiers modifiés.
- Exécuter tous les tests réalisables dans l'environnement disponible.
- Tester les nouveaux cas et les non-régressions.
- Vérifier les préconditions et le comportement des scripts d'installation.
- Ne jamais annoncer un test comme réussi s'il n'a pas été exécuté.

**Sur MAIN :**

- Fournir les commandes de la suite complète des tests unitaires.
- Ajouter les contrôles d'intégration appropriés.
- Vérifier Composer, Symfony, contrats, versions et état Git.
- Inclure les contrôles d'encodage UTF-8 sans BOM.
- Vérifier le fonctionnement réel lorsque la modification l'exige.
- Faire échouer immédiatement la recette si une commande échoue.
- N'afficher le marqueur final de validation que si toutes les vérifications ont réussi.

**Un test unitaire réussi ne constitue pas une validation opérationnelle.**

### 7.1. Tests ordonnés selon la séquence réelle de boot

Pour tout système à démarrage séquentiel (notamment Orchestrator, services DEV/PROD et supervision Windows), la recette doit suivre **l'ordre effectif des dépendances**, de l'initialisation jusqu'à la supervision continue. Les tests isolés restent nécessaires, mais ne remplacent pas les tests de séquence.

Ordre de référence, à ajuster seulement après vérification des dépendances réellement implémentées :

1. **Bootstrap** : chargement de la configuration, contrôle des préconditions, acquisition de l'exclusivité et démarrage du superviseur.
2. **État désiré** : lecture de l'intention persistée pour chaque service ; un arrêt volontaire reste un arrêt volontaire, sans redémarrage implicite.
3. **Inventaire et attestation** : identification des processus, PID, ports, propriétaires et états réellement observables ; distinguer état inconnu, état absent et arrêt confirmé.
4. **Réconciliation** : contrôle et traitement sûr des attestations périmées, sans arrêt ni adoption de processus étrangers.
5. **Démarrage ordonné** : lancement des seuls services attendus actifs, dans l'ordre de leurs dépendances ; ne jamais démarrer un service dont les préconditions ne sont pas satisfaites.
6. **Disponibilité** : attestation des processus, ports et interfaces effectivement nécessaires, en contrôlant séparément les chaînes DEV et PROD.
7. **Supervision continue** : détection des pannes, récupération ciblée, temporisation bornée des nouvelles tentatives et respect permanent de l'état désiré.

Les domaines indépendants restent isolés : une panne LAB ne doit pas déclencher une intervention sur PROD ou Caddy DEV. L'ordre ci-dessus définit une **logique de validation**, pas une autorisation de modifier des processus.

### 7.2. Scénarios obligatoires et niveaux de preuve

- **Boot à froid** : aucun service préexistant ; vérifier chaque transition et l'ordre des dépendances.
- **Boot à chaud** : services déjà actifs ; vérifier l'idempotence, la non-duplication et l'absence de redémarrages inutiles.
- **Panne contrôlée** : perte d'un service ou attestation obsolète ; vérifier la reprise du seul composant concerné, après vérification de son identité.
- **Arrêt intentionnel** : l'état STOPPED persiste pendant les cycles de supervision et après redémarrage du superviseur.
- **Échec d'une dépendance** : signaler l'échec, ne pas lancer les dépendants incompatibles et préserver les autres domaines.
- **Conflit d'identité / PID étranger** : refuser toute action dangereuse et produire un diagnostic explicite.

Pour chaque scénario, distinguer **tests unitaires avec doubles de test**, **tests d'intégration**, puis **recette opérationnelle réelle** sur un environnement autorisé. Un scénario simulé ne prouve ni le boot Windows effectif, ni la récupération d'un service réel.

### 7.3. Exécution, durée et critères de validation

- Exécuter en priorité les tests ciblés correspondant à la séquence affectée, puis les tests d'intégration appropriés et la suite complète avant validation finale.
- Une exécution bloquée ou un **timeout** est un échec non diagnostiqué, jamais une réussite implicite ; identifier le test ou l'attente responsable avant d'augmenter un délai.
- Tracer le nom de l'étape, son début, sa fin, son résultat et sa durée lorsque nécessaire pour localiser un blocage ; préserver les preuves.
- Éviter la répétition d'une suite complète inchangée lorsque son blocage est déjà établi ; isoler d'abord la cause et corriger le mécanisme concerné.
- Ne jamais activer une supervision permanente ou lancer des services PROD uniquement pour faire passer des tests, sans préflight, périmètre autorisé et procédure de restauration.
- Une validation finale exige des preuves distinctes : **séquence de boot conforme**, **tests automatisés réussis**, puis **fonctionnement réel attesté** quand le changement porte sur le cycle de vie des services.


## 8. Fichiers temporaires et environnement

Tous les éléments temporaires doivent être créés exclusivement sous :

`H:\temp`

Cela comprend les ZIP extraits, scripts ponctuels, rapports, dumps, sauvegardes et fichiers de diagnostic.

- Aucun fichier temporaire dans les dépôts.
- Aucun composant permanent ne doit dépendre de `H:\temp`.
- Les données de fonctionnement et preuves devant survivre à une purge doivent être stockées dans un emplacement durable approprié.
- Ne jamais supprimer automatiquement des preuves d'incident.

## 9. Réutilisation obligatoire des solutions existantes

**Avant tout développement maison :**

1. Rechercher les fonctions déjà présentes dans le projet.
2. Examiner les capacités natives des technologies utilisées.
3. Identifier les bibliothèques, composants et outils éprouvés disponibles.
4. Comparer leur maintenance, leur sécurité, leurs dépendances et leur compatibilité.
5. Ne développer une solution spécifique que si les alternatives ne répondent pas correctement au besoin.

Lorsqu'une solution existante est écartée, documenter pourquoi.

**Ne jamais recréer une fonction standard uniquement parce qu'il est possible de la programmer.**

---

## 10. Priorité au fonctionnement démontré

Le développement doit viser des résultats opérationnels vérifiables, et non l'accumulation de protections théoriques.

Progression privilégiée :

**Fonctionnement minimal réel → validation → stabilisation → durcissement progressif.**

Les protections fondamentales restent obligatoires dès le départ, notamment contre :

- la perte de données ;
- les modifications non autorisées ;
- les opérations sur des processus étrangers ;
- les conflits DEV/PROD ;
- les actions irréversibles sans preuve suffisante.

Les protections avancées peuvent être planifiées après validation du fonctionnement principal.

## 11. Une seule étape opérationnelle à la fois

- Préparer une progression cohérente en étapes.
- Livrer une seule modification ou opération significative à la fois.
- Attendre et analyser le résultat d'une étape avant toute opération dépendante.
- Ne jamais enchaîner automatiquement après un échec.
- Ne pas multiplier les commandes diagnostiques lorsqu'un contrôle global fiable est possible.
- Éviter toute répétition non nécessaire d'une recette déjà validée.

Pour les opérations sensibles, distinguer explicitement :

**PRÉFLIGHT → APPLICATION → RECETTE → VALIDATION → PUBLICATION.**

## 12. Sécurité des opérations et récupération

Avant toute action susceptible de modifier des processus, services, données ou configurations :

- Vérifier les identités, dépendances et états actuels.
- Déterminer les impacts et les effets secondaires possibles.
- Prévoir un mécanisme de restauration ou de réconciliation.
- Refuser une action lorsque les informations nécessaires sont insuffisantes.
- Ne jamais contourner un garde-fou uniquement pour obtenir un résultat positif.
- Ne pas confondre absence d'information, absence de processus et arrêt confirmé.

## 13. Format obligatoire de chaque réponse de développement

Chaque réponse opérationnelle doit présenter, de façon proportionnée :

1. **Constat** — résultats et anomalies pris en compte.
2. **Cause** — démontrée ou hypothèse clairement identifiée.
3. **Audit** — sources GitHub, contrats et composants examinés.
4. **Décision** — solution choisie et alternatives écartées.
5. **Modifications** — fichiers concernés, legacy, impacts.
6. **Livrable** — ZIP vérifié ou justification de son absence.
7. **Commandes** — installation, recette, restauration si applicable.
8. **Validation** — tests réellement exécutés et limites.
9. **Suite** — une seule prochaine étape clairement définie.

**Aucune conformité ne doit être affirmée sans preuve.**

---

## RÈGLE FINALE

**La priorité est d'obtenir un système fonctionnel, maintenable, reproductible et sûr.**

La méthode est au service de cet objectif.

Ne pas remplacer le progrès réel par une succession de correctifs, de diagnostics ou de tests qui ne rapprochent pas concrètement le projet de son fonctionnement attendu.

## 14. Panneau de diagnostic DEV — espace d'observation de l'assistant

Le panneau de diagnostic partagé de l'Orchestrator est mis à la disposition de l'assistant comme **espace d'instrumentation et d'observation**. Le mainteneur autorise explicitement l'assistant à en modifier librement la présentation, les vues, les mesures et les rapports afin de recueillir les informations nécessaires à l'analyse des incidents, aux recettes et aux investigations de non-régression, sans devoir demander une autorisation pour chaque nouveau champ de diagnostic.

Cette autonomie concerne **uniquement le diagnostic** et ne constitue pas une autorisation générale de modifier le comportement métier ou d'exécuter des opérations sensibles. Les règles suivantes restent impératives :

- Le panneau peut être enrichi, réorganisé, replié, filtré et doté de commandes de **copie/export** de rapports ; il peut collecter des observations PHP/Twig, JavaScript, DOM, API, processus et services lorsque ces observations sont nécessaires et accessibles de manière légitime.
- Les collectes sont **en lecture seule par défaut**. Aucun START/STOP, déploiement, suppression, réconciliation d'état ou écriture applicative ne peut être déclenché par un dispositif de diagnostic sans demande et procédure explicites du mainteneur.
- Aucune collecte ni copie de secrets : exclure notamment les jetons CSRF, clés API, cookies, identifiants d'authentification, en-têtes sensibles, données privées, chemins personnels inutiles et corps de réponse non filtrés. Préférer une liste blanche de champs diagnostiques et des rapports expurgés.
- Le panneau est réservé à l'environnement **DEV** et ne doit ni exposer d'informations de diagnostic sur PROD ni modifier son fonctionnement. Il doit rester repliable, accessible et sans perturbation de la navigation ou de la supervision existante.
- Les informations rapportées doivent identifier leur provenance et distinguer **état observé**, **erreur**, **hypothèse** et **conclusion vérifiée**. Un échec de collecte doit être affiché comme tel, jamais converti en état positif.
- L'assistant peut faire évoluer ce panneau à son initiative pour accélérer le diagnostic, mais **toute modification de code reste soumise** à l'audit GitHub, au préflight, aux tests, à la livraison ZIP, à la traçabilité et à la discipline de publication du présent contrat. Cette autorisation n'accorde pas le droit de committer ou pousser le code applicatif à la place du mainteneur.

**Finalité :** permettre au mainteneur de transmettre en une copie un diagnostic structuré et exploitable, sans dépendance systématique aux outils de développement du navigateur ni aux commandes ponctuelles.

## 16. Contrat normatif — Disponibilité autonome et recette stateless

### 16.1 Watchdog indépendant

La surveillance de disponibilité ROOT est exécutée hors de Caddy et de FastCGI ROOT, notamment par une tâche Windows. Chaque cycle doit effectuer une sonde HTTP bornée sur un chemin de santé explicite qui valide le fonctionnement applicatif, et pas seulement l'ouverture d'un port.

- Réponse saine : le watchdog ne modifie pas ROOT.
- Réponse absente ou incorrecte : diagnostiquer puis tenter une récupération autonome si et seulement si les contrôles de sécurité l'autorisent.
- PID étranger, PID réutilisé, identité incomplète, port occupé sans attribution, intention de spawn non résolue : refuser toute terminaison ou adoption et journaliser l'incident.
- Ne pas créer de boucle agressive : verrou, délais bornés, journalisation et résultat exploitable par le Planificateur Windows.
- L'exécution du watchdog ne dépend pas de l'interface web de ROOT.

### 16.2 Tests indépendants et contrôle de démarrage

Les tests unitaires doivent réussir dans n'importe quel état des services réels. Leurs dépendances système sont simulées ou injectées ; les dossiers d'état sont uniques à chaque scénario. Ils ne lisent ni n'effacent les états de production ou de MAIN.

La suite de tests complète est obligatoire avant livraison et publication, mais ne doit pas être exécutée automatiquement à chaque reprise ROOT. Le démarrage utilise un ensemble réduit de préconditions rapides, bornées et sans effet de bord.

### 16.3 Supervision selon les intentions persistantes

Une fois ROOT disponible, l'Orchestrator reprend la supervision des groupes selon leurs intentions explicitement enregistrées : RUNNING et STOPPED, séparation DEV/LAB/Assistant/PROD, modes maintenance et environnement, arrêts volontaires et paramètres requis. Les états absents ou invalides ne doivent jamais être inventés. Un STOPPED volontaire ne doit pas être converti en RUNNING par une sonde.

### 16.4 Recette obligatoire, stateless et réelle

Chaque scénario produit un état initial contrôlé, une panne injectée, une attente explicite, les observations finales et les preuves de nettoyage. Couvrir au minimum : démarrage à froid et à chaud, Caddy mort, FastCGI mort, processus vivant mais HTTP indisponible, port étranger, PID réutilisé, intention pending, collision de verrou, arrêt volontaire, absence de doublon, protection PROD et reprise des intentions. Répéter les scénarios dans un ordre arbitraire.

Les tests isolés sont exécutés dans des environnements indépendants. Les essais sur MAIN ne doivent intervenir qu'après contrôle des ressources, sans suppression des données ou états persistants et avec procédure de restauration. Un nombre de tests PHPUnit réussi ne constitue jamais une preuve d'accessibilité HTTP ni de reprise opérationnelle.

### 16.5 Critère de validation

Il faut démontrer cumulativement : disponibilité HTTP de ROOT, reprise automatique effective après défaillance, conservation des intentions et sécurité des processus étrangers, validation stateless, tests non-régressifs et absence d'impact PROD. Une exigence non démontrée reste NON VALIDÉE.

## CONTRAT TRANSVERSAL - Dialogues et supervision

- Ne jamais utiliser window.confirm(), window.alert(), window.prompt() ou MsgBox natif pour les confirmations de l'interface EZS. Utiliser une modale HTML accessible, dont la fermeture vaut annulation.
- Ne pas declencher de processus Windows depuis une minuterie jQuery sans verification native de l'absence de console et de vol de focus.
- Cette regle concerne tous les depots EZS et leurs interfaces.

## CONTRAT TRANSVERSAL — Structure Symfony et cleanup obligatoires

Cette section est normative pour **EZS_orchestrator, EZStudio_lab, EZStudioLab_assistant, EZScore (DEV et PROD)** et toute application intégrée à l'écosystème. La même version du présent contrat est conservée à la racine de chaque dépôt ; les contraintes spécifiques de `AGENTS.md` s'ajoutent sans amoindrir ces obligations.

### Arborescence et responsabilité unique

- Respecter les conventions Symfony : `src/` pour le code PHP applicatif, `config/` pour la configuration, `templates/` pour Twig, `public/` pour les ressources publiques, `assets/` si une chaîne d'assets est utilisée, `tests/` pour PHPUnit et tests de contrat, `migrations/` en cas de schéma persistant, `translations/` si nécessaire, `bin/` pour les entrées CLI, `var/` pour les données runtime/cache/log non versionnées, et `vendor/` pour Composer non versionné. `composer.json` et `composer.lock` sont gérés à la racine.
- Préserver une seule implantation canonique par fonctionnalité et une seule route/commande/queue/worker propriétaire. Les modules Symfony restent clairement séparés, sans contrôleurs ou services dupliqués dans des arborescences historiques.
- Éviter les racines applicatives parallèles (par exemple `web/` et racine) lorsqu'elles désignent deux applications concurrentes. Toute exception architecturale est explicitement documentée, avec propriété et plan de convergence.
- Conserver Python uniquement là où nécessaire aux moteurs scientifiques et à l'IA, dans un espace identifié appartenant à LAB, Assistant ou EZScore ; aucun retour de logique d'orchestration Python dans EZS_orchestrator.
- Utiliser Twig, jQuery et Bootstrap pour l'interface standardisée, PHPUnit pour les tests PHP et les composants Symfony maintenus plutôt que des mécanismes maison redondants.

### Cleanup obligatoire à chaque livraison

1. **Avant écriture** : inventorier les fichiers, services, routes, scripts, fixtures, tests, dépendances et répertoires touchés ; identifier les doublons, le legacy et les données à conserver. Comparer le dépôt GitHub et le worktree MAIN, sans écraser les changements locaux.
2. **Dans la même livraison que le remplacement validé** : retirer les fichiers et références devenus réellement obsolètes (routes, scripts, imports, services, configurations, tests anciens) après preuve de parité et d'absence d'usage. Aucun empilement de versions `*_old`, `*_backup`, `*_fix`, `*_v2` ou copies parallèles dans le dépôt.
3. **Hors dépôt** : placer ZIP, scripts de patch ponctuels, backups, dumps, rapports de diagnostic et fichiers temporaires sous `H:\temp`. Ne jamais versionner `vendor/`, `var/cache`, `var/log`, modèles IA, secrets, datasets, résultats scientifiques temporaires ni fichiers générés ; appliquer les `.gitignore`/`.gitattributes` appropriés sans supprimer de preuves utiles.
4. **Protection des données** : ne jamais purger automatiquement queues persistantes, jobs, attempts, SQLite, résultats, presets, médias, historiques ou traces d'incident. Leur migration, archivage ou suppression exige un inventaire et une procédure explicitement validée.
5. **Vérifications bloquantes** : contrôler l'arborescence, `git status --short`, `git diff --check`, fichiers non suivis, routes/services concurrents, absence de temporaires, décodage UTF-8 strict sans BOM, `composer validate`, lint PHP/Twig et tests PHPUnit/contrats appropriés. Une livraison n'est pas terminée si le cleanup prévu n'est pas exécuté ou si ses preuves manquent.
6. **Traçabilité** : inscrire dans l'issue/handoff les éléments conservés, supprimés et différés, les raisons des exceptions de structure, les tests réellement exécutés et le plan de migration. Le nettoyage n'autorise jamais une régression métier.

### Installation et restauration

- Préflight, application, recette, validation, publication sont des étapes distinctes. Aucun rollback automatique ni étape de rollback dans la séquence d'application normale.
- Préserver les sauvegardes nécessaires **hors dépôt**, sans les réappliquer tant qu'une restauration n'est pas explicitement décidée.
- Toute refactorisation transversale est livrée par lots atomiques testés, sous version canonique propre à chaque projet et commit/push effectué par le mainteneur.


## CONTRAT TRANSVERSAL — Diagnostic brut, dumps JSON et séparation de responsabilités

Cette règle s'applique à **tous les modules et applications EZS en développement**, notamment EZS_orchestrator, EZStudio_lab, EZStudioLab_assistant et EZScore DEV, ainsi qu'à leurs interfaces de diagnostic et rapports automatisés. **EZScore PROD est exclusivement un déploiement du code EZScore DEV validé, et non un projet ou une branche de développement fonctionnel indépendant.** Les mêmes règles de diagnostic et de présentation s'appliquent à PROD lors du déploiement contrôlé de DEV vers PROD ; aucune correction spécifique en PROD ne doit créer de divergence fonctionnelle. Elle prime sur les anciennes implémentations ou présentations des panneaux de diagnostic.

### 1. Diagnostic : restitution de preuves, sans interprétation

- Un panneau de diagnostic, y compris son template Twig, affiche les **résultats bruts structurés** des sources sous forme de **dumps JSON indentés, lisibles, copiables et exportables** ; le template se limite à la présentation, à la provenance et à l'organisation des blocs.
- Conserver les noms de champs, types, valeurs et distinctions de la source : `null`, `false`, `0`, `PARTIAL`, `STOPPED`, `RUNNING`, codes HTTP, erreurs et absences de champs. Ne jamais inventer une valeur ou traduire un état technique en diagnostic métier.
- **Aucun calcul de badge ou état synthétique, requalification, fallback heuristique, déduction ni fusion silencieuse** des résultats dans le volet de diagnostic. Les décisions métier et états affichés dans les interfaces opérationnelles appartiennent à une couche distincte.
- Une observation API, une observation native, un relevé réseau et un instantané DOM sont des sources **distinctes**. Afficher chaque dump séparément avec sa provenance, sa date/heure de capture, son statut de collecte et, si utile, sa durée. Ne jamais masquer une divergence par une valeur recomposée.
- Les champs additionnels de collecte (`source`, `timestamp_utc`, `http_status`, `collection_error`, etc.) doivent être placés dans une **enveloppe de métadonnées distincte**, identifiée comme telle ; le corps `data` contient les champs de la réponse source préservés.
- En cas d'erreur de collecte, afficher **l'erreur réelle**, sa provenance et les données effectivement disponibles. Ne jamais présenter comme actuel un ancien résultat conservé ; l'éventuel dernier résultat valide doit être explicitement horodaté comme historique.

### 2. Sécurité et intégrité des dumps

- Les dumps « bruts » sont **fidèles aux données non sensibles** : retirer ou masquer, avant affichage, copie, export ou stockage, les secrets et identifiants sensibles (jetons CSRF, cookies, mots de passe, clés API, entêtes d'authentification, données privées). Un masquage est indiqué explicitement ; ne jamais exposer un corps HTTP brut non filtré.
- La politique d'expurgation est déterministe, limitée aux champs sensibles, testée et documentée. Elle ne change jamais la sémantique des champs techniques restants. Préférer une liste blanche de champs diagnostiques si la source contient des données potentiellement privées.
- Les outils de diagnostic sont **en lecture seule par défaut**. Aucun bouton de collecte ou export ne peut déclencher un START/STOP, une réconciliation ou un changement de l'état désiré.
- Conserver un JSON valide, en **UTF-8 sans BOM** dans les artefacts, avec indentation stable, sans mojibake ; fournir une copie/export du même résultat expurgé effectivement affiché.

### 3. Interface opérationnelle séparée

- L'interface de pilotage peut calculer ses indicateurs à partir des preuves disponibles ; cette interprétation n'altère jamais les dumps du panneau de diagnostic.
- Les badges principaux d'un service utilisent exclusivement **ONLINE**, **OFFLINE** ou **ERREUR**. `OFFLINE` est l'arrêt volontaire **effectivement confirmé** ; cet état normal n'est jamais une erreur. `ONLINE` nécessite une disponibilité attestée ; `ERREUR` signale une défaillance ou une impossibilité d'attester l'état attendu, dont la cause détaillée reste visible dans les dumps.
- Un groupe partiellement arrêté n'est pas `OFFLINE` tant que l'arrêt complet n'est pas attesté. Les commandes `Ouvrir`, `Démarrer`, `Arrêter` reflètent les capacités et la disponibilité réelles ; `Ouvrir` n'est pas actif pour un service `OFFLINE` ou non accessible.
- La **maintenance PROD** est un mode d'exploitation indépendant de ces trois états ; elle n'autorise aucun changement de processus ou configuration sans commande explicite.

### 4. Tests contractuels et non-régression

- Vérifier séparément : fidélité du JSON et de ses types ; provenance et horodatage ; expurgation des secrets ; affichage des erreurs de collecte ; absence d'inférence ou de transformation dans le diagnostic ; copie/export identiques à l'affichage.
- Vérifier les transitions opérationnelles ONLINE/OFFLINE/ERREUR par attestation réelle quand elles impliquent le cycle de vie des services. Une suite PHPUnit verte ou une réponse HTTP 200 **ne prouve pas** un arrêt natif.
- Ne jamais modifier les preuves d'incident ni les intentions persistées pour rendre un badge conforme. Un changement de contrat n'autorise pas à lui seul une modification des processus, de PROD ou des données persistantes.
