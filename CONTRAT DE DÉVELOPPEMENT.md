# CONTRAT DE DÉVELOPPEMENT DE LA PLATEFORME EZS — MÉTHODE SYSTÉMATIQUE ET OBLIGATOIRE

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

## CONTRAT TRANSVERSAL — Supervision fédérée, sondes système et REST

Cette section s'applique à EZS_orchestrator, EZStudio_lab, EZStudioLab_assistant, EZScore DEV et à son déploiement PROD, ainsi qu'à toute application rejoignant l'écosystème EZS. Elle complète la section 16 (disponibilité autonome) et le contrat de diagnostic brut. En cas de divergence, les garanties d'isolation, d'attestation et de sécurité des processus restent prioritaires.

### 1. Propriété et frontières de responsabilité

- Le watchdog Windows, indépendant de ROOT, surveille et restaure **exclusivement** la disponibilité du socle ROOT Orchestrator, en respectant l'intention persistée et toutes les attestations de propriété. Il ne supervise ni ne recycle les applications clientes.
- EZS_orchestrator assure le pilotage autorisé des **applications comme unités** : inventaire, disponibilité système, interrogation REST, conservation des preuves et commandes de cycle de vie explicitement permises. Il ne réimplémente pas leurs règles métier ni leur supervision interne.
- Chaque application est l'unique propriétaire de ses composants internes (frontend, backend, processus auxiliaires, workers, files, bases, moteurs scientifiques, etc.), de leurs états, de leurs diagnostics et de leurs politiques de récupération. L'Orchestrator ne termine pas un worker interne parce qu'une API signale `DEGRADED`.
- L'existence d'un frontend et d'un backend ne crée pas deux propriétaires de supervision. Une application fournit une vue cohérente de son périmètre, y compris lorsqu'un composant est indisponible. Les contrats applicatifs peuvent préciser plusieurs sondes sans transférer la propriété des composants.
- Le mode maintenance et les intentions `RUNNING`/`STOPPED` sont indépendants des états de santé. Un `STOPPED` volontaire attesté n'autorise ni sonde déclenchant un démarrage ni récupération implicite. Aucune action implicite sur PROD.

### 2. Deux catégories de sondes complémentaires

- **Sonde système** : preuve native bornée de l'identité du processus, de son chemin, de sa commande, de sa date de création et, quand pertinent, de la connectivité TCP du port attendu. Les relevés WMI/CIM, TCP et netstat restent des observations distinctes. Un ICMP `ping` vers une adresse n'atteste jamais l'état d'un port ni d'une application.
- **Sonde REST** : requête HTTP bornée vers un endpoint applicatif documenté, mesurant la disponibilité fonctionnelle et retournant les états de supervision que l'application peut attester. Une réponse HTTP du seul reverse proxy (`502`, `503` ou autre) n'établit pas la santé de l'application.
- La disponibilité opérationnelle ne se déduit pas de la seule présence d'un PID, d'un port ouvert ou d'un HTTP `200` ne testant rien d'applicatif. Le code HTTP, le corps JSON valide et les critères du contrat applicatif doivent être évalués explicitement dans la couche opérationnelle.
- Toute divergence (TCP ouvert / REST indisponible, REST disponible / attestation native impossible, données périmées) est conservée telle quelle et signalée comme anomalie, sans fusion ou correction heuristique du dump.

### 3. API REST de santé et statut

