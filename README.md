# EZScore — R5.7 signature dynamique + accords compacts

Ce livrable part du R5.6 validé et ajoute le reste demandé sans toucher au
player audio ni aux timestamps techniques.

## 1. Signature rythmique éditable

Un contrôle compact `Signature` est affiché dans l'en-tête de l'éditeur.

Priorité :
1. signature éditoriale sauvegardée ;
2. signature détectée dans la structure / conducteur ;
3. défaut `4/4` si aucune donnée n'est disponible.

Formats acceptés :
`2/4`, `3/4`, `4/4`, `6/8`, `9/8`, `12/8`, etc.

La modification est une donnée de présentation. Elle ne modifie jamais la
timeline des beats.

## 2. Regroupement dynamique des beats

Le numérateur pilote le regroupement visuel :

```text
2/4 -> 2 beats par mesure
3/4 -> 3 beats par mesure
4/4 -> 4 beats par mesure
6/8 -> 6 beats par mesure
```

Exemple 4/4 :

```text
Gm-A.
```

Signification :

```text
beat 1 = Gm
beat 2 = -
beat 3 = A
beat 4 = .
```

Aucun espace n'est ajouté entre les beats.

Quand le détecteur renvoie le même accord sur plusieurs beats, l'affichage
est compacté automatiquement :

```text
Gm Gm Gm Gm  ->  Gm---
```

Le premier beat de chaque mesure répète l'accord afin que chaque mesure reste
lisible indépendamment.

## 3. Édition beat par beat

Chaque token de la mesure est éditable au double-clic.

Valeurs possibles :
- accord (`Gm`, `A`, `Cm7`, etc.) ;
- `-` maintien ;
- `.` silence / aucun accord ;
- `^` accent ;
- toute autre notation éditoriale non vide.

La persistance existante `chord_overrides` est conservée, indexée par beat.
Aucun nouveau remapping temporel.

## 4. Compatibilité de persistance

Le fichier éditorial reste en `schema_version = 3`.

Ajout facultatif :

```json
"time_signature_override": "6/8"
```

Un ancien `editorial_timeline.json` R5/R5.6 sans cette clé continue donc à être
chargé sans migration destructrice.

Les paroles, ancres, sauts de ligne et corrections d'accords existants restent
conservés.

## 5. Paroles légèrement resserrées

Échelle horizontale :
- R5.6 : 115 px/s
- R5.7 : 100 px/s

Taille des paroles légèrement réduite pour gagner de la densité sans toucher
aux timestamps.

## 6. Sauts de ligne / ancres

Le comportement R5.6 validé est conservé :
- clic long ~475 ms sur un mot : insérer `↵` ;
- drag gauche sur `↵` : déplacer ;
- `Suppr` : supprimer ;
- drag gauche sur une ancre : déplacer ;
- double-clic ancre : renommer ;
- scrollbar toujours visible.

## Portée

Fichiers modifiés :

- `ezscore/ui/editorial_timeline.py`
- `ezscore/ui/lyrics_inline_editor.py`
- `templates/views/lyrics-editor.html`
- `templates/views/lyrics-editor.css`
- `templates/views/lyrics-editor.js`

Aucun player audio.
Aucun template `.score`.
Aucune réanalyse.
Aucun changement de timestamps.

## Installation

```powershell
cd H:\EZScore

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\EZScore_INLINE_TIMELINE_R5_7.zip" `
  -DestinationPath . `
  -Force

python -m py_compile .\ezscore\ui\editorial_timeline.py
python -m py_compile .\ezscore\ui\lyrics_inline_editor.py
node --check .\templates\views\lyrics-editor.js

git diff --check
git status --short
```

## Test ciblé

1. Ouvrir `Analyse > Paroles`.
2. Vérifier que les paroles/ancres/sauts R5.6 sont toujours présents.
3. Vérifier la signature affichée.
4. Passer par exemple de `4/4` à `3/4` : le regroupement doit changer immédiatement.
5. Revenir à la bonne signature.
6. Vérifier un accord répété : `Gm---` au lieu de quatre boîtes `Gm`.
7. Double-cliquer un beat et saisir par exemple `A`, `-`, `.`, `^`.
8. Vérifier l'affichage sans espaces, par exemple `Gm-A.`.
9. Enregistrer.
10. Changer d'onglet puis revenir : signature et beats édités persistants.
11. Revalider insertion/déplacement de `↵`, déplacement des ancres et scrollbar.
