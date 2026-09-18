# EZScore — FIX Aline accords dans Analyse > Paroles

## Diagnostic

Le pipeline HQ écrit les beats modernes sous cette forme :

```json
{
  "index": 42,
  "time": 24.327,
  "chord": "Fm"
}
```

R5.10 normalisait uniquement :

```text
start
temps
time_start
```

et ignorait `time`.

Conséquence : chaque beat moderne prenait `start = 0`, donc les accords étaient
bien analysés mais empilés à gauche de la timeline. C'est le cas visible sur
Aline. Dance Me utilisait une timeline/cache d'un schéma déjà compris par R5.10.

## Correction

Un seul fichier est modifié :

```text
ezscore/ui/editorial_timeline.py
```

`normalize_beats()` accepte maintenant le contrat canonique :

```text
beat_timeline[].time
```

Pour ce schéma point-à-point :

```text
beat[i].start = beat[i].time
beat[i].end   = beat[i+1].time
```

Le dernier beat reprend uniquement la durée positive du précédent intervalle.
Les anciens schémas `start`, `temps` et `time_start` gardent exactement leur
comportement R5.10 afin de ne pas modifier Dance Me ni les anciennes analyses.

## Migration ciblée du fingerprint R5.10

Si `editorial_timeline.json` a déjà été enregistré pendant le bug, son
`source_fingerprint` contient les beats modernes à `0`.

Le correctif reconnaît **uniquement** ce fingerprint exact. Dans ce cas :

- aucun mot n'est remappé ;
- aucun beat n'est remappé ;
- `lead_overrides` est conservé ;
- `backing_overrides` est conservé ;
- `chord_overrides` est conservé ;
- les `↵` sont conservés ;
- les ancres conservent leur `snap_index` ;
- le temps d'une ancre beat est recalculé depuis le timestamp technique corrigé.

Tout autre changement réel de timeline continue à déclencher l'erreur R5.10 :

```text
La timeline technique a changé depuis la sauvegarde éditoriale.
Aucun remapping automatique.
```

Le nouveau fingerprint est persisté au prochain clic sur **Enregistrer**.

## Installation

```powershell
cd H:\EZScore

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\EZScore_FIX_ALINE_CHORD_TIMELINE_R1.zip" `
  -DestinationPath . `
  -Force

python -m py_compile .\ezscore\ui\editorial_timeline.py

git diff --check
git status --short
```

Relancer Streamlit.

## Test ciblé

1. Ouvrir Aline.
2. Aller dans `Analyse > 2 · Paroles`.
3. À `0:00`, vérifier que les accords ne sont plus superposés au même X.
4. Défiler vers `0:24`, `0:30`, etc. : les accords doivent suivre leur timeline.
5. Vérifier les paroles, chœurs et scrollbar.
6. Vérifier une ancre existante.
7. Vérifier un `↵` existant.
8. Double-cliquer un accord et vérifier l'édition beat par beat.
9. Cliquer **Enregistrer** pour réécrire le fingerprint corrigé.
10. Ouvrir Dance Me et vérifier l'absence de régression.

## Non-régression

Ce lot ne modifie pas :

- `EZScore.py` ;
- `ezscore/ui/__init__.py` ;
- le player R12c ;
- `lyrics_inline_editor.py` ;
- les templates `lyrics-editor.*` ;
- les fichiers d'analyse ;
- les timestamps techniques ;
- le Répertoire / playlists / i18n ;
- la base SQLite.
