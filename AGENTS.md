# AGENTS.md

## SOURCE DE VÉRITÉ GITHUB — PRÉFLIGHT OBLIGATOIRE

- GitHub est la source de contexte persistante, **avant** toute réponse opérationnelle ou modification : consulter les dépôts concernés, `AGENTS.md`, contrats, README, issues/handoffs, décisions, historique Git et changements récents. Ne jamais remplacer une vérification possible par une supposition ou par le souvenir d'un ancien chat.
- Consulter également le dépôt privé `philstephibanez-wq/EZStudio_Run_Reports` pour les rapports existants. Les rapports sont des copies expurgées ; la base MAIN reste autorité pour les résultats métier. Ne jamais prétendre disposer d'un log non publié ni d'une observation temps réel.
- L'accès GitHub direct à l'assistant est autorisé dans ce chantier lorsqu'il est demandé par le mainteneur. Les handoffs plus anciens qui interdisaient une écriture directe sont historiques ; signaler les contradictions et préférer les consignes explicites actuelles du mainteneur sans effacer l'historique.
- Pour chaque chantier, mettre à jour l'issue/handoff concerné : état prouvé, versions et SHA, décisions, limites, risques, tests **exécutés** versus à exécuter, action suivante et conditions de reprise. Ne jamais présenter un test ajouté mais non exécuté comme validé.
- Pour les machines MAIN/XPS, ne demander une commande locale que lorsque les données nécessaires ne sont réellement pas accessibles par GitHub ou les rapports existants. Ne publier aucun secret, jeton, trace HTTP brute, audio ou donnée privée.
- Avant publication, contrôler l'intégralité des contrats applicables et les écarts avec les handoffs ; toute non-conformité est bloquante, pas une remarque facultative.

## PRÉFIXE DE COMMIT ET CONFORMITÉ DE LIVRAISON — OBLIGATOIRE

- Tout **nouveau** message de commit commence exactement par `[vVERSION] `, où `VERSION` est la valeur exacte du fichier `VERSION` dans ce même commit, suivi de `type(périmètre): résultat obtenu`, en français. Exemple : `[v1.0i] fix(dev): imposer la version réelle dans le préfixe de commit`. Le préfixe littéral `[v]` est interdit.
- Corps de message multiligne : `Contexte`, `Modifications`, `Validation`, `Impact`, et `Limites / risques` si nécessaire.
- Un changement livré comprend le code durable, ses tests et l'incrément de `VERSION` dans **un commit cohérent**, sauf impossibilité technique explicitée avant écriture. Ne jamais créer une succession de commits incomplets en prétendant que chacun satisfait au contrat.
- Avant toute publication : confirmer fichiers concernés, absence de fichiers temporaires, version, préfixe, messages, vérifications statiques et tests pertinents. Aucun historique partagé n'est réécrit de force.
- Un test CI qui échoue ne bloque pas à lui seul un push direct tant qu'une protection de branche n'impose pas le statut. Ne jamais annoncer un blocage effectif avant sa configuration et sa vérification.

## ⛔ RÈGLE ABSOLUE — FICHIERS TEMPORAIRES

- **Aucun fichier temporaire, test ponctuel, installateur ponctuel, script apply/migrate/preflight/hotfix/rollback, backup, ZIP de livraison, log, dump, cache, export de diagnostic, artefact généré ou fichier de migration intermédiaire ne doit être créé dans ce dépôt.**
- Tous ces fichiers doivent être créés sous `H:\temp`.
- `H:\temp` est **jetable** et peut être purgé régulièrement **sans préavis**.
- Le produit ne doit donc **jamais dépendre** d'un fichier présent dans `H:\temp`.
- Seuls les composants durables et réellement nécessaires au produit ont leur place dans le dépôt.
- Avant tout staging/commit : vérifier `git status --short` et exclure toute pollution.
- Ne pas utiliser `git add .` ou `git add -A` tant que des fichiers non vérifiés sont présents.
- Si le caractère durable d'un fichier est douteux, **il va dans `H:\temp` par défaut**.

