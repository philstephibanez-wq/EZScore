# EZScore_STEM_LYRICS_VISIBLE_R1c

Cette livraison remplace R1/R1b.

## Ce qui était faux dans R1b

R1b contenait encore un ancrage généré incorrectement pour le bloc `player_words`.
Il cherchait un texte qui n'existait pas exactement dans le fichier. Le patch a
donc été bloqué avant écriture.

R1c supprime complètement ce changement non nécessaire.

## Périmètre R1c

Un seul changement fonctionnel :
- restauration du moteur de placement du conducteur STEM qui fonctionnait avant
  le branchement du layout visuel partagé de l'éditeur Paroles.

Sécurités :
- aucune modification de `player_words` ;
- aucune modification du mixer ;
- aucune modification du transport ;
- aucune modification de la source des beats/accords ;
- aucune modification du workflow ;
- identité du composant navigateur `r1 -> r3` ;
- couleur des paroles explicitée.

Le patch construit le fichier complet en mémoire, exécute `ast.parse()` sur ce
fichier complet, puis seulement copie le candidat vers le repo.

## Application

```powershell
cd H:\EZScore

tar -xf "$env:USERPROFILE\Downloads\EZScore_STEM_LYRICS_VISIBLE_R1c.zip" -C H:\EZScore

$env:PYTHONPATH = "H:\EZScore"

.\.venv-py313\Scripts\python.exe .\scripts\apply_stem_lyrics_visible_r1c.py

.\.venv-py313\Scripts\python.exe .\scripts\test_stem_lyrics_visible_r1c_contract.py
```

Attendu :

```text
STEM LYRICS VISIBLE R1c CONTRACT OK
patched Python syntax: OK
composed player import: OK
known-good STEM conductor restored: YES
all supplied words materialized: YES
component identity r3: YES
mixer / transport / payload source: UNCHANGED
```

Aucun commit ni push.
