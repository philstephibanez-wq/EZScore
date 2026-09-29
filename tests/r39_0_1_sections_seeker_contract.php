<?php
declare(strict_types=1);
$root=$argv[1]??'H:\\EZScore_v1';
function bad(string $m):never{fwrite(STDERR,$m.PHP_EOL);exit(1);}
function txt(string $p):string{$s=@file_get_contents($p);if($s===false)bad("Missing ".$p);return $s;}
$j=txt($root.'/public/assets/js/lyricslab-timeline-r39.js');
$t=txt($root.'/templates/song/lyricslab.html.twig');
$c=txt($root.'/public/assets/css/lyricslab-r37.css');
foreach([
 'R39.0.1 — restore sections + manual seeker',
 'data-section-nav',
 'data-lyrics-manual-seeker',
 "new CustomEvent('ezscore:request-seek'",
 "root.dataset.sectionsRestored='r39.0.1'",
 "root.dataset.manualSeeker='r39.0.1'"
] as $n)if(strpos($j,$n)===false)bad('JS marker missing: '.$n);
if(strpos($t,'lyricslab-timeline-r39.js?v=20260929r39_0_1')===false)bad('JS cache bust missing');
if(strpos($t,'lyricslab-r37.css?v=20260929r39_0_1')===false)bad('CSS cache bust missing');
if(strpos($c,'R39.0.1 sections + manual seek')===false)bad('CSS patch missing');

# Non-regression: this hotfix must not touch ChordsLab.
$chord=txt($root.'/public/assets/js/chordslab.js');
if(strpos($chord,'timelineCore=()=>window.EZScoreTimelineCoreR39')===false)bad('R39 ChordsLab baseline missing');

echo "R39_0_1_SECTIONS_SEEKER_CONTRACT_OK".PHP_EOL;
