# EZScore R36.1 — Correctif transition FSM après analyse

Base attendue : `R36_WORKFLOW_FSM` déjà appliquée localement.

## Bug corrigé

La fin d'une deuxième analyse déclenchait :

```text
StreamlitWidgetAlreadyInstantiatedError:
st.session_state.song_view_... cannot be modified after the widget
with key song_view_... is instantiated.
```

Cause :

```text
analyse terminée
→ complete_analysis_to_edit()
→ écriture immédiate dans song_view_* / song_mode_*
→ les radios existent déjà dans ce même run
→ Streamlit interdit la modification
```

## Correction

La transition devient asynchrone au rerun Streamlit :

```text
analyse terminée
→ workflow = editing
→ _pending_song_edit_hash = audio_hash
→ st.rerun()
→ début du run suivant
→ EZScore.py consomme _pending_song_edit_hash
→ Vue = Grille
→ Mode = Édition
→ création des radios
```

Aucune clé de widget n'est donc modifiée après instanciation.

## Fichier modifié

```text
ezscore/ui/song_fsm.py
```

Aucune migration SQLite.
Aucune donnée musicale modifiée.

## Installation PowerShell

Dézipper puis :

```powershell
cd H:\EZScore
python .\apply_r36_1.py --root H:\EZScore
```

Puis :

```powershell
python -m py_compile .\EZScore.py
python -m py_compile .\ezscore\ui\song_fsm.py
python -m compileall -q .\ezscore
```

Lancer :

```powershell
python -m streamlit run .\EZScore.py --server.address 127.0.0.1 --server.port 8501 --server.headless true
```

## Recette

Sur le morceau déjà analysé :

1. rester en édition ;
2. relancer explicitement une deuxième analyse ;
3. attendre 100 % ;
4. vérifier qu'il n'y a plus de `StreamlitWidgetAlreadyInstantiatedError` ;
5. vérifier le retour automatique :

```text
Vue = Grille
Mode = Édition
```

Trace attendue :

```text
[EZTRACE][FSM] hash=... post_analysis_transition=queued
```

Ne pas commit/push avant validation de cette étape.
