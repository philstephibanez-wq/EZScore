<?php
declare(strict_types=1);
$root=dirname(__DIR__);
$css=file_get_contents($root.'/public/assets/css/chordslab.css');
$main=file_get_contents($root.'/public/assets/js/chordslab.js');
$scroll=file_get_contents($root.'/public/assets/js/chordslab-r33-1.js');
$checks=[
 'R34.4 CSS present'=>str_contains($css,'R34.4 — chord typography'),
 'long chord global shrink disabled'=>str_contains($css,'.chord-slot.is-long')&&str_contains($css,'font-size:14px!important'),
 'root fixed size'=>str_contains($css,'.chord-label-root')&&str_contains($css,'font-size:15px!important'),
 'maj independently small'=>str_contains($css,'.chord-quality-maj')&&str_contains($css,'font-size:8px!important'),
 'guitar toggle full row'=>str_contains($css,'grid-column:1 / -1!important'),
 'tempo display installed'=>str_contains($main,'Tempo = ${tempo}'),
 'tempo comes from beats'=>str_contains($main,'60000/median'),
 'pause disables autoscroll'=>str_contains($scroll,"playbackActive=false")&&str_contains($scroll,'if(!playbackActive)return;'),
];
foreach($checks as $label=>$ok){if(!$ok){fwrite(STDERR,"FAIL: $label\n");exit(1);}echo "OK: $label\n";}
echo "\n".count($checks)." R34.4 checks passed.\n";
