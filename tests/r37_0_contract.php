<?php
declare(strict_types=1);

$root=$argv[1]??dirname(__DIR__,2);

$checks=[
    'templates/song/chordslab.html.twig'=>[
        "_lab_song_card.html.twig",
        "_timeline_stage.html.twig",
    ],
    'templates/song/lyricslab.html.twig'=>[
        "Extraire les paroles",
        "_lab_song_card.html.twig",
        "_timeline_stage.html.twig",
        "_analysis_player.html.twig",
        "data-lyrics-source",
        "data-lyricslab",
    ],
    'worker_app/ezscore_analysis_worker.pyw'=>[
        'self._run_chord_job(job)',
        'def _read_progress(',
        'from lyrics_worker_r37 import run_lyrics_job',
        'run_lyrics_job(self, job)',
    ],
    'worker_app/lyrics_worker_r37.py'=>[
        'def _discover_lyrics_python',
        'H:\\EZScore\\.venv-py313\\Scripts\\python.exe',
        'import json,torch,whisper,sys',
        'def _read_progress(',
        '--mode",mode',
    ],
    'analysis/lyrics_timeline_analysis.py'=>[
        '--mode',
        'choices=[\'extract\', \'align\']',
        'CUDA required for LyricsLab',
        'language=None',
        'large-v3.pt',
    ],
    'src/Controller/SongLabController.php'=>[
        'app_song_lyricslab_extract',
        "$jobs->queue($song,$user,'extract');",
        "$jobs->queue($song,$user,'align');",
    ],
    'src/Controller/AnalysisDesktopController.php'=>[
        'ezscore.lyrics.extract.r37',
        'setLyricsSourceText($text)',
    ],
];

foreach($checks as $rel=>$tokens){
    $path=$root.DIRECTORY_SEPARATOR.str_replace('/',DIRECTORY_SEPARATOR,$rel);
    if(!is_file($path)) throw new RuntimeException("Fichier absent: $rel");
    $content=(string)file_get_contents($path);
    foreach($tokens as $token){
        if(!str_contains($content,$token)){
            throw new RuntimeException("$rel token absent: $token");
        }
    }
}

echo "R37_0_CONTRACT_OK\n";