Voir aussi `REPOSITORY_HYGIENE.md`.

## CONTRAT TRANSVERSAL — UTF-8 ET LISIBILITÉ DES SOURCES

**Obligatoire dans tous les correctifs, scripts d'installation et livraisons.**

- PHP, Twig, Python, JavaScript, CSS, JSON, YAML, Markdown et scripts applicatifs : **UTF-8 sans BOM**. Ne jamais altérer la sémantique d'un fichier lors d'une conversion.
- Respecter le charset UTF-8 sur toute la chaîne : réponse HTTP (`Content-Type`), balise HTML `<meta charset="utf-8">`, sérialisation JSON, stockage et rendu navigateur. Vérifier les caractères accentués **dans l'interface rendue**, pas seulement dans le code source.
- Rejeter les chaînes corrompues (*mojibake*) comme `RÃ©vision`, `Ã©`, `Ã¨`, `â€™`, `Â` en contexte français ; rechercher la cause d'encodage, ne pas appliquer de substitutions aveugles.
- Les templates **Twig doivent rester multilignes, lisibles et structurés** : indentation de 4 espaces par niveau, `{% if %}`, `{% for %}`, `{% block %}`, `{% endif %}` et `{% endfor %}` isolés par ligne, éléments HTML structurels sur des lignes séparées, attributs répartis sur plusieurs lignes si nécessaire.
- Les scripts JS/CSS sources ne sont pas minifiés dans le dépôt ; les artefacts compilés restent distincts. Ne pas reformater massivement les fichiers historiques sans demande explicite ni tests de non-régression.
- Conserver les fins de ligne conformément à `.gitattributes` ; **CRLF/LF n'est pas un diagnostic d'UTF-8**.
- Avant validation : décodage UTF-8 strict sans BOM, contrôle de mojibake, `php -l`, `lint:twig` et tests contractuels pertinents, puis vérification visuelle des libellés français. Aucun simple lint de syntaxe ne vaut validation d'encodage ou de présentation.
- Ce contrat s'applique à tous les dépôts EZScore, EZStudio_lab, EZStudioLab_assistant et EZS_orchestrator, y compris aux contributions des assistants et automatisations.


## CONTRAT DES MESSAGES DE COMMIT — OBLIGATOIRE

Chaque commit publié doit être intelligible sans ouvrir le diff. Rédiger **en français**, avec :

- Un titre précis au format `[vVERSION] type(périmètre): résultat obtenu` (par exemple `[v1.4n] fix(profile): rejeter les preuves CLAP non indépendantes`). La valeur `VERSION` doit être identique au fichier `VERSION` inclus dans le commit ; ne jamais écrire le préfixe littéral `[v]`. Types usuels : `fix`, `feat`, `refactor`, `test`, `docs`, `chore`.
- Un **corps de message multiligne** expliquant `Contexte`, `Modifications`, `Validation`, `Impact` et, si nécessaire, `Limites / risques`.
- Dans `Validation`, distinguer explicitement les tests exécutés des tests seulement ajoutés ou non exécutés. Ne jamais affirmer une réussite non constatée.
- Dans `Impact`, indiquer les dépôts ou composants touchés, les éventuels redémarrages/déploiements, et si les modèles, presets scientifiques, données et interfaces sont inchangés.
- Ne pas masquer plusieurs changements fonctionnels indépendants sous un intitulé générique (`fix`, `update`, `VERSION`, `cleanup`).
- **Un commit de livraison cohérent par version**, réunissant code durable, tests et `VERSION`, autant que les outils de publication le permettent. Les commits intermédiaires éventuels doivent eux aussi être descriptifs. Aucun réécriture forcée de l'historique déjà publié.
- Si une contrainte du dépôt exige de modifier `VERSION`, la respecter, y compris pour les livraisons documentaires.

Cette règle s'applique aux contributions humaines, assistants et automatisations sur tous les dépôts du projet.
