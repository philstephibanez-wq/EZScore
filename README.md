# EZScore_LYRICS_SOURCE_PERSIST_R1

Base distante vérifiée avant livraison :

```text
master = 21e051ad58f1e0ed890fbd7afdebe973299b0ec5
EZScore_ANALYSIS_PLAYER_R1b
```

## Principe

Le bloc `Texte exact du chant` devient la source éditable persistante de la
chanson.

```text
bloc texte utilisateur
    ↓ sauvegarde durable
SQLite + lyrics_input.txt
    ↓
MMS_FA
    ↓
mots horodatés
```

Modifier le bloc ne supprime pas le texte. Cela signifie seulement que les
timestamps doivent être réalignés.

## Réouverture et migration

À l'ouverture d'une chanson, priorité :

```text
1. source utilisateur persistée
2. source_text de l'alignement forcé
3. lyric_block_edits historiques
4. analyses.whisper_json historique
5. analysis_versions.whisper_json historique
```

Une source historique récupérée est immédiatement copiée dans le nouveau
stockage durable.

Le widget utilise `on_change` : un champ vide transitoire ne réécrit plus
aveuglément la source à chaque rendu.

## Application

```powershell
cd H:\EZScore

tar -xf "$env:USERPROFILE\Downloads\EZScore_LYRICS_SOURCE_PERSIST_R1.zip" -C H:\EZScore

.\.venv-py313\Scripts\python.exe .\scripts\apply_lyrics_source_persist_r1.py

.\.venv-py313\Scripts\python.exe -m py_compile `
  .\ezscore\integration\choir_pipeline.py `
  .\scripts\test_lyrics_source_persist_r1_contract.py

.\.venv-py313\Scripts\python.exe .\scripts\test_lyrics_source_persist_r1_contract.py
```

Attendu :

```text
PATCH OK
 - bloc utilisateur persisté à chaque modification
 - rechargement automatique à l'ouverture
 - migration automatique lyric_block_edits -> source canonique
 - migration fallback analyses.whisper_json
 - migration fallback analysis_versions.whisper_json
 - retours à la ligne conservés quand disponibles

LYRICS SOURCE PERSIST R1 CONTRACT OK
...
```

Puis redémarrer Streamlit.

## Test

Sur la chanson où le champ était vide :
- ouvrir `2 · Paroles`;
- le bloc doit se remplir automatiquement depuis la meilleure source historique ;
- modifier une ligne ;
- passer sur une autre chanson puis revenir ;
- la modification doit toujours être là ;
- si le texte diffère de l'alignement courant, le bouton de réalignement reste disponible.

Aucune réanalyse STEM n'est nécessaire.
