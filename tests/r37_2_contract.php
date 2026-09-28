<?php
declare(strict_types=1);
$root=$argv[1]??dirname(__DIR__,2);
$js=(string)file_get_contents($root.'/public/assets/js/lyricslab-r37.js');
$css=(string)file_get_contents($root.'/public/assets/css/lyricslab-r37.css');
foreach(['function metricX(t)','const xBeat=i=>firstX+i*spacing','track.style.transform=','metricX(Number(syl.start_ms||0)/1000)','ezscore:audio-timeupdate'] as $token){if(!str_contains($js,$token))throw new RuntimeException('JS token absent: '.$token);}
foreach(['overflow-x:hidden!important','scroll-snap-type:none!important','transition:none!important'] as $token){if(!str_contains($css,$token))throw new RuntimeException('CSS token absent: '.$token);}
foreach(['scrollIntoView(','scrollLeft=','scrollTo('] as $forbidden){if(str_contains($js,$forbidden))throw new RuntimeException('Navigation horizontale interdite: '.$forbidden);}
if(str_contains($css,'overflow-x:auto'))throw new RuntimeException('overflow-x:auto interdit');
echo "R37_2_CONTRACT_OK\n";