- `GET /health` (ou chemin équivalent versionné et documenté) : sonde **légère**, bornée, sans effets de bord, ne déclenchant ni analyse lourde, ni migration, ni réparation, ni démarrage de worker. Elle atteste le fonctionnement minimal réel de l'application et fournit un résultat interprétable par la supervision. Une absence de résultat est une erreur de collecte, jamais un `OK` présumé.
- `GET /api/status` (ou chemin équivalent déclaré) : réponse JSON structurée, exposant les informations **nécessaires et disponibles** à la supervision globale : identité, version, instance/environnement, santé, activité, composants, anomalies et horodatage de la mesure. Les composants facultatifs et les états inconnus sont représentés honnêtement, sans valeur inventée.
- La santé (`OK`, `DEGRADED`, `ERROR`, `UNKNOWN`) est distincte de l'activité (`IDLE`, `BUSY`, `PAUSED`, `UNKNOWN`). `BUSY` n'est pas une panne ; `DEGRADED` ne donne pas automatiquement le droit de redémarrer quoi que ce soit.
- Les états applicatifs détaillés sont des **faits déclarés par l'application**, pas des attestations natives produites par l'Orchestrator. Les causes et métriques de workers/queues relèvent de l'application.
- Chaque application documente le schéma et la version de son contrat REST, les champs requis et optionnels, leurs types, les éventuelles unités et la signification des erreurs HTTP. Les consommateurs acceptent explicitement les versions compatibles ; pas de fallback silencieux.
- Les réponses doivent être bornées en taille et en temps, sécurisées sur le réseau local ou par authentification adaptée, et expurgées des tokens, cookies, secrets, chemins personnels sensibles et données métier privées. Une sonde ne doit pas provoquer de charge notable ni d'effet secondaire.

### 4. Collecte, journaux et restitution

- Watchdog et Orchestrator journalisent **séparément** les observations, décisions et actions avec heure UTC, ID de cycle, application/instance, provenance, durée, code HTTP, statut de collecte, résultat de l'attestation, identité attestée, erreur éventuelle et statut final.
- Conserver une trace durable lisible machine (JSONL ou équivalent documenté) et les preuves d'incident, sans dépendance à `H:\temp` et sans suppression automatique des traces nécessaires. La rotation, si activée, préserve les incidents utiles.
- Le résultat de cycle distingue explicitement `HEALTHY`, `RECOVERED`, `DEGRADED`, `FAILED` : `RECOVERED` requiert une **nouvelle sonde REST réussie après l'action**. Un redémarrage de processus sans rétablissement HTTP reste un échec.
- Le code retour du watchdog, notamment vers le Planificateur de tâches, distingue succès, dégradation non récupérable et échec technique selon une table documentée. Une panne de ROOT ne peut pas être déclarée réussie par défaut parce que le script s'est exécuté.
- Les dumps bruts système et REST restent **distincts**, avec enveloppes de métadonnées de collecte, sans inférence ni réécriture des valeurs dans le volet diagnostic. Les agrégations et badges appartiennent exclusivement à la couche opérationnelle (ONLINE/OFFLINE/ERREUR).

### 5. Récupération, tests et déploiement

- Le watchdog tente une récupération ROOT **seulement** après preuve de l'identité, de la propriété et des préconditions de sécurité. PID étranger/réutilisé, port sans propriétaire attribuable, observation incohérente et intention ambiguë imposent un refus journalisé ; pas de boucle agressive.
- L'Orchestrator ne répare pas directement les composants internes des applications. Il conserve leur état déclaré et peut déclencher exclusivement les opérations globales explicitement autorisées, avec préflight, respect de l'intention et isolation PROD.
- Les tests couvrent : système OK / REST OK ; système OK / REST KO ; système KO / REST KO ; système ambigu / REST OK ; retour REST invalide ou périmé ; application `BUSY` ; application `DEGRADED` ; `STOPPED` volontaire ; port/PID étranger ; échec puis réussite de récupération ; absence d'effet sur PROD.
- Les tests unitaires sont indépendants des services réels. Une recette MAIN prouve séparément la sonde système, la réponse REST applicative, les journaux, l'absence de redémarrage abusif et l'absence d'impact PROD. Une suite de tests verte ne prouve pas la reprise opérationnelle.
- **Ordre du chantier en cours** : restaurer et valider le watchdog ROOT et la disponibilité HTTP de l'Orchestrator ; ensuite seulement contractualiser et intégrer les endpoints de supervision des autres applications. Le présent amendement ne constitue aucune autorisation d'activer immédiatement des sondes ou actions sur PROD.

