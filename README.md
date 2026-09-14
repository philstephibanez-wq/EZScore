# EZScore — lecteur Analyse compact + sélection instrument

Cette livraison est un delta sur `EZScore_R30_SPEED_PLAYER_CLEANUP`.

## Corrections

### Instrument MIDI

Le lecteur `Analyse` permet à nouveau de choisir :

```text
Electric Guitar (clean)
Acoustic Grand Piano
```

Le changement d'instrument ne relance pas Whisper, l'analyse harmonique ni R33.
Il ne reconstruit que les événements MIDI.

### Suppression des diagrammes guitare dans Analyse

La case :

```text
Diagrammes guitare
```

n'est plus affichée dans le lecteur de la vue Analyse.

Les diagrammes restent disponibles dans les vues d'édition qui utilisent le
lecteur complet.

### Suppression de la grande marge noire

La marge provenait du lecteur complet, qui réservait :

```text
835 px
```

pour :
- bandeau de mesures;
- diagrammes;
- paroles synchronisées.

Or la vue Analyse ne leur fournissait aucune donnée.

Analyse utilise désormais un composant compact de :

```text
285 px
```

avec uniquement :

```text
titre / artiste
audio MP3
volume chanson
volume MIDI
chargement synthé
état du synthé
```

### Texte obsolète supprimé

Le message :

```text
La lecture MIDI synchronisée est disponible dans Grille > Jouer.
```

est neutralisé car la vue `Jouer` n'existe plus.

## Performance

Le log fourni confirme que le correctif R33 fonctionne :

```text
structure.persisted.reuse
```

La structure persistée a été réutilisée en quelques millisecondes.

Sur l'extrait fourni, le coût principal restant au premier affichage Analyse est :

```text
waveform_preview_cache ≈ 6.10 s
timeline.create_harmonic_timeline ≈ 6.23 s
player.render ≈ 0.28 s
MIDI bridge ≈ 0.35 s
```

Donc le lecteur MIDI n'est plus la cause de la lenteur principale.

## Fichiers livrés

```text
.gitignore
ezscore/ui/app_shell.py
ezscore/midi/analysis_player.py
readme.md
```

Aucune DB.
Aucun audio.
Aucun cover.
Aucun dossier de livraison parasite.

## Installation

```powershell
cd H:\EZScore

tar -xf "$env:USERPROFILE\Downloads\EZScore_R30_PLAYER_UI_FIX.zip" -C H:\EZScore

python -m py_compile .\ezscore\midi\analysis_player.py
python -m py_compile .\ezscore\ui\app_shell.py
python -m py_compile .\EZScore.py
python -m compileall -q .\ezscore

python -m streamlit run .\EZScore.py
```

## Recette

Dans `Analyse > Comparaison audio / accords` :

1. sélectionner `Acoustic Grand Piano`;
2. charger le synthé;
3. vérifier le volume MP3;
4. vérifier le volume MIDI;
5. lancer la lecture;
6. repasser sur `Electric Guitar (clean)`.

La case `Diagrammes guitare` ne doit plus apparaître et le lecteur doit se
terminer immédiatement après son texte d'état, sans grande zone noire.
