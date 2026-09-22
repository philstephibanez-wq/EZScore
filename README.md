# EZScore_LYRICS_RENDER_REMOTE_R1b

Correctif du livrable R1 qui échouait car les chaînes `Lecture/Pause/Stop`
existent deux fois dans le source du conducteur : une fois dans le motif
supprimé du player de base et une fois dans le transport réellement injecté.

R1b cible désormais **le bloc transport injecté complet**, donc aucun patch
ambigu.

Base GitHub vérifiée :

```text
master = a52485f22a8f0ccaaa36808a9f712916a2d84f53
```

## Résultat attendu

Le bloc Paroles est rendu directement depuis :

```text
data\EZScore.sqlite3
user_lyrics_sources.source_text
```

Le widget Streamlit utilise une clé contenant une empreinte du contenu BDD.
Un ancien état vide du navigateur/session ne peut plus masquer la donnée.

Le parcours télécommande/clavier reste dans l'ordre DOM naturel, avec focus
visible pour les contrôles HTML du lecteur STEM.

## Application

```powershell
cd H:\EZScore

tar -xf "$env:USERPROFILE\Downloads\EZScore_LYRICS_RENDER_REMOTE_R1b.zip" -C H:\EZScore

.\.venv-py313\Scripts\python.exe .\scripts\apply_lyrics_render_remote_r1b.py

.\.venv-py313\Scripts\python.exe -m py_compile `
  .\ezscore\integration\choir_pipeline.py `
  .\ezscore\player\stem_analysis_conductor.py `
  .\scripts\test_lyrics_render_remote_r1b_contract.py

.\.venv-py313\Scripts\python.exe .\scripts\test_lyrics_render_remote_r1b_contract.py
```

Attendu :

```text
PATCH OK
 - textarea alimenté directement par SQLite
 - clé widget versionnée par le contenu BDD
 - bouton Valider conservé
 - aide Ctrl+Enter masquée
 - lecteur STEM navigable au clavier/télécommande

LYRICS RENDER + REMOTE R1b CONTRACT OK
DB rows verified: 2
 - cd8e4603f548: 2105 chars
 - f7759e677f20: 776 chars
textarea <- SQLite direct: YES
stale empty widget can mask DB: NO
explicit validation button: YES
Ctrl+Enter helper hidden: YES
Android remote / keyboard focus: YES
```

Puis arrêter complètement Streamlit et le relancer.
