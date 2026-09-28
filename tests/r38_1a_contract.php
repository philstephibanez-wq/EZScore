<?php
declare(strict_types=1);
$root=$argv[1]??dirname(__DIR__,2);
$j=(string)file_get_contents($root.'/public/assets/js/lyricslab-r37.js');
$t=(string)file_get_contents($root.'/templates/song/lyricslab.html.twig');

if(!str_contains($j,"replace(/^\\[([^\\]]+)\\]$/,'$1')"))
    throw new RuntimeException('regex chord normalization absent');
if(str_contains($j,"replace(/^\\\\[([^\\\\]]+)\\\\]$/"))
    throw new RuntimeException('double escaped invalid regex still present');

foreach(['function buildWarp()','function buildChords()','data-section-nav','data-lyrics-diagram-toggle'] as $x)
    if(!str_contains($j,$x)) throw new RuntimeException("JS token absent: ".$x);

if(!str_contains($t,'r38_1a')) throw new RuntimeException('cache-bust r38_1a absent');

echo "R38_1A_CONTRACT_OK\n";
