# EZScore_v1 — R39.5 FULL Lyrics diagram + Catalog fix

## Base unique

Ce livrable cible directement le `master` GitHub :

`93d117e60af0e05b078e6c845e9482f8deccef92`
`EZScore_v1_R39_4_WORKER_RESILIENCE`

Il ne dépend d'aucun R39.5 / R39.5A / R39.5A1 local.

Avant installation, jeter/discard tous les essais locaux R39.5* et revenir au master propre.

## 1. Diagramme dans Lyrics : réimplémentation au bon endroit

Le diagramme n'est plus ajouté dans le `chordslab-stage` externe.

Il est créé directement DANS :

`lyrics-ribbon-stage`

C'est le vrai conteneur visuel qui contient :
- le rectangle bleu ;
- les cellules d'accord ;
- les syllabes.

La stage réserve maintenant explicitement une bande haute de 174 px.

Disposition :

```text
lyrics-ribbon-stage
┌─────────────────────────────────────────────┐
│          diagramme partagé Chords           │  0..174
│                                             │
├──────── zone / accords ─────────────────────┤  174..266
│                                             │
├──────── syllabes ───────────────────────────┤  284...
└─────────────────────────────────────────────┘
```

Le diagramme :
- utilise exactement `ezscore-chord-diagram.js/css` ;
- garde la taille Chords : 150 px / SVG 128 px ;
- est centré sur `focusX()` ;
- suit `timeline.activeEventAt(chords, ms)` ;
- respecte « Afficher les accords guitare » ;
- ne duplique aucune shape guitare.

## 2. Régression CatalogController

Correction du HTTP 500 :

`Undefined variable $requestedStatus`

Le status posté est maintenant lu avant `applyStatus()` :

```php
$requestedStatus = SongStatus::tryFrom((string) $request->request->get('status', ''))
    ?? $song->getStatus();
```

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R39_5_FULL_LYRICS_DIAGRAM_AND_CATALOG_FIX.zip" -C H:\EZScore_v1

H:\EZScore\.venv-py313\Scripts\python.exe .\_r39_5_full\scripts\apply_r39_5_full.py H:\EZScore_v1

H:\EZScore\.venv-py313\Scripts\python.exe .\_r39_5_full\tests\r39_5_full_contract.py H:\EZScore_v1

H:\EZScore\.venv-py313\Scripts\python.exe -m py_compile .\worker_app\ezscore_analysis_worker.pyw

php bin\console lint:container
php bin\console cache:clear

git diff --check
git status --short
```

Attendu :

```text
R39_5_FULL_LYRICS_DIAGRAM_AND_CATALOG_FIX_INSTALL_OK
R39_5_FULL_LYRICS_DIAGRAM_AND_CATALOG_FIX_CONTRACT_OK
```

## Validation visuelle Lyrics

- diagramme de même taille que Chords ;
- diagramme dans la bande supérieure du grand cadre ;
- rectangle bleu commence sous le diagramme ;
- axe horizontal diagramme = axe bleu ;
- timeline et syllabes restent synchronisées ;
- toggle diagramme immédiat.

## Important

Si l'installateur échoue : STOP. Ne pas lancer le test/cache ensuite.
