<?php
declare(strict_types=1);
$root=$argv[1]??dirname(__DIR__,2);
$p=$root.'/templates/layout/song/_workflow_tabs.html.twig';
if(!is_file($p)) throw new RuntimeException('workflow tabs absent');
$s=(string)file_get_contents($p);
foreach(['TABLEAU DE BORD','IMPORT','ÉDITION','STEMSLAB','CHORDSLAB','LYRICSLAB','PUBLICATION'] as $token){
    if(!str_contains($s,$token)) throw new RuntimeException("onglet absent: $token");
}
foreach(['wf.can_stems','wf.can_chords','wf.can_lyrics','wf.can_publish'] as $token){
    if(!str_contains($s,$token)) throw new RuntimeException("garde workflow absente: $token");
}
if(str_contains($s,'dashboard-only-tab')) throw new RuntimeException('mode onglet unique encore présent');
echo "R35_5A_CONTRACT_OK\n";
