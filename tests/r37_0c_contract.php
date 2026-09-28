<?php
declare(strict_types=1);

$root=$argv[1]??dirname(__DIR__,2);
$path=$root.'/src/Controller/SongLabController.php';

if(!is_file($path)){
    throw new RuntimeException('SongLabController absent');
}

$s=(string)file_get_contents($path);

$tokens=[
    "app_song_lyricslab_extract",
    '$jobs->queue($song, $user, \'extract\');',
];

foreach($tokens as $token){
    if(!str_contains($s,$token)){
        throw new RuntimeException("Token absent: ".$token);
    }
}

echo "R37_0C_CONTRACT_OK\n";