## CONTRAT DE PLATEFORME EZS — Socle technologique et responsabilités transversales

### Périmètre normatif et synchronisation

La **Plateforme EZS** regroupe exactement quatre dépôts de développement : `EZS_orchestrator`, `EZScore` (source DEV, dont PROD est un déploiement), `EZStudio_lab` et `EZStudioLab_assistant`. Le contrat de plateforme est **identique** dans les quatre dépôts ; leurs fichiers `VERSION`, cycles de publication, configurations et métiers demeurent propres à chacun. Toute modification transversale exige l'audit puis la propagation explicite aux quatre dépôts, avec suivi de convergence et vérification des écarts locaux avant pull, merge ou remplacement. Aucune synchronisation documentaire n'autorise un déploiement PROD.

### Standard technique commun

- **Web et architecture** : PHP 8.5 et Symfony maintenu ; organisation canonique `src/`, `config/`, `templates/`, `public/`, `assets/` si requis, `tests/`, `var/`, `migrations/` si nécessaire ; une responsabilité unique pour chaque service, route et composant.
- **Interface** : Twig pour les vues, jQuery et Bootstrap pour l'interface standard ; libellés français et encodage UTF-8 sans BOM ; aucun dialogue natif interdit par le contrat.
- **Asynchrone et temps** : Symfony Messenger pour les files et handlers lorsque des tâches asynchrones sont nécessaires ; Symfony Clock pour une gestion injectable et testable du temps ; Scheduler uniquement lorsque l'application a un besoin de planification. Transport, retry, échecs, idempotence et persistance sont explicitement contractualisés. Ne pas créer d'ordonnanceur ou de queue parallèle inutile.
- **Tests** : PHPUnit, tests de contrat et d'intégration indépendants des états réels ; mocks/injections de l'horloge et des transports ; scénarios de disponibilité, d'échec, de non-régression et d'isolement. Les tests verts ne remplacent pas une recette opérationnelle.
- **Python** : seulement dans les applications qui en ont besoin pour l'IA, les moteurs scientifiques et les workers ; environnement virtuel, dépendances, limites de ressources, messages, logs et cycle de vie sous la responsabilité exclusive de l'application propriétaire. Aucun moteur métier Python déplacé dans l'Orchestrator.
- **Infrastructure** : mêmes principes de configuration séparée par environnement, supervision, santé, isolation des ports/processus, sécurité et secrets, démarrage/arrêt, journalisation, sauvegarde, récupération et diagnostic. Standard commun ne signifie ni instance partagée non maîtrisée ni installation de composants inutiles.

### Contrats de santé et supervision fédérée

- Le **watchdog Windows indépendant** assure exclusivement la disponibilité de ROOT : contrôle système (identité native, port TCP), santé HTTP applicative, récupération sûre et bornée, puis attestation HTTP finale. Un processus vivant ou un port ouvert ne suffit pas. Aucun impact PROD.
- L'**Orchestrator** collecte, conserve et expose l'état global de chaque application en respectant son intention persistée et son mode maintenance. Il n'invente pas d'état interne, ne démarre pas un service volontairement STOPPED et ne répare pas directement les workers, frontend ou backend des applications.
- **Chaque application** pilote et répare ses propres frontend, backend, workers, files et dépendances. Elle expose un endpoint léger de disponibilité (`GET /health` ou équivalent documenté) et un endpoint de supervision détaillée (`GET /api/status` ou équivalent documenté), protégés selon la sensibilité des informations.
- Le **ping système** atteste la présence et l'identité du processus ainsi que la disponibilité TCP pertinente. Le **ping REST** confirme la santé applicative et restitue les informations de supervision nécessaires : identité, version, environnement, santé, activité, composants internes, anomalies, mesures disponibles et horodatage. `BUSY` n'est jamais une erreur. Un échec REST n'est pas transformé en état métier déduit.
- Chaque application reste seule propriétaire de la signification de ses états et du détail de ses composants. Le panneau de diagnostic de la plateforme affiche chaque réponse source en JSON brut expurgé et horodaté, séparément de l'observation système ; les indicateurs synthétiques appartiennent à la couche opérationnelle.

