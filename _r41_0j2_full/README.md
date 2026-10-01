# EZScore_v1 — R41.0J2 tonalité générale depuis accords HQ

Base GitHub exacte : `feb01ace289f751cc6a64e1aa6478fc3b5b59bb4` (`EZScore_v1_R41_0I_CHORDS_LYRICS_COMPACT_TOGGLE`).

## Problème

La détection d'accords HQ est désormais bonne avec `lv-chordia`, mais la tonalité
générale restait calculée séparément par moyenne chroma Krumhansl. Cette méthode
peut confondre facilement une tonalité mineure avec sa relative majeure
(ex. E mineur / G majeur).

## Correction

La tonalité est maintenant dérivée en priorité des **segments continus lv-chordia** :

- pondération par durée réelle de chaque segment ;
- conformité degré + qualité d'accord pour les 24 tonalités majeur/mineur ;
- poids renforcé du véritable accord de tonique ;
- reconnaissance du **V / V7 majeur en tonalité mineure** comme preuve harmonique forte ;
- léger bonus de terminaison sur la tonique ;
- chroma audio conservé uniquement comme **tie-break secondaire**.

Le moteur d'accords, la projection sur les beats et les trois profils restent inchangés.

Le JSON conserve `"key"` et ajoute :
- `"key_confidence"`
- `"key_method"`

Méthode normale :
`lv-chordia-duration+chroma-tiebreak`

## Cache Symfony

Comme demandé, l'installateur exécute systématiquement :

```powershell
php bin\console cache:clear --env=dev
php bin\console cache:clear --env=prod
```

En cas d'échec, rollback du fichier puis STOP.

## Correctif J2

J1 corrige uniquement l'installateur : le package J avait injecté un `\\n` littéral devant `def diatonic_roots`, provoquant le `SyntaxError`. Le rollback de J a bien restauré le fichier d'origine.

## Installation

```powershell
cd H:\EZScore_v1
git status --short
git rev-parse HEAD
```

Attendu : dépôt propre et HEAD `feb01ace289f751cc6a64e1aa6478fc3b5b59bb4`.

Puis :

```powershell
tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R41_0J2_HQ_SONG_KEY.zip" -C H:\EZScore_v1

H:\EZScore_v1\.venv-py313\Scripts\python.exe .\_r41_0j2_full\scripts\apply_r41_0j2.py H:\EZScore_v1
```

Attendu final :

`R41_0J2_HQ_SONG_KEY_INSTALL_OK`

Sinon : **STOP**.

Puis seulement :

```powershell
H:\EZScore_v1\.venv-py313\Scripts\python.exe .\_r41_0j2_full\tests\r41_0j2_contract.py H:\EZScore_v1

git diff --check
git status --short
```

Attendu :

`R41_0J2_HQ_SONG_KEY_CONTRACT_OK`

## Test fonctionnel

Réanalyser `Dance me to the end of love`.

Le but n'est pas de coder une tonalité spécifique au morceau : le test vérifie que
la tonalité affichée est désormais cohérente avec la progression HQ détectée et,
en particulier, que la relative majeure n'est plus choisie lorsque les accords
mineurs + dominante harmonique indiquent clairement la tonalité mineure.
