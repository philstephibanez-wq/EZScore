<?php
declare(strict_types=1);

$root=$argv[1]??dirname(__DIR__,2);
$js=(string)file_get_contents($root.'/public/assets/js/lyricslab-r37.js');
$css=(string)file_get_contents($root.'/public/assets/css/lyricslab-r37.css');

foreach([
  'function metricXRaw(t)',
  'function buildWarp()',
  'const minGap=18',
  'function shiftForRaw(raw)',
  'function metricX(t)',
  'track.style.transform=',
  'ez-karaoke-focus-frame',
  'ezscore:audio-timeupdate'
] as $token){
  if(!str_contains($js,$token)) throw new RuntimeException("JS token absent: ".$token);
}

foreach([
  '.ez-karaoke-focus-frame',
  '.ez-karaoke-word.is-current',
  'overflow:hidden!important',
  'scroll-snap-type:none!important',
  'transition:none!important'
] as $token){
  if(!str_contains($css,$token)) throw new RuntimeException("CSS token absent: ".$token);
}

foreach(['scrollIntoView(','scrollLeft','scrollTo(','overflow-x:auto','fallbackSyllables','syllablesForEvent'] as $forbidden){
  if(str_contains($js,$forbidden) || str_contains($css,$forbidden)){
    throw new RuntimeException("Interdit en R37.3: ".$forbidden);
  }
}

echo "R37_3_CONTRACT_OK\n";
