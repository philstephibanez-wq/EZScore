<?php
declare(strict_types=1);

$root=$argv[1]??dirname(__DIR__,2);
$j=(string)file_get_contents($root.'/public/assets/js/lyricslab-r37.js');
$t=(string)file_get_contents($root.'/templates/song/lyricslab.html.twig');

foreach([
    "data-lyrics-progress",
    "function pollLyricsProgress()",
    "data-lyrics-progress-text",
    "data-lyrics-progress-percent",
    "setTimeout(pollLyricsProgress,900)",
] as $token){
    if(!str_contains($j,$token)){
        throw new RuntimeException("JS progress token absent: ".$token);
    }
}

if(!str_contains($t,'r38_2a')){
    throw new RuntimeException('cache-bust r38_2a absent');
}

echo "R38_2A_CONTRACT_OK\n";
