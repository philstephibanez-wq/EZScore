<?php
declare(strict_types=1);
$root=$argv[1]??dirname(__DIR__,2);
$a=(string)file_get_contents($root.'/analysis/lyrics_timeline_analysis.py');
$t=(string)file_get_contents($root.'/templates/song/lyricslab.html.twig');
$j=(string)file_get_contents($root.'/public/assets/js/lyricslab-r37.js');
foreach(['tempfile.mkstemp(','os.replace(tmp, p)','except PermissionError as exc'] as $x) if(!str_contains($a,$x)) throw new RuntimeException($x);
foreach(['r38_0b','Prompteur en lecture seule'] as $x) if(!str_contains($t,$x)) throw new RuntimeException($x);
foreach(['lyrics-simple-chord','lyrics-simple-section','function poll()'] as $x) if(!str_contains($j,$x)) throw new RuntimeException($x);
echo "R38_0B_CONTRACT_OK\n";
