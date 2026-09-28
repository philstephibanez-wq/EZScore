# EZScore_v1 — R37.0 LyricsLab partagé avec ChordsLab

Base de travail : le ChordsLab stable actuel reste la référence.

## Objectif

R37.0 remet LyricsLab sur la timeline ChordsLab sans modifier le moteur harmonique ni l’édition des beats.

### Templates mutualisés

Nouveaux composants :

```text
templates/song/components/_lab_song_card.html.twig
templates/song/components/_timeline_stage.html.twig
templates/song/components/_analysis_player.html.twig
```

ChordsLab et LyricsLab utilisent maintenant le même `_lab_song_card` et le même `_timeline_stage`.

LyricsLab utilise le player partagé `_analysis_player`.

Le JS ChordsLab n’est pas remplacé et son édition des beats reste intacte.

### Extraire les paroles

Le bouton **Extraire les paroles** crée un job `lyrics` en mode `extract`.

Le Worker Lyrics est isolé dans :

```text
worker_app/lyrics_worker_r37.py
```

Il ne modifie pas `_run_chord_job()` et ne dépend pas de `WorkerEngine._read_progress()` pour les paroles.

Il cherche un Python `Whisper + Torch + CUDA` dans cet ordre :

```text
EZSCORE_LYRICS_PYTHON
Python déjà sélectionné par le Worker
H:\EZScore\.venv-py313\Scripts\python.exe
H:\EZScore_v1\.venv-py313\Scripts\python.exe
Python courant
python
```

Le premier environnement qui importe `whisper`, dispose de CUDA et voit le GPU est utilisé.

Donc l’absence de `whisper` dans `.venv-py313` de EZScore_v1 n’empêche plus l’extraction si le venv historique `H:\EZScore\.venv-py313` est correctement équipé.

Aucun fallback CPU.

### Modèles Whisper

Priorité :

```text
EZSCORE_WHISPER_MODEL
H:\EZScoreModels\whisper\large-v3.pt
H:\EZScoreModels\whisper\large-v3-turbo.pt
H:\EZScoreModels\whisper\medium.pt
H:\EZScoreModels\whisper\small.pt
```

`large-v3` est préféré s’il est installé.

Pour les morceaux multilingues, `language=None` est relancé par fenêtres de 26 secondes avec recouvrement.

### Box éditable

Une extraction réussie remplit automatiquement `Song.lyricsSourceText`, donc la box LyricsLab.

Si la box contient déjà du texte, EZScore demande confirmation avant remplacement.

La box reste éditable en permanence avec sauvegarde automatique.

### Analyser les paroles

Le bouton **Analyser les paroles** :

1. sauvegarde d’abord la box ;
2. crée un job `lyrics` en mode `align` ;
3. Whisper retrouve les timestamps ;
4. le texte de la box reste la vérité éditoriale ;
5. les mots sont ancrés sur la timeline beat/mesure existante.

Les sauts de ligne de la box sont conservés dans `line_break_after` pour impression et futur karaoké vertical ; ils ne changent pas la timeline horizontale.

### Prompteur

Le prompteur utilise :

```text
chord-measure
chord-measure-number
chord-measure-notation
chord-slot
chordslab-stage
chordslab-measures
```

Chaque beat garde exactement sa cellule ChordsLab.

Dans cette cellule :

```text
accord
mot(s)
```

Le mot courant et le beat courant sont surlignés pendant la lecture.

Un pickup vocal peut donc apparaître sous un beat `.` avant le premier accord.

## Installation

Fermer le Worker avant installation.

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R37_0_LYRICSLAB_SHARED.zip" -C H:\EZScore_v1

python .\scripts\apply_r37_0.py H:\EZScore_v1

php bin\console cache:clear
php bin\console lint:container
php bin\console lint:twig templates

python -m py_compile .\worker_app\ezscore_analysis_worker.pyw
python -m py_compile .\worker_app\lyrics_worker_r37.py
python -m py_compile .\analysis\lyrics_timeline_analysis.py

php .\tests\r37_0_contract.php H:\EZScore_v1

git diff --check
git status --short
```

Attendu :

```text
R37_0_APPLIED_OK
R37_0_CONTRACT_OK
```

## Test conseillé

1. Vérifier ChordsLab avant tout : première mesure complète et premier beat toujours éditable.
2. Ouvrir LyricsLab.
3. Vérifier que la carte morceau, la timeline et le player ont la géométrie ChordsLab.
4. Cliquer `Extraire les paroles`.
5. Attendre 100 % : la box doit se remplir.
6. Corriger le texte si nécessaire.
7. Cliquer `Analyser les paroles`.
8. Vérifier les mots sous les beats et leur surbrillance en lecture.

Si `large-v3.pt` n’existe pas, le moteur passe au modèle local suivant, sans CPU fallback.