### Logs, diagnostic et preuve de fonctionnement

- Chaque watchdog et application produit des **journaux structurés durables** (UTC, source, version, instance, identifiant de corrélation, contrôle, durée, état brut, erreur réelle, action et résultat). Les fichiers de fonctionnement sont dans `var/log` ou l'emplacement canonique non versionné de l'application ; les preuves ne sont jamais supprimées automatiquement pour masquer un incident.
- Le **panneau Twig de diagnostic** de chaque application présente des dumps JSON fidèles, indentés, copiables et exportables, avec provenance et métadonnées de collecte séparées, expurgation déterministe des secrets et absence d'inférence. Les diagnostics sont en lecture seule ; les commandes opérationnelles sont distinctes.
- Les tentatives de récupération consignent le résultat **avant/après**. HTTP 502, timeout, port étranger, identité ambiguë ou impossibilité d'attestation sont des échecs/alertes documentés, jamais des succès implicites. Les tâches de supervision produisent un résultat exploitable par l'ordonnanceur, sans boucle agressive.
- Les recettes de plateforme couvrent disponibilité système et REST, états sains/dégradés/occupés, arrêt intentionnel, pannes internes déclarées, timeouts, port/PID étranger, redémarrage sûr, préservation des journaux et **absence d'interférence DEV/LAB/Assistant/PROD**.

### Gouvernance des changements

Le présent chapitre définit la **norme cible**, sans prétendre que chaque application y est déjà conforme. Les écarts constatés sont tracés dans des issues, traités par livraisons ciblées avec tests et sans réécriture simultanée des moteurs métier. Chaque dépôt conserve sa version canonique et ses conventions de commit ; tout correctif transversal est audité sur les quatre dépôts avant publication. Ordre de chantier en cours : restaurer ROOT par son watchdog et démontrer la disponibilité HTTP, puis implémenter progressivement les endpoints et tableaux de supervision des autres applications.

## CONTRAT EZS — EXPLOITATION FÉDÉRÉE V1

### Autorité et périmètre

Ce chapitre est **normatif et identique dans les quatre dépôts** `EZS_orchestrator`, `EZScore`, `EZStudio_lab` et `EZStudioLab_assistant`. Il actualise les dispositions plus anciennes qui lui seraient contraires, sans réduire les protections de sécurité, de propriété native, de PROD, d'authentification ni d'isolation.

L'Orchestrator a exactement trois responsabilités à ce stade : **démarrage et arrêt des services**, **supervision** et **gestion de la queue de jobs de plateforme** (ordonnancement, distribution, suivi). Les opérations autorisées s'appliquent aux applications comme des unités, pas à leurs composants internes.

- **EZScore DEV et PROD** sont propriétaires de leurs données, chemins et droits d'accès médias, configuration métier, modèles IA, moteurs et workers internes. PROD est un déploiement contrôlé du code EZScore DEV, avec sa propre configuration.
- **EZStudio_lab** est propriétaire de ses pipelines, presets, modèles IA, moteurs scientifiques, ressources et workers internes.
- **EZStudioLab_assistant** est propriétaire de Llama, de ses modèles IA, ressources et processus internes. L'Orchestrator pilote l'Assistant uniquement à travers son point d'entrée de cycle de vie canonique ; il ne lance ni ne répare directement Llama.
- L'Orchestrator ne choisit ni n'invente de chemin média, modèle, paramètre scientifique ou moteur. Il peut acheminer une configuration validée par le service propriétaire ; il n'en devient pas l'autorité. Ses jobs de plateforme ne remplacent pas les queues et workers internes des applications.

### Démarrage manuel, supervision et récupération

