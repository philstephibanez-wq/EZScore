# EZScore — branche `feature/vocal-midi-analysis`

Base de départ :

```text
master validé : 4e325e796ab32b4483127b395b1345c865fa3578
branche       : feature/vocal-midi-analysis
```

Cette livraison est volontairement expérimentale et additive.

## Objectif

Ajouter une quatrième timeline primaire indépendante :

```text
audio original
  ├─ accords
  ├─ paroles
  ├─ phonèmes
  └─ hauteur vocale / notes chantées
```

Puis utiliser la mélodie chantée comme **signal secondaire** pour affiner la
proposition de blocs, sans jamais modifier les timestamps des autres timelines.

## Analyse vocale

Nouveau module :

```text
ezscore/analysis/vocal.py
```

Pipeline :

```text
audio
 -> Demucs vocals si disponible
 -> sinon fallback sur le mix
 -> librosa.pyin
 -> F0
 -> quantification en notes MIDI
 -> segmentation temporelle
 -> cache JSON
```

Cache :

```text
data/analysis/vocal_pitch/<audio_hash>.json
```

Le cache est séparé de la DB et n'altère aucune analyse existante.

## MIDI du chant

Dans :

```text
Analyse > Comparaison audio / accords
```

un nouveau bloc apparaît :

```text
🎤 Mélodie chantée — expérimental
```

Bouton :

```text
Analyser / recalculer la voix
```

Après analyse :

```text
⬇ Télécharger le MIDI du chant
```

Le MIDI est monophonique et conserve les timestamps audio absolus.

## Raffinement des blocs

Le simple calcul de la mélodie **ne change pas les blocs**.

Il faut explicitement cliquer :

```text
Recalculer les blocs avec la mélodie
```

Le comportement est alors :

```text
1. suppression uniquement des structure_blocks persistés
2. recalcul R33 habituel
3. lecture de la timeline vocale persistée
4. raffinement conservateur des frontières
5. nouvelle persistance des blocs
```

Règles de sécurité :

```text
- aucune nouvelle découpe périodique
- aucune modification accords/paroles/phonèmes
- aucune modification des timestamps audio
- déplacement d'une frontière R33 : maximum ±2 mesures
- déplacement seulement si la nouveauté mélodique est clairement plus forte
- sans timeline vocale : résultat R33 strictement inchangé
```

Donc le moteur vocal est un **critère secondaire**, jamais le maître.

## Demucs

Aucune nouvelle dépendance obligatoire.

Si Demucs est déjà installé :

```text
Demucs vocals + pYIN
```

Sinon :

```text
mix original + pYIN
```

Le fallback est explicitement indiqué dans l'UI et utilise un seuil de confiance
plus strict.

Pour installer Demucs ultérieurement :

```powershell
python -m pip install demucs
```

Ce n'est pas nécessaire pour démarrer les tests.

## Logs

Les nouvelles traces vont toujours dans :

```text
H:\EZScore\data\logs\ezscore_perf.log
```

Événements :

```text
vocal_pitch.analyse
vocal_pitch.analyse.result
structure.vocal.refine
structure.vocal.refine.result
structure.vocal.refine.requested
```

## Fichiers livrés

```text
ezscore/analysis/vocal.py
ezscore/ui/app_shell.py
readme.md
```

Aucune DB.
Aucun MP3.
Aucun fichier de cache vocal.
Aucun dossier racine parasite.

## Installation sur la branche

Vérifier d'abord :

```powershell
cd H:\EZScore
git branch --show-current
```

Résultat obligatoire :

```text
feature/vocal-midi-analysis
```

Puis :

```powershell
tar -xf "$env:USERPROFILE\Downloads\EZScore_FEATURE_VOCAL_MIDI_ANALYSIS.zip" -C H:\EZScore

python -m py_compile .\ezscore\analysis\vocal.py
python -m py_compile .\ezscore\ui\app_shell.py
python -m py_compile .\EZScore.py
python -m compileall -q .\ezscore

python -m streamlit run .\EZScore.py
```

## Recette recommandée

Pour un morceau déjà analysé :

1. ouvrir `Analyse`;
2. vérifier que le lecteur accords MP3+MIDI fonctionne toujours;
3. cliquer `Analyser / recalculer la voix`;
4. télécharger `MIDI du chant`;
5. écouter / vérifier grossièrement la mélodie;
6. noter les blocs actuels;
7. seulement ensuite cliquer `Recalculer les blocs avec la mélodie`;
8. comparer le découpage avant/après;
9. vérifier `ezscore_perf.log`.

Ne pas fusionner cette branche dans `master` avant comparaison sur plusieurs
chansons.
