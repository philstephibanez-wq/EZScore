# EZScore — STEM pipeline R8 / HTTP media player

## Règle contractuelle EZScore

Même règle que MAESTRO :

**on ne masque aucune erreur et on n'ajoute aucun fallback silencieux.**

En cas d'erreur :
1. l'erreur réelle reste visible ;
2. la source est étudiée ;
3. la cause est corrigée ;
4. la correction est validée.

R8 ne contient aucun handler destiné à avaler `WinError 10054` et aucun retour
automatique vers l'ancien player.

## Correction de la source

Les players précédents transportaient les MP3 dans les données du composant
sous forme base64. Ces données passaient donc par la connexion Streamlit/Bidi,
la même connexion qui subissait les resets 10054.

R8 supprime ce transport.

Streamlit possède déjà un `MediaFileManager`, utilisé par `st.audio` et
`st.video`. R8 enregistre les previews dans ce gestionnaire et ne transmet au
composant que leur URL HTTP `/media/...`.

```text
AVANT
MP3 -> base64 -> Bidi/WebSocket -> composant

R8
MP3 -> Streamlit MediaFileManager -> HTTP /media/...
                              |
Bidi/WebSocket -> URL + petits événements JSON seulement
```

Aucun serveur HTTP parallèle et aucune configuration `static/` ne sont ajoutés.

## Lecteurs

Le sélecteur reste :
- `STEM audio`
- `MP3 + MIDI`

Un seul player lourd est monté à la fois.

Le MP3 reste l'horloge maître. MIDI Chant / Accords / Batterie suivent
`audio.currentTime`.

## Pas de fallback

Si l'enregistrement HTTP média échoue, EZScore lève l'erreur réelle.
Il ne rebascule pas en base64.

## Compilation

```powershell
cd H:\EZScore
python -m py_compile .\ezscore\player\media_url.py
python -m py_compile .\ezscore\player\stem_webaudio.py
python -m py_compile .\ezscore\midi\stem_sync_player.py
python -m py_compile .\ezscore\analysis\stem_midi.py
python -m py_compile .\ezscore\analysis\stem_midi_worker.py
python -m py_compile .\ezscore\ui\stem_lab_analysis.py
python -m py_compile .\ezscore\ui\app_shell.py
```

Ne pas ajouter au commit :
- `data/EZScore.sqlite3`
- `data/logs/ezscore_perf.log`
- `data/analysis/`

L'utilisateur effectue lui-même commit/push.
