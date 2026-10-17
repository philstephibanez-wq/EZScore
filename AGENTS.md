# AGENTS.md

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
