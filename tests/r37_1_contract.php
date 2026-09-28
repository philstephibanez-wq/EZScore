<?php
declare(strict_types=1);

$root=$argv[1]??dirname(__DIR__,2);
$js=(string)file_get_contents($root.'/public/assets/js/lyricslab-r37.js');
$css=(string)file_get_contents($root.'/public/assets/css/lyricslab-r37.css');

$jsTokens=[
    'function syllablesForEvent',
    'fallbackSyllables',
    'track.style.transform=',
    'ezscore:audio-timeupdate',
    'is-word-current',
    'is-current',
];
foreach($jsTokens as $token){
    if(!str_contains($js,$token)) throw new RuntimeException("JS token absent: ".$token);
}
if(str_contains($js,'scrollIntoView(')){
    throw new RuntimeException('scrollIntoView interdit dans le prompteur');
}
if(str_contains($css,'karaoke-playhead')){
    throw new RuntimeException('barre verticale encore présente');
}
foreach(['font-size:30px','font-size:32px','.ez-karaoke-syllable.is-current'] as $token){
    if(!str_contains($css,$token)) throw new RuntimeException("CSS token absent: ".$token);
}
echo "R37_1_CONTRACT_OK\n";
