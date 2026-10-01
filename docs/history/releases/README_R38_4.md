# EZScore_v1 R38.4 — sections déclaratives + alignement du début

Base : `master` poussé au commit `f0b35e90fb60e5e021583163d1d56d39e5519ac6`
(`EZScore_v1_R38_3_PLAYER_UI_SYNC_FIX`).

## Sections

La source éditable est la vérité :

- `[Intro]` => section `Intro`
- `Intro:` => section `Intro`
- `[Final]`, `Solo:`, `[Partie musicale]`, etc. fonctionnent de la même façon
- aucune whitelist
- aucune section ajoutée si elle n'est pas déclarée
- les sections instrumentales existent même sans lyric event

La barre de navigation est construite depuis la source. Les timestamps des sections
avec paroles viennent des mots ancrés ; une section purement instrumentale est placée
sur la première frontière de beat disponible après la section précédente.

## Alignement des paroles

Le problème du début venait du global `SequenceMatcher` : avec des refrains/couplets
répétés, il peut choisir une occurrence plus tardive du morceau et ignorer la première
phrase.

R38.4 cherche d'abord **chronologiquement** une vraie grappe acoustique locale
(plusieurs mots cohérents), puis lance l'alignement depuis cette position.

Conséquences :
- un `Je` isolé/halluciné à t=0 ne suffit pas ;
- `Je vous parle...` réellement détecté vers l'entrée du chant devient l'ancre ;
- les répétitions plus tardives ne peuvent plus voler l'ancre initiale ;
- seulement 1 à 3 mots manquants juste avant une vraie ancre peuvent être reconstruits localement ;
- aucune longue intro instrumentale n'est remplie artificiellement.

R38.3 utilisait déjà la source/original pour `align`; cela est conservé.

## Régressions explicitement protégées

R38.4 ne remplace pas :
- le player R38.3 ;
- le volume rapide/master ;
- la persistance du diagramme ;
- le polling/barre de progression R38.2A.

Le contrat vérifie la présence du polling de progression.

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R38_4_SECTIONS_ALIGNMENT_FIX.zip" -C H:\EZScore_v1

python .\scripts\install_r38_4.py H:\EZScore_v1

python -m py_compile .\analysis\lyrics_timeline_analysis.py
node --check .\public\assets\js\lyricslab-r37.js

php .\tests\r38_4_contract.php H:\EZScore_v1

php bin\console cache:clear

git diff --check
git status --short
```

Attendu :

```text
R38_4_INSTALL_OK
R38_4_CONTRACT_OK
```

Ensuite :
1. `Ctrl+F5`
2. relancer **Analyser les paroles**
3. vérifier `Intro`, `Final` et une section personnalisée
4. comparer l'entrée de `Je vous parle...` avec le sous-titrage externe
