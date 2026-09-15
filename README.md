# EZScore — sensibilité vocale + compensation d'écoute

Branche cible :

```text
feature/vocal-midi-analysis
```

Cette livraison reste strictement expérimentale et modifie uniquement :

```text
ezscore/analysis/vocal.py
```

## 1. Notes faibles mieux récupérées

Le seuil pYIN principal devient légèrement plus permissif :

```text
Demucs vocals : 0.55 → 0.48
fallback mix   : 0.72 → 0.66
```

Mais les frames faibles ne sont pas acceptées aveuglément.

Une frame située sous le seuil principal peut être récupérée uniquement si :

```text
- pYIN la considère encore comme vocale
- sa confiance reste proche du seuil principal
- son énergie RMS est suffisante par rapport à la piste du morceau
- sa hauteur est cohérente avec une frame forte voisine
```

Le seuil RMS est **relatif au morceau**, jamais absolu.

Objectif : récupérer surtout les attaques et fins de notes peu puissantes sans
réintroduire beaucoup de résidus instrumentaux.

## 2. Filtre anti-vibrato conservé

Les réglages validés précédemment restent inchangés :

```text
filtre médian        : 7 frames
hystérésis           : 70 cents
nouvelle note stable : 100 ms
```

## 3. Compensation de latence dans le lecteur uniquement

La piste MIDI chant du lecteur est avancée de :

```text
40 ms
```

Important :

```text
timeline analytique vocale : NON décalée
MIDI chant exporté         : NON décalé
analyse des blocs          : NON décalée
lecteur comparatif         : -40 ms seulement
```

La correction ne modifie donc aucune donnée canonique.

## 4. Cache

Le schéma vocal passe à :

```text
3
```

Il faut recalculer la voix une fois pour chaque morceau afin d'utiliser les
nouveaux seuils.

## Installation

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
tar -xf "$env:USERPROFILE\Downloads\EZScore_FEATURE_VOCAL_SENSITIVITY_LATENCY.zip" -C H:\EZScore

python -m py_compile .\ezscore\analysis\vocal.py
python -m py_compile .\EZScore.py
python -m compileall -q .\ezscore

python -m streamlit run .\EZScore.py
```

## Recette conseillée avec Le Sud

1. `Analyser / recalculer la voix`.
2. Laisser `Alto Sax`.
3. Mettre `Volume accords MIDI = 0`.
4. Comparer MP3 + chant MIDI.
5. Vérifier :
   - davantage de notes faibles présentes ;
   - pas de retour massif des notes parasites de vibrato ;
   - saxo légèrement mieux calé sur les attaques vocales.
6. Télécharger aussi le MIDI chant : il doit rester sur les timestamps
   analytiques non compensés.

Ne pas fusionner dans `master` avant validation.
