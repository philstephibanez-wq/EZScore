# EZScore_v1 — R36.1 LyricsLab PRO

## Ce livrable corrige

- le Worker LyricsLab qui levait :
  `WorkerEngine object has no attribute _run_lyrics_job`
- la présentation LyricsLab qui divergeait encore de ChordsLab ;
- l’absence du bouton **Extraire les paroles** ;
- la détection de langue trop simpliste ;
- l’absence des jobs Paroles dans le tableau de bord Analyse.

## Extraction des paroles

Nouveau bouton :

`Extraire les paroles`

Le job utilise d’abord `lead_vocals` si disponible, sinon la source audio.

Pour maximiser la qualité :

- CUDA obligatoire ;
- priorité à `large-v3.pt` ;
- aucune langue forcée ;
- transcription en fenêtres de 26 s avec recouvrement ;
- nouvelle détection de langue pour chaque fenêtre ;
- agrégation des segments et suppression des doublons de recouvrement ;
- meilleure tolérance aux chansons multilingues / code-switching.

Ordre de recherche des modèles :

```text
EZSCORE_WHISPER_MODEL
H:\EZScoreModels\whisper\large-v3.pt
H:\EZScoreModels\whisper\large-v3-turbo.pt
H:\EZScoreModels\whisper\medium.pt
H:\EZScoreModels\whisper\small.pt
```

Pour la qualité maximale, installer `large-v3.pt`.

Si le bloc Paroles contient déjà du texte, **Extraire les paroles** demande confirmation via la modale EZScore avant remplacement.

## Analyse / ancrage

`Analyser les paroles` reste distinct de l’extraction :

- le texte édité par l’utilisateur reste la vérité éditoriale ;
- Whisper sert à retrouver les timestamps ;
- les mots sont ancrés sur la timeline beat / mesure / accord existante ;
- les sauts de ligne restent des métadonnées éditoriales ;
- le mot courant s’allume sous le beat / accord joué.

## Présentation

LyricsLab réutilise directement :

```text
chordslab.css
stems.css
```

et les classes ChordsLab :

```text
chordslab-song-card
chordslab-prompter
chordslab-stage
chordslab-measures
chord-measure
chord-measure-notation
chord-slot
chordslab-player
chordslab-transport
```

Le player partagé est maintenant isolé dans :

```text
templates/song/components/_analysis_player.html.twig
```

LyricsLab l’inclut via Twig.

ChordsLab stable n’est pas modifié dans ce livrable : on évite toute régression du socle validé.

## Worker

R36.1 ne dépend plus d’une insertion fragile de méthode dans le corps de `WorkerEngine`.

Il crée l’implémentation puis la lie explicitement :

```python
WorkerEngine._run_lyrics_job = _ezscore_r36_1_run_lyrics_job
```

et vérifie le binding avec `hasattr()` au chargement.

## Tableau de bord Analyse

Les traitements récents affichent maintenant :

- Stems
- Accords
- Paroles

Pour LyricsLab :

- `Extraction du texte`
- `Ancrage sur la timeline`

## Installation — dézip direct dans H:\EZScore_v1

Le ZIP ne contient **aucun dossier wrapper `EZScore_v1_R...`**.

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R36_1_LYRICSLAB_PRO.zip" -C H:\EZScore_v1

python .\scripts\apply_r36_1.py H:\EZScore_v1

php bin\console cache:clear
php bin\console lint:container
php bin\console lint:twig templates

python -m py_compile .\analysis\lyrics_timeline_analysis.py
python -m py_compile .\worker_app\ezscore_analysis_worker.pyw

php .\tests\r36_1_contract.php H:\EZScore_v1

git diff --check
git status --short
```

Attendu :

```text
R36_1_APPLIED_OK
R36_1_CONTRACT_OK
```

Ensuite fermer complètement puis redémarrer **EZScore Analysis Worker**.

## Tests

1. Le job Paroles déjà en attente doit être pris sans erreur `_run_lyrics_job`.
2. Vider le bloc puis cliquer **Extraire les paroles**.
3. À 100 %, le bloc est rempli automatiquement.
4. Corriger le texte si nécessaire.
5. Cliquer **Analyser les paroles**.
6. Vérifier les mots sous les beats / accords et l’illumination pendant Lecture.
7. Vérifier le job Paroles dans le tableau de bord Analyse.

Aucun fallback CPU.
Aucun changement de l’algorithme ChordsLab stable.
