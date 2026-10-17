# ⛔ HYGIÈNE DU DÉPÔT — RÈGLE OBLIGATOIRE

## INTERDICTION ABSOLUE DE POLLUER LE DÉPÔT

Le dépôt doit contenir uniquement des fichiers **durables et nécessaires au produit**.

Tous les éléments temporaires ou liés à une intervention ponctuelle doivent être créés **hors du dépôt**, sous :

```text
H:\temp
```

Cette règle s'applique notamment à :

- tests ponctuels, tests de contrat temporaires et scripts de vérification ad hoc ;
- scripts d'installation ou de provisioning ponctuels ;
- scripts `apply-*`, `migrate-*`, `preflight-*`, `hotfix-*`, `rollback-*` temporaires ;
- sauvegardes `*.bak`, `*.before_*`, copies avant migration et snapshots ;
- ZIP de livraison, fichiers d'extraction et README de livraison intermédiaires ;
- logs, traces, dumps, exports de diagnostic, caches et artefacts générés ;
- bases de données locales, fichiers audio/imports, modèles téléchargés et résultats d'analyse ;
- tout autre fichier créé uniquement pour développer, tester, migrer, diagnostiquer ou livrer une modification.

## H:\temp EST JETABLE

`H:\temp` peut être purgé régulièrement et **sans préavis**.

En conséquence :

1. le produit ne doit jamais dépendre d'un fichier temporaire présent dans `H:\temp` ;
2. un fichier nécessaire au fonctionnement permanent doit être conçu comme un vrai composant du produit, nommé sans numéro de patch/hotfix et versionné intentionnellement ;
3. aucun fichier temporaire ne doit être ajouté à Git « pour garder une trace » ;
4. avant tout `git add` ou commit, vérifier explicitement `git status --short` et exclure toute pollution ;
5. ne jamais utiliser `git add .` ou `git add -A` dans un dépôt contenant des fichiers non vérifiés.

## RÈGLE POUR LES ASSISTANTS ET AUTOMATISATIONS

Tout assistant, agent, script ou automatisation intervenant sur ce dépôt doit respecter cette règle par défaut.

**Si un fichier n'est pas clairement un composant durable du produit, il doit être créé dans `H:\temp`, pas dans le dépôt.**

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
