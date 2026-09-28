<?php
declare(strict_types=1);
$root=$argv[1]??dirname(__DIR__,2);
$j=(string)file_get_contents($root.'/public/assets/js/lyricslab-r37.js');
$c=(string)file_get_contents($root.'/public/assets/css/lyricslab-r37.css');
$m=(string)file_get_contents($root.'/public/assets/js/stems-mixer.js');
$t=(string)file_get_contents($root.'/templates/song/lyricslab.html.twig');
foreach(['function buildWarp()','function buildChords()',"else if(bn===0)text=shown",'stage.clientWidth*.30','data-section-nav','data-lyrics-diagram-toggle'] as $x) if(!str_contains($j,$x)) throw new RuntimeException($x);
foreach(['.lyrics-reading-zone','.lyrics-fixed-diagram','.lyrics-ribbon-chord','.lyrics-ribbon-word.current'] as $x) if(!str_contains($c,$x)) throw new RuntimeException($x);
if(!str_contains($m,"root.addEventListener('ezscore:request-seek'")) throw new RuntimeException('seek handler absent');
if(!str_contains($t,'r38_1')) throw new RuntimeException('cache bust absent');
echo "R38_1_CONTRACT_OK\n";