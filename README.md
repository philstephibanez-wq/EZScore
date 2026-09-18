# EZScore — Editorial Fingerprint Recovery R1

Base GitHub vérifiée :

```text
fb5691f189d1430f73f36b4652f54d94218588f0
EZScore_PLAYER_SEEK_LYRICS_R1
```

## Symptôme corrigé

Après la correction « faux Chœurs », `Analyse > Paroles` pouvait lever :

```text
La timeline technique a changé depuis la sauvegarde éditoriale.
Aucun remapping automatique.
```

Le message était techniquement exact sur le fingerprint, mais dans ce cas
précis la différence provenait surtout d'un changement de sémantique :

```text
avant :
mot récupéré par le second Whisper = Chœurs

maintenant :
mot récupéré par le second Whisper = complément du Chant principal
```

L'ancien `editorial_timeline.json` avait donc un fingerprint incluant les faux
mots de Chœurs, tandis que la nouvelle timeline a une lane Chœurs vide.

## Migration déterministe

Le patch reconstruit exactement l'ancienne lane provisoire depuis :

```text
whisper_vocals_small.json
```

Puis il tente de charger l'ancien fichier éditorial avec l'ancien fingerprint.

La migration n'est acceptée QUE si ce fingerprint correspond exactement.

Dans ce cas sont conservés :

```text
lead_overrides
line_break_after_lead
chord_overrides
anchors
```

Les anciens `backing_overrides` sont supprimés, puisque leur source était une
lane Chœurs désormais reconnue comme incorrecte.

Le fichier éditorial est ensuite sauvegardé avec le nouveau fingerprint.

## Vraie modification de timeline

Si le fingerprint ne correspond toujours pas (nouveaux beats, nouvelle
transcription, réanalyse réellement différente), il n'y a TOUJOURS PAS de
remapping automatique.

Le fichier incompatible est renommé :

```text
editorial_timeline.stale-YYYYMMDDTHHMMSSZ.json
```

et la nouvelle timeline repart avec une édition vide.

Donc :
- pas de crash ;
- pas de perte silencieuse ;
- pas de remapping hasardeux ;
- ancienne édition récupérable sur disque.

## Fichiers

Nouveau :

```text
ezscore/ui/editorial_compat_patch.py
```

Modifié :

```text
ezscore/ui/__init__.py
```

Non modifiés :

```text
ezscore/ui/editorial_timeline.py
ezscore/ui/lyrics_inline_editor.py
templates/views/lyrics-editor.*
player R12c
analyse STEM
```

## Installation

```powershell
cd H:\EZScore

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\EZScore_EDITORIAL_FINGERPRINT_RECOVERY_R1.zip" `
  -DestinationPath . `
  -Force

python -m py_compile `
  .\ezscore\ui\editorial_compat_patch.py `
  .\ezscore\ui\__init__.py

git diff --check
git status --short
```

## Test immédiat

1. Redémarrer Streamlit.
2. Ouvrir Jolene > Analyse > Paroles.
3. L'erreur RuntimeError ne doit plus apparaître.
4. Si le seul changement était l'ancienne lane faux-Chœurs, une information de
   migration s'affiche et les corrections Chant/Accords/↵/ancres restent.
5. Si la timeline technique a réellement changé, un warning indique le nom du
   fichier `.stale-...json` archivé et la vue Paroles reste utilisable.
