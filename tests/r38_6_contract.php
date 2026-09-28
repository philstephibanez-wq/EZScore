<?php
declare(strict_types=1);
$root=$argv[1]??dirname(__DIR__,2);
$a=(string)file_get_contents($root.'/analysis/lyrics_timeline_analysis.py');
$t=(string)file_get_contents($root.'/templates/song/lyricslab.html.twig');
$j=(string)file_get_contents($root.'/public/assets/js/lyricslab-r38-6-fix.js');
foreach(['def _r386_first_phrase(','def _r386_forward_candidate(','first acoustic phrase is written once and NEVER overwritten','There is no global matching pass after this point.'] as $token){if(!str_contains($a,$token))throw new RuntimeException('lyrics token absent: '.$token);}
if(substr_count($a,'def align_provided_text(')!==1)throw new RuntimeException('align_provided_text count != 1');
foreach(['data-song-id="{{ song.id }}"','lyricslab-r38-6-fix.js?v=20260928r38_6'] as $token){if(!str_contains($t,$token))throw new RuntimeException('twig token absent: '.$token);}
foreach(['TEMPO','tempoFromBeats','ezscore:lyricslab:diagram:v2:'] as $token){if(!str_contains($j,$token))throw new RuntimeException('js token absent: '.$token);}
echo "R38_6_CONTRACT_OK\n";
