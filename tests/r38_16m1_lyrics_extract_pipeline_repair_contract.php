<?php
declare(strict_types=1);
$root=$argv[1]??'H:\\EZScore_v1';
function bad(string $m):never{fwrite(STDERR,$m.PHP_EOL);exit(1);}
$job=@file_get_contents($root.'/src/Service/SongLyricsJobService.php');
$lab=@file_get_contents($root.'/src/Controller/SongLabController.php');
$desktop=@file_get_contents($root.'/src/Controller/AnalysisDesktopController.php');
$js=@file_get_contents($root.'/public/assets/js/lyricslab-r37.js');
if($job===false||$lab===false||$desktop===false||$js===false)bad('Missing R38.16m1 files');

foreach([
    "\$activeMode = (string) (\$active->getRequestData()['mode'] ?? 'align');",
    "lyrics_job_mode_conflict:",
] as $n) if(strpos($job,$n)===false)bad('Mode collision fix missing: '.$n);

if(strpos($lab,'Sauvegarde automatique avant extraction Whisper.')!==false)bad('Forbidden automatic save before extract remains');
foreach(["'source_characters'","'result_characters'","'recognized_words'"] as $n)
    if(strpos($lab,$n)===false)bad('Lyrics status diagnostic missing: '.$n);

foreach([
    "setLyricsCurrentRevisionId(null)",
    "lyrics_extract_persist_failed",
] as $n) if(strpos($desktop,$n)===false)bad('Extract persistence guard missing: '.$n);

foreach([
    "aucune parole n’a été persistée",
    "String(data.mode||'align')==='extract'",
] as $n) if(strpos($js,$n)===false)bad('Frontend extraction guard missing: '.$n);

echo "R38_16M1_LYRICS_EXTRACT_PIPELINE_REPAIR_CONTRACT_OK".PHP_EOL;
