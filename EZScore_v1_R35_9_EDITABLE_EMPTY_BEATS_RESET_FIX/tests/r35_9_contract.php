<?php
declare(strict_types=1);
$root=$argv[1]??dirname(__DIR__,2);
$ctl=(string)file_get_contents($root.'/src/Controller/SongLabController.php');
foreach(['app_song_chordslab_beat_override','manual-beat-r35.9',"setOriginalValue('.')"] as $t){if(!str_contains($ctl,$t))throw new RuntimeException('controller token absent: '.$t);}
$svc=(string)file_get_contents($root.'/src/Service/ChordTimelineResultService.php');
foreach(['findBeatEvents($song)','findChordEvents($song)','$this->em->remove($existingChord)'] as $t){if(!str_contains($svc,$t))throw new RuntimeException('purge authoritative absent: '.$t);}
$twig=(string)file_get_contents($root.'/templates/song/chordslab.html.twig');
if(!str_contains($twig,'data-beat-edit-url-template'))throw new RuntimeException('beat edit URL absent');
if(!str_contains($twig,'20260928r35_9'))throw new RuntimeException('cache-bust R35.9 absent');
$js=(string)file_get_contents($root.'/public/assets/js/chordslab.js');
foreach(['editable:!!beat.id','data-beat-id','async function editSlot','beatEditUrlTemplate'] as $t){if(!str_contains($js,$t))throw new RuntimeException('JS token absent: '.$t);}
echo "R35_9_CONTRACT_OK\n";