- **Tous les services applicatifs DEV et PROD ont un démarrage initial exclusivement manuel et une intention persistée**. Aucun service arrêté volontairement ne redémarre du seul fait d'une sonde, d'un reboot ou de la réouverture de l'interface. ROOT conserve son watchdog de disponibilité propre et indépendant.
- **DEV (EZScore DEV, LAB, Assistant)** : démarrage et arrêt explicites, supervision continue, **aucune tentative de redémarrage automatique après une panne** par l'Orchestrator. Le diagnostic et l'alerte sont maintenus.
- **PROD (EZScore PROD)** : démarrage initial manuel, supervision continue et **récupération automatique contrôlée seulement après une panne attestée**, si une intention persistée autorise encore `RUNNING` et qu'aucun arrêt volontaire n'a eu lieu. Préflight, attribution univoque des processus, exclusion des PID réutilisés/étrangers, ports libres, temporisation et limite de tentatives sont obligatoires. Un état ambigu entraîne un refus et une alerte, jamais une destruction ou adoption forcée.
- L'interface PROD expose seulement **Normal** et **Maintenance** ; aucun bouton `Démarrer`, `Arrêter` ou `Redémarrer` PROD dans l'interface. L'action initiale manuelle autorisée est une procédure d'exploitation explicite hors de ces boutons. **Maintenance n'est pas STOPPED** : les composants nécessaires restent actifs et supervisés ; le trafic public est traité par le mécanisme de maintenance existant.
- **Un seul Orchestrator** contrôle les modes Normal/Maintenance et la supervision. **Pas de second orchestrateur ni de second service de supervision PROD.** L'instance FrankenPHP native PROD **déjà dédiée** (Caddyfile spécifique, ports 8501/8510/8511) est conservée ; aucun nouveau service Windows ou binaire FrankenPHP spécial PROD n'est requis à ce stade. Une évolution future de l'hébergement nécessitera une étude d'impact et une décision distinctes.
- Toute action suit les mécanismes canoniques et les protections PROD. Les chemins historiques concurrents de démarrage PHP-CGI/Caddy doivent être audités puis retirés par livraison technique distincte ; le présent texte n'autorise pas à les utiliser, ni à les supprimer sans recette.

### Pings hard et soft : preuves indépendantes

- L'Orchestrator sonde séparément **l'identité native et la propriété du processus** et la **connectivité TCP** de chaque port attendu (ping hard). Un port ouvert n'atteste pas la santé métier ni la propriété du processus.
- **Chaque application doit implémenter** un endpoint REST de supervision détaillée, `GET /api/status` ou chemin équivalent documenté, renvoyant son **état global et l'état de tous les composants internes pertinents**, définis par l'application elle-même : frontend, backend, stockage, workers, queues internes, moteurs, modèles et, pour l'Assistant, Llama. Une sonde `GET /health` légère peut être distincte.
- **Avant la livraison de l'endpoint REST**, l'Orchestrator prévoit la requête et affiche `NOT_IMPLEMENTED` si sa non-implémentation est déclarée, ou `NOT_CONFIGURED` si le chemin n'est pas configuré. Ce n'est **ni OK ni KO** et cela **ne bloque ni démarrage, ni supervision TCP, ni récupération PROD sur preuve native admissible**. Une fois l'endpoint déclaré disponible, erreur HTTP, timeout, JSON invalide ou indisponibilité sont des `COLLECTION_ERROR` distinctes du `KO` applicatif. Aucune récupération automatique sur la seule absence de ping soft.
- Les requêtes sont bornées, en lecture seule et sécurisées ; aucun contrôle de santé ne démarre une analyse lourde, un modèle, une migration ou un processus interne.

### Réponse REST applicative cible

Exemple de **schéma**, valeurs illustratives et non observations :

```json
{
  "schema": "ezs.service-status.v1",
  "service": "exemple_service",
  "environment": "dev",
  "version": "VERSION_CANONIQUE",
  "timestamp_utc": "2026-11-03T17:00:00Z",
  "state": "OK",
  "message": "Service opérationnel",
  "components": [
    {
      "id": "composant_stable",
      "state": "OK",
      "message": "Composant disponible",
      "error_code": null
    }
  ]
}
```

