<?php
declare(strict_types=1);
$root=$argv[1]??'H:\\EZScore_v1';
function bad(string $m):never{fwrite(STDERR,$m.PHP_EOL);exit(1);}
function txt(string $p):string{$s=@file_get_contents($p);if($s===false)bad("Missing: ".$p);return $s;}
$core=txt($root.'/public/assets/js/ezscore-timeline-core-r39.js');
$renderer=txt($root.'/public/assets/js/lyricslab-timeline-r39.js');
$cj=txt($root.'/public/assets/js/chordslab.js');
$lj=txt($root.'/public/assets/js/lyricslab-r37.js');
$ct=txt($root.'/templates/song/chordslab.html.twig');
$lt=txt($root.'/templates/song/lyricslab.html.twig');
$cdc=txt($root.'/docs/CDC_TIMELINE_CANONIQUE_R39.md');

foreach(['timeToX','beatIndexAtMs','chordProjection','saveBeatOverride','flattenSyllables'] as $n) if(strpos($core,$n)===false)bad('Core missing: '.$n);
foreach(['timelineCore=()=>window.EZScoreTimelineCoreR39','core.chordProjection(events,displayChord)','core.beatIndexAtMs(ms)'] as $n) if(strpos($cj,$n)===false)bad('ChordsLab shared-core marker missing: '.$n);
if(strpos($lj,'EZScoreLyricsTimelineR39.mount(root)')===false)bad('LyricsLab delegation missing');
foreach(['Core.flattenSyllables(words)','timeline.timeToX(s.nucleusMs)','Core.saveBeatOverride','lyrics-ribbon-syllable'] as $n) if(strpos($renderer,$n)===false)bad('LyricsLab R39 renderer missing: '.$n);
foreach(['buildWarp','shiftFor(','visMetric('] as $forbidden) if(strpos($renderer,$forbidden)!==false)bad('Forbidden lyric time warp: '.$forbidden);
foreach(['data-chord-beat-edit-url-template','data-chord-edit-token','lyricslab-timeline-r39.js?v=20260929r39_0'] as $n) if(strpos($lt,$n)===false)bad('LyricsLab template missing: '.$n);
if(strpos($ct,'ezscore-timeline-core-r39.js?v=20260929r39_0')===false)bad('ChordsLab does not load canonical core');
if(strpos($cdc,'forced aligner phonétique')===false)bad('CDC phonetic pipeline missing');
if(strpos($cdc,'ne doit **pas remettre en cause ChordsLab**')===false)bad('CDC non-regression clause missing');
echo "R39_CANONICAL_TIMELINE_SYLLABLES_CONTRACT_OK".PHP_EOL;
