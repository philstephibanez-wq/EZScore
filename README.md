# EZScore R16 — publication par version, édition et release

## Base

R16 repart du master R15 poussé le 12/09/2026.

Le moteur d'analyse reste inchangé :

```text
V29_R14_BALANCED_MIDI_EDITORIAL
```

Aucune modification de l'analyse harmonique, Whisper ou MIDI.

## Nouveau contrat éditorial

Les snapshots techniques restent internes.

L'utilisateur manipule désormais trois notions distinctes :

```text
Version × Édition × Release
```

Exemples :

```text
V1.8 · Simplifiée · R1
V1.8 · Avancée · R1
V1.8 · Avancée · R2
V1.9 · Simplifiée · R1
```

### Enregistrer les modifications

Le bouton :

```text
💾 Enregistrer les modifications
```

- sauvegarde un snapshot technique ;
- met à jour la date de dernière modification ;
- met à jour le commentaire ;
- conserve la version cible ;
- conserve l'édition cible ;
- ne crée aucune publication ;
- n'incrémente pas la version éditoriale.

### Publier

Le bouton :

```text
🌍 Publier Vx · Édition
```

crée une publication complète avec son propre snapshot.

Le numéro de release est calculé par couple :

```text
Version + Édition
```

Une nouvelle publication de `V1.8 · Avancée` produit donc `R2` sans modifier `V1.8 · Simplifiée · R1`.

## Éditions

Éditions proposées :

- Simplifiée
- Standard
- Avancée
- Personnalisée

Une édition personnalisée peut recevoir un nom libre, par exemple `Fingerstyle`.

Après publication, deux actions sont distinguées :

```text
Nouvelle édition de cette version
Préparer une nouvelle version
```

La première conserve la version publiée.
La seconde propose la version suivante, qui reste modifiable manuellement.

## Migration R15

Une ancienne entrée R15 seulement « validée » n'est plus considérée comme une version publiée.

Elle revient en état :

```text
Modification en cours
```

et son ancien numéro est repris comme version cible.

Les anciennes publications restent visibles comme éditions `Standard`.

## Répertoire

Chaque morceau affiche maintenant :

- une miniature de pochette si disponible ;
- son état ;
- sa version publiée/cible ;
- son édition ;
- son release ;
- la date de dernière modification ;
- le commentaire éditorial.

Les numéros internes de `analysis_versions` sont affichés comme `Snapshots`, jamais comme versions éditoriales.

## Pochette

En mode Éditer :

- aperçu de la pochette ;
- upload JPG / JPEG / PNG / WEBP ;
- remplacement ;
- suppression.

Les images sont stockées dans :

```text
data/covers/
```

SQLite ne contient que le chemin du fichier.

La suppression complète d'une chanson supprime aussi sa pochette.

## Schéma SQLite

Migrations rétrocompatibles :

### songs

```text
cover_path TEXT
```

### song_editorial_versions

```text
version_label TEXT
edition_label TEXT
```

### song_workflow

```text
target_version_label TEXT
target_edition_label TEXT
```

## Livrable

Le ZIP contient exactement :

```text
EZScore.py
readme.md
```

## Mise à jour locale

```bat
cd /d H:\EZScore
git pull
python -m py_compile EZScore.py
streamlit run EZScore.py
```
