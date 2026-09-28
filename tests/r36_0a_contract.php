<?php
declare(strict_types=1);
$root=$argv[1]??dirname(__DIR__,2);

$w=(string)file_get_contents($root.'/worker_app/ezscore_analysis_worker.pyw');
if(substr_count($w,'    def _run_lyrics_job(self, job: dict) -> None:')!==1)throw new RuntimeException('Worker lyrics method count != 1');
if(!str_contains($w,'if job.get("kind") == "lyrics":'))throw new RuntimeException('lyrics dispatch absent');

$t=(string)file_get_contents($root.'/templates/song/lyricslab.html.twig');
foreach(['chordslab.css?v=20260928r35_10','panel chordslab-prompter','chordslab-stage','chordslab-measures','chordslab-player'] as $x){
 if(!str_contains($t,$x))throw new RuntimeException('LyricsLab ChordsLab presentation token absent: '.$x);
}

$j=(string)file_get_contents($root.'/public/assets/js/lyricslab-r36-0a.js');
foreach(['chord-measure','chord-measure-notation','chord-slot','lyrics-word.is-current'] as $x){
 if(!str_contains($j,$x))throw new RuntimeException('LyricsLab renderer token absent: '.$x);
}
echo "R36_0A_CONTRACT_OK\n";
