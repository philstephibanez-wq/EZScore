# EZScore — R11b karaoké synchronisé

Ce ZIP contient directement les fichiers à recopier dans le dépôt, avec leur
arborescence relative. Il ne contient ni patch, ni script d'installation.

## Fichiers

- `ezscore/player/karaoke_stem_webaudio_r11.py`
- `ezscore/ui/__init__.py`
- `readme.md`

Le lecteur R10 validé reste intact. R11b le réutilise pour l'audio, les STEM,
l'EQ, les caches et la réanalyse, et remplace uniquement la couche de
présentation/contrôle du karaoké.

## Installation PowerShell

Depuis `H:\EZScore` :

```powershell
Expand-Archive -Path .\EZScore_R11b_karaoke_sync_REAL.zip -DestinationPath . -Force

python -m py_compile .\ezscore\player\karaoke_stem_webaudio_r11.py
python -m py_compile .\ezscore\ui\__init__.py

git diff --check
git status
```

Puis redémarrer Streamlit. Le nom du composant passe explicitement à
`ezscore_karaoke_stem_player_r11`, ce qui force le chargement du nouveau bundle.

## Résultat attendu

```text
Mixeur STEM / EQ
Master
Mesure [4/4]   Vitesse [1.00x]   [ ] Diagrammes guitare
Lecture / Pause / Stop + seek
Diagramme courant (uniquement si coché et disponible)
Accord courant
Accords (file)
Chant (file)
Chœurs (file)
```

La signature ne modifie jamais la timeline absolue. Elle ne fait que regrouper
les beats existants pour l'affichage. Les trois files utilisent la même
fonction temps -> position X.

La vitesse agit sur tous les `AudioBufferSourceNode` et sur l'horloge visuelle
avec le même facteur.

## Test minimal avant push

- passage `4/4 -> 2/4` : aucune dérive Chant/Chœurs par rapport aux accords ;
- `0.75x`, `1.00x`, `1.25x` : audio et conducteur restent synchronisés ;
- transport immédiatement au-dessus du karaoké ;
- accord courant visible en permanence ;
- case diagrammes : le diagramme apparaît au-dessus de l'accord courant sans
  remplacer la file d'accords ;
- mixeur STEM, EQ 3 bandes et Master inchangés.

Ne pas pousser avant ces vérifications.

## Étape suivante

Après validation fonctionnelle : persistance SQLite automatique par
`(utilisateur, chanson)` de la source, ON/OFF pistes, volumes, EQ, Master,
vitesse, signature et affichage des diagrammes.
