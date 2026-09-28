<?php
declare(strict_types=1);

$root=$argv[1]??dirname(__DIR__,2);

$checks=[
    'analysis/lyrics_timeline_analysis.py'=>[
        'r36.1-large-v3-multilingual',
        'language=None',
        'CHUNK_SECONDS = 26.0',
        'large-v3.pt',
        'CUDA required for LyricsLab',
    ],
    'src/Service/SongLyricsJobService.php'=>[
        "string \$mode = 'align'",
        "'extract'",
        "'language' => 'auto'",
    ],
    'templates/song/lyricslab.html.twig'=>[
        'Extraire les paroles',
        'song/components/_analysis_player.html.twig',
        'chordslab.css?v=20260928r35_10',
        'data-lyricslab',
    ],
    'templates/song/components/_analysis_player.html.twig'=>[
        'chordslab-player',
        'chordslab-transport',
        'stem-mixer-tracks',
        'chordslab-master-fx',
    ],
    'public/assets/js/lyricslab-r36-1.js'=>[
        'chord-measure',
        'chord-measure-notation',
        'chord-slot lyricslab-beat',
        'lyricslab-word.is-current',
    ],
    'worker_app/ezscore_analysis_worker.pyw'=>[
        'WorkerEngine._run_lyrics_job = _ezscore_r36_1_run_lyrics_job',
        'hasattr(WorkerEngine, "_run_lyrics_job")',
        '"--mode", mode',
    ],
    'src/Controller/SongLabController.php'=>[
        'app_song_lyricslab_extract',
        "'align'",
        'AnalysisJobRepository',
        'analysis_jobs',
    ],
    'src/Controller/AnalysisDesktopController.php'=>[
        'Lyrics extraction returned an empty text.',
        "setLyricsSourceText(\$text)",
        "'mode'=>'extract'",
    ],
];

foreach($checks as $rel=>$tokens){
    $path=$root.DIRECTORY_SEPARATOR.str_replace('/',DIRECTORY_SEPARATOR,$rel);
    if(!is_file($path))throw new RuntimeException("Fichier absent: $rel");
    $content=(string)file_get_contents($path);
    foreach($tokens as $token){
        if(!str_contains($content,$token)){
            throw new RuntimeException("$rel token absent: $token");
        }
    }
}

echo "R36_1_CONTRACT_OK\n";
