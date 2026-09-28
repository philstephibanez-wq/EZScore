<?php
declare(strict_types=1);
$root=$argv[1]??dirname(__DIR__,2);
$j=(string)file_get_contents($root.'/public/assets/js/lyricslab-r37.js');
$t=(string)file_get_contents($root.'/templates/song/lyricslab.html.twig');
$a=(string)file_get_contents($root.'/analysis/lyrics_timeline_analysis.py');
$c=(string)file_get_contents($root.'/src/Controller/ContactController.php');
$u=(string)file_get_contents($root.'/src/Domain/User/UserRepository.php');

foreach(['data-lyrics-profile','profileDataUrlTemplate','async function loadChordProfile','buildChords();'] as $x)
    if(!str_contains($j,$x) && !str_contains($t,$x)) throw new RuntimeException("profile token absent: ".$x);

foreach(['Prefix words are packed immediately before the first acoustic anchor.','window = min(1800'] as $x)
    if(!str_contains($a,$x)) throw new RuntimeException("alignment token absent: ".$x);

foreach(['findFirstAdmin()','->to($admin->getEmail())','%env(MAILER_FROM)%'] as $x)
    if(!str_contains($c,$x) && !str_contains($u,$x)) throw new RuntimeException("mail token absent: ".$x);

if(str_contains($c,'EZSCORE_ADMIN_CONTACT_EMAIL')) throw new RuntimeException('legacy admin env recipient still used');
if(!str_contains($t,'r38_2')) throw new RuntimeException('cache bust r38_2 absent');

echo "R38_2_CONTRACT_OK\n";
