<?php
declare(strict_types=1);
$root=$argv[1]??'H:\\EZScore_v1';
function bad(string $m):never{fwrite(STDERR,$m.PHP_EOL);exit(1);}
$a=@file_get_contents($root.'/analysis/lyrics_timeline_analysis.py');
$r=@file_get_contents($root.'/src/Service/LyricsTimelineResultService.php');
$j=@file_get_contents($root.'/public/assets/js/lyricslab-r37.js');
$t=@file_get_contents($root.'/templates/song/lyricslab.html.twig');
if($a===false||$r===false||$j===false||$t===false)bad('Missing R38.17C files');

foreach([
 '# R38.17C — leading-prefix-only lyric repair',
 '_r3817c_repair_leading_prefix',
 'leading_prefix_acoustic_repair',
 'fixed_anchor_ms',
 "'version': 'r38.17c-leading-prefix-acoustic-repair'",
 "'prefix_repair': prefix_diagnostics",
] as $n) if(strpos($a,$n)===false)bad('Analysis marker missing: '.$n);

foreach(["'syllables'=>","'cue_ms'=>"] as $n)
 if(strpos($r,$n)===false)bad('Persistence marker missing: '.$n);

foreach(["const wordCueMs=","wordCueMs(words[k])"] as $n)
 if(strpos($j,$n)===false)bad('Renderer marker missing: '.$n);

if(strpos($j,'R38.13 canonical ChordsLab projection.')===false)bad('Harmonic projection changed/lost');
if(strpos($t,'lyricslab-r37.js?v=20260929r38_17c')===false)bad('Cache-bust missing');

echo "R38_17C_LEADING_PREFIX_ALIGNMENT_CONTRACT_OK".PHP_EOL;
