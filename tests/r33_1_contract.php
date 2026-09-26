<?php
declare(strict_types=1);
$root=dirname(__DIR__);
$a=file_get_contents($root.'/analysis/chord_timeline_analysis.py');
$s=file_get_contents($root.'/src/Service/ChordTimelineAnalysisService.php');
$w=file_get_contents($root.'/public/assets/js/chordslab-r33-1.js');
$p=file_get_contents($root.'/scripts/apply_r33_1_riff_wakelock.py');
$checks=[
 'harmonic stems'=>str_contains($s,"['bass','guitar','piano','other']"),
 'drums rhythm'=>str_contains($s,"stemPath(\$song,'drums')"),
 'triad priority'=>str_contains($a,'TRIADS'),
 'temporal smoothing'=>str_contains($a,'change={'),
 'key aware'=>str_contains($a,'diatonic'),
 'intermediate gate'=>str_contains($a,"margin<.085"),
 'centered event'=>str_contains($p,'ezscore:chord-current'),
 'centered scroll'=>str_contains($w,'strip.scrollBy'),
 'wake lock'=>str_contains($w,"navigator.wakeLock.request('screen')"),
 'wake release'=>str_contains($w,'releaseWakeLock'),
 'visibility recovery'=>str_contains($w,'visibilitychange'),
 'preference persisted'=>str_contains($w,'localStorage'),
 'CDC'=>str_contains($p,'CAHIER_DES_CHARGES.md'),
 'recette'=>str_contains($p,'recette.md'),
 'mobile'=>str_contains(file_get_contents($root.'/scripts/_payload/snippets/css_add.txt'),'@media(max-width:640px)'),
 'no migration'=>!str_contains($p,'doctrine:migrations'),
];
foreach($checks as $label=>$ok){if(!$ok){fwrite(STDERR,"FAIL: $label\n");exit(1);}echo "OK: $label\n";}
echo "\n".count($checks)." R33.1 checks passed.\n";
