<?php
declare(strict_types=1);
$root=$argv[1]??'H:\\EZScore_v1';
function bad(string $m):never{fwrite(STDERR,$m.PHP_EOL);exit(1);}
$a=@file_get_contents($root.'/analysis/lyrics_timeline_analysis.py');
$r=@file_get_contents($root.'/src/Service/LyricsTimelineResultService.php');
$j=@file_get_contents($root.'/public/assets/js/lyricslab-r37.js');
$t=@file_get_contents($root.'/templates/song/lyricslab.html.twig');
if($a===false||$r===false||$j===false||$t===false)bad('Missing R38.17A files');

foreach([
 '# R38.17A acoustic syllabic alignment correction',
 'src = provided',
 '_r3817a_effective_t0',
 'lexical_anchor_calibrated_lower_bound',
 '_r3817_refine_syllable_nuclei(rows, args.vocal_audio)',
 'local_vocal_rms_peak',
 "'version': 'r38.17a-acoustic-syllabic-alignment'",
 "'timing_diagnostics':",
] as $n) if(strpos($a,$n)===false)bad('Analysis marker missing: '.$n);

foreach(["'syllables'=>","'cue_ms'=>","'alignment'=>","'recognized_index'=>"] as $n)
 if(strpos($r,$n)===false)bad('Result marker missing: '.$n);

foreach(["const wordCueMs=","if(wordCueMs(words[k])<=ms)","rawMetric(wordCueMs(w)/1000)"] as $n)
 if(strpos($j,$n)===false)bad('Renderer marker missing: '.$n);

if(strpos($j,'R38.13 canonical ChordsLab projection.')===false)bad('Harmonic projection marker lost');
if(strpos($t,'lyricslab-r37.js?v=20260929r38_17a')===false)bad('Asset cache-bust missing');

echo "R38_17B_ACOUSTIC_SYLLABIC_ALIGNMENT_REPAIR_CONTRACT_OK".PHP_EOL;
