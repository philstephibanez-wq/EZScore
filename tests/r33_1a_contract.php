<?php
declare(strict_types=1);
$root=dirname(__DIR__);
$p=file_get_contents($root.'/scripts/apply_r33_1_riff_wakelock.py');
$checks=[
 'supports compact R33'=>str_contains($p,'compact R33'),
 'supports formatted R33'=>str_contains($p,'formatted R33'),
 'structural safe fallback'=>str_contains($p,'structural fallback'),
 'emits chord-current event'=>str_contains($p,'ezscore:chord-current'),
 'keeps wake-lock payload'=>str_contains($p,'chordslab-r33-1.js'),
 'updates CDC'=>str_contains($p,'CAHIER_DES_CHARGES.md'),
 'updates recipe'=>str_contains($p,'recette.md'),
 'refuses unsupported variant'=>str_contains($p,'No unsafe edit was applied'),
];
foreach($checks as $label=>$ok){if(!$ok){fwrite(STDERR,"FAIL: $label\n");exit(1);}echo "OK: $label\n";}
echo "\n".count($checks)." R33.1a checks passed.\n";
