<?php
declare(strict_types=1);
$root=$argv[1]??'H:\\EZScore_v1';
function bad(string $m):never{fwrite(STDERR,$m.PHP_EOL);exit(1);}
function txt(string $p):string{$s=@file_get_contents($p);if($s===false)bad("Missing ".$p);return $s;}

$j=txt($root.'/public/assets/js/lyricslab-collision-r39-2.js');
$t=txt($root.'/templates/song/lyricslab.html.twig');
$c=txt($root.'/public/assets/css/lyricslab-r37.css');

foreach([
 'visual collision repair only',
 "node.style.setProperty('--ez-font-scale'",
 "node.style.setProperty('--ez-y-offset'",
 "root.dataset.collisionLayout='r39.2'"
] as $n)if(strpos($j,$n)===false)bad('Missing collision marker: '.$n);

# Contract: no horizontal timeline mutation.
foreach(['style.left=','style.left =','translateX(','timeToX(','xBeat('] as $forbidden){
    if(strpos($j,$forbidden)!==false)bad('Forbidden X/timeline mutation in collision layer: '.$forbidden);
}

if(strpos($t,'lyricslab-collision-r39-2.js?v=20260929r39_2')===false)bad('Collision asset missing');
if(strpos($c,'EZScore R39.2 — visual-only collision handling')===false)bad('Collision CSS missing');

# ChordsLab untouched.
$chord=txt($root.'/public/assets/js/chordslab.js');
if(strpos($chord,'timelineCore=()=>window.EZScoreTimelineCoreR39')===false)bad('R39 ChordsLab baseline missing');

echo "R39_2_LYRIC_COLLISION_LAYOUT_CONTRACT_OK".PHP_EOL;
