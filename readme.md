# EZScore_v1 — R36.0a LyricsLab Worker + ChordsLab UI HOTFIX

Ce hotfix corrige les deux problèmes visibles du premier test R36.0.

## 1. Worker

Erreur observée :

```text
AttributeError: 'WorkerEngine' object has no attribute '_run_lyrics_job'
```

Le dispatch `kind=lyrics` avait bien été ajouté, mais la méthode `_run_lyrics_job()` n’était pas réellement disponible dans `WorkerEngine`.

R36.0a insère explicitement cette méthode dans `WorkerEngine`, juste avant `_read_progress()`, et le contrat vérifie qu’elle existe une seule fois.

Après application, **redémarrer le Worker**, puis relancer `Analyser les paroles`. L’ancien job en échec reste historique ; un nouveau job `lyrics` sera créé.

## 2. Présentation LyricsLab

LyricsLab réutilise désormais explicitement la présentation ChordsLab :

- `chordslab.css` chargé directement ;
- même carte chanson ;
- même `chordslab-prompter` ;
- mêmes `chordslab-stage` / `chordslab-measures` ;
- mêmes `chord-measure`, `chord-measure-number`, `chord-measure-notation`, `chord-slot` ;
- même player `chordslab-player` / `chordslab-transport` / pistes ;
- seuls les mots ajoutent une seconde ligne dans chaque cellule beat.

Donc le bandeau conserve exactement la géométrie visuelle de ChordsLab ; les paroles apparaissent **sous le beat/accord correspondant**, dans la même cellule.

## Installation

À appliquer **après R36.0** :

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R36_0a_LYRICSLAB_WORKER_UI_HOTFIX.zip" -C H:\EZScore_v1

python .\EZScore_v1_R36_0a_LYRICSLAB_WORKER_UI_HOTFIX\scripts\apply_r36_0a.py H:\EZScore_v1

php bin\console cache:clear
php bin\console lint:container
php bin\console lint:twig templates

python -m py_compile .\worker_app\ezscore_analysis_worker.pyw
python -m py_compile .\analysis\lyrics_timeline_analysis.py

php .\EZScore_v1_R36_0a_LYRICSLAB_WORKER_UI_HOTFIX\tests\r36_0a_contract.php H:\EZScore_v1

git diff --check
git status --short
```

Attendu :

```text
R36_0A_APPLIED_OK
R36_0A_CONTRACT_OK
```

Puis :
1. fermer/redémarrer `EZScore Analysis Worker` ;
2. retourner dans LyricsLab ;
3. cliquer `Analyser les paroles` ;
4. vérifier le job `lyrics` et la progression ;
5. à la fin, tester la synchro mot / beat / accord avec le player.

Aucune modification de ChordsLab lui-même ni du workflow stable antérieur.