- **État global** : `OK` ou `KO`, avec un message clair. Chaque composant possède un identifiant stable, un état `OK`, `KO` ou `UNKNOWN` lorsqu'il n'est pas attestable, un message compréhensible et un code d'erreur optionnel. L'activité (par exemple `BUSY`) est une dimension indépendante et ne vaut pas panne.
- **L'application propriétaire** décide quels éléments sont critiques et agrège leur état global ; l'Orchestrator n'invente ni état interne ni cause racine. Les composants en cascade restent visibles, avec `caused_by` seulement si la relation est attestée par l'application.
- Le JSON source, l'horodatage UTC réel, l'environnement et la version sont distincts des preuves TCP/processus. Les diagnostics exposés sont expurgés de secrets, données personnelles et chemins sensibles.

### Anti-spam et erreurs en cascade : registre de checksums

- La supervision continue à sa fréquence normale même lorsque l'état reste `KO`. **Chaque message nouveau est affiché immédiatement et ajouté au diagnostic ; un message identique déjà signalé pour l'occurrence active n'est jamais répété.**
- Calculer un checksum déterministe (par exemple SHA-256) sur la combinaison canonique **service + environnement + composant + état + code stable + message normalisé**. **Exclure** timestamp, durée, PID volatil, identifiants de requête, compteurs de sondes et autres champs variables sans valeur diagnostique. Ne pas normaliser au point de fusionner deux informations significativement différentes.
- Conserver **un ensemble persistant de checksums par incident et composant**, pas seulement le dernier checksum : les séquences `A,A,A` et `A,B,A,B` n'affichent chacune que les messages `A` et `B` tant qu'ils n'ont pas été résolus. Un nouveau message `C` est ajouté sans effacer `A` ni `B`, même si le service reste globalement `KO`.
- Une **résolution attestée** est affichée une fois et clôt l'occurrence du composant. Si la même erreur revient après résolution, elle est une **nouvelle occurrence** et doit être affichée de nouveau. La résolution d'un composant ne masque pas les erreurs toujours actives des autres. L'incident global est clos lorsque tous les problèmes actifs sont résolus.
- Conserver séparément première et dernière observations UTC, journal des mesures et journal des événements/notifications. Ne pas notifier de nouveau à chaque polling et ne pas inférer de causalité non fournie. Les rappels/escalades périodiques sont désactivés par défaut.

### Standard technique, contrôles et ordre du chantier

- **Étape 1 :** publier le présent contrat dans les quatre dépôts et vérifier le texte identique, avec leur `VERSION` canonique propre.
- **Étape 2 :** finaliser sur l'Orchestrator le démarrage manuel, les intentions persistées, la supervision hard processus/TCP des DEV et PROD, le client REST soft même avant disponibilité des endpoints, les modes Normal/Maintenance PROD et la récupération contrôlée **réservée à PROD**. Ne déclarer opérationnel que ce qui est prouvé sur MAIN.
- **Étape 3 :** aligner les applications **une par une**, chacune propriétaire de son endpoint et de ses composants, puis réaliser leur homogénéisation progressive : PHP 8.5/Symfony, Twig, jQuery, Bootstrap, PHPUnit et contrats de tests selon pertinence ; Python reste interne aux moteurs IA et scientifiques propriétaires. Aucune modification scientifique ni transfert de responsabilité implicite.
- Recettes obligatoires : intention STOPPED, démarrage manuel, état natif ambigu, TCP seul, endpoint REST non implémenté, `OK` et `KO` multi-composants, erreurs de collecte, 100 sondes répétées sans doublon, `A/B/A/B`, résolution partielle, rechute, persistance après relance de ROOT, modes PROD et absence d'effet croisé DEV/LAB/Assistant/PROD.
- **Ce contrat ne déploie aucun composant** et ne prouve aucune fonctionnalité : les changements de code, le retrait des anciennes voies de cycle de vie et toute activation PROD nécessitent des livraisons et recettes séparées, avec sauvegarde, retour arrière et traçabilité.
