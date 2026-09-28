<?php
declare(strict_types=1);

$root=$argv[1]??dirname(__DIR__,2);
$path=$root.'/src/Controller/AnalysisDesktopController.php';
if(!is_file($path)) throw new RuntimeException('AnalysisDesktopController absent');

$s=(string)file_get_contents($path);

$tokens=[
    "ezscore.lyrics.extract.r37",
    'setLyricsSourceText($text)',
    "\$mode === 'extract'",
    'lyricsResults->apply($job->getSong(), $result)',
];

foreach($tokens as $token){
    if(!str_contains($s,$token)){
        throw new RuntimeException("Token absent: ".$token);
    }
}

echo "R37_0E_CONTRACT_OK\n";
