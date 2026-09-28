<?php
declare(strict_types=1);

$root=$argv[1]??dirname(__DIR__,2);
$twig=(string)file_get_contents($root.'/templates/song/lyricslab.html.twig');
$controller=(string)file_get_contents($root.'/src/Controller/SongLabController.php');
$js=(string)file_get_contents($root.'/public/assets/js/lyricslab-r37.js');

foreach(['id="lyrics-analyze-form"','name="lyrics_source"','form="lyrics-analyze-form"'] as $token){
    if(!str_contains($twig,$token)) throw new RuntimeException('Twig token absent: '.$token);
}
foreach(['$request->request->get(\'lyrics_source\'','EntityManagerInterface $em'] as $token){
    if(!str_contains($controller,$token)) throw new RuntimeException('Controller token absent: '.$token);
}
if(!str_contains($controller,'$jobs->queue($song,$user,\'align\');')
   && !str_contains($controller,'$jobs->queue($song, $user, \'align\');')){
    throw new RuntimeException('queue align absente');
}
if(str_contains($js,'data-lyrics-analyze-form')){
    throw new RuntimeException('ancien intercepteur Analyze JS encore présent');
}
echo "R37_0H_CONTRACT_OK\n";
