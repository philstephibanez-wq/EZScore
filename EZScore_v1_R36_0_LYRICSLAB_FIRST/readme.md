# EZScore_v1 — R36.0 LyricsLab FIRST

Premier livrable LyricsLab, construit **au-dessus de la référence stable ChordsLab + workflow antérieur**.

## Ce qui est livré

- LyricsLab récupère la timeline existante : beats, mesures, accords analysés/corrigés, capo.
- Bloc éditable pour coller/modifier le texte source à tout moment, avec sauvegarde automatique.
- Les sauts de ligne sont conservés dans le texte source et dans les métadonnées de mots ; ils ne coupent pas le bandeau prompteur.
- Bouton **Analyser les paroles**.
- Nouveau job Worker `lyrics`.
- Whisper CUDA, `word_timestamps=True`, français, **sans fallback CPU**.
- Le texte fourni reste la vérité éditoriale ; Whisper sert à retrouver les positions temporelles.
- Alignement du texte fourni sur la transcription horodatée.
- Événements `TYPE_LYRIC` persistés sur la timeline existante.
- Prompteur horizontal : accords au-dessus, mots dessous.
- Le mot courant s’allume pendant la lecture.
- Clic sur un mot : correction éditable persistée.
- Même player/stems que ChordsLab avec vitesse, seek et préchargement audio existant.

## Installation

```powershell
cd H:\EZScore_v1

tar -xf "$env:USERPROFILE\Downloads\EZScore_v1_R36_0_LYRICSLAB_FIRST.zip" -C H:\EZScore_v1

python .\EZScore_v1_R36_0_LYRICSLAB_FIRST\scripts\apply_r36_0.py H:\EZScore_v1

php bin\console doctrine:migrations:migrate --no-interaction

php bin\console cache:clear
php bin\console lint:container
php bin\console lint:twig templates

python -m py_compile .\analysis\lyrics_timeline_analysis.py
python -m py_compile .\worker_app\ezscore_analysis_worker.pyw

php .\EZScore_v1_R36_0_LYRICSLAB_FIRST\tests\r36_0_contract.php H:\EZScore_v1

git diff --check
git status --short
```

Attendu :

```text
R36_0_APPLIED_OK
R36_0_CONTRACT_OK
```

## Premier test

1. Ouvrir une chanson dont StemsLab + ChordsLab sont terminés.
2. Ouvrir **LyricsLab**.
3. Coller les paroles exactes.
4. Attendre `Enregistré`.
5. Cliquer **Analyser les paroles**.
6. Vérifier l’apparition du job `lyrics` dans le Worker.
7. À 100 %, le prompteur doit afficher les accords et les mots dessous.
8. Lancer Lecture : le mot courant doit s’allumer sous le beat/accord correspondant.

Aucune modification volontaire de l’algorithme ChordsLab ni du workflow antérieur stable.
