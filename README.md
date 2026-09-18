# EZScore — Répertoire général, playlists et notation collective

Ce livrable part de la baseline fonctionnelle R5.10 de l'éditeur Paroles et
n'altère aucun fichier du player ni aucun template de la timeline R5.10.

## Fonctionnalités

L'accueil Répertoire possède maintenant deux vues :

- **Répertoire général**
- **Playlists**

### Répertoire général

Chaque chanson conserve les fonctions existantes principales :

- tri titre / auteur ;
- recherche ;
- index alphabétique ;
- pochette ;
- état éditorial ;
- choix de version ;
- éditeur ;
- Voir / Modifier / Supprimer.

S'ajoutent :

- note collective moyenne sur 5 ;
- nombre de votes ;
- vote 1 à 5 étoiles pour chaque utilisateur enregistré ;
- bouton `＋` pour ajouter la chanson à une playlist existante ;
- création d'une nouvelle playlist directement depuis ce bouton.

Une note utilisateur remplace sa note précédente. La note affichée est :

```text
AVG(song_ratings.rating)
```

sur l'ensemble des utilisateurs ayant voté.

### Playlists

Chaque utilisateur enregistré ne voit que ses propres playlists.

Fonctions :

- créer une playlist ;
- supprimer une playlist ;
- ajouter une chanson depuis `＋` dans le Répertoire ;
- retirer une chanson ;
- ouvrir une chanson ;
- conserver l'ordre d'ajout grâce à `position`.

Supprimer une playlist ou retirer une chanson ne supprime jamais la chanson du
Répertoire général.

## Modèle SQLite

Tables ajoutées automatiquement :

```text
song_ratings
- user_id
- audio_hash
- rating (1..5)
- created_at
- updated_at
PRIMARY KEY(user_id, audio_hash)

user_playlists
- playlist_id
- user_id
- name
- created_at
- updated_at
UNIQUE(user_id, name)

user_playlist_items
- playlist_id
- audio_hash
- position
- created_at
PRIMARY KEY(playlist_id, audio_hash)
```

## Templates SCORE

L'UI visuelle est volontairement externalisée :

- `templates/views/catalog-home.score`
- `templates/views/catalog-song.score`
- `templates/views/catalog-rating.score`
- `templates/views/catalog-playlist.score`
- `templates/views/catalog-playlist-song.score`

La logique interactive reste dans Python ; styles, structure HTML et présentation
peuvent ainsi évoluer sans réécrire le stockage.

## Modularisation

Nouveaux modules :

- `ezscore/catalog_social.py` : persistence notation / playlists ;
- `ezscore/ui/catalog_home.py` : surface Streamlit.

`ezscore/ui/__init__.py` installe la surface Répertoire comme les hooks déjà
utilisés pour le player R12c et l'éditeur timeline. Le bloc historique du
Répertoire dans `EZScore.py` n'est pas modifié : une fois la nouvelle surface
rendue, `st.stop()` empêche simplement son double affichage.

## Installation

Décompresser directement dans `H:\EZScore` :

```powershell
cd H:\EZScore

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\EZScore_CATALOG_PLAYLISTS_R1.zip" `
  -DestinationPath . `
  -Force
```

Contrôles :

```powershell
python -m py_compile `
  .\ezscore\catalog_social.py `
  .\ezscore\ui\catalog_home.py `
  .\ezscore\ui\__init__.py

git diff --check
git status --short
```

Lancer ensuite :

```powershell
python -m streamlit run EZScore.py `
  --server.address 127.0.0.1 `
  --server.port 8501 `
  --server.headless true
```

## Test ciblé

1. Ouvrir **Répertoire**.
2. Vérifier les deux vues `Répertoire général / Playlists`.
3. Noter une chanson 5★ avec un utilisateur.
4. Avec un second utilisateur, noter la même chanson 3★.
5. Vérifier la moyenne `4,0` et `2 votes`.
6. Modifier la première note à 1★ : vérifier `2,0` et toujours `2 votes`.
7. Cliquer `＋`, créer une playlist et ajouter la chanson.
8. Vérifier que le second ajout dans la même playlist est bloqué.
9. Ouvrir Playlists, retirer la chanson : elle doit rester au Répertoire.
10. Supprimer la playlist : aucune chanson ne doit être supprimée.

## Non-régression

Ce lot ne modifie pas :

- le player Analyse / STEM ;
- la synchronisation audio ;
- la signature rythmique ;
- `Analyse > Paroles` R5.10 ;
- les ancres / `↵` ;
- les accords éditoriaux ;
- les fichiers audio / STEM.
