<?php
declare(strict_types=1);
$root = $argv[1] ?? 'H:\\EZScore_v1';
$js = @file_get_contents($root.'/public/assets/js/lyrics-history-r38-15.js');
$css = @file_get_contents($root.'/public/assets/css/lyrics-history-r38-15.css');
if ($js === false || $css === false) { fwrite(STDERR, "Missing assets\n"); exit(1); }
foreach (['alert(', 'confirm(', 'prompt('] as $forbidden) {
    if (strpos($js, $forbidden) !== false) { fwrite(STDERR, "Forbidden native dialog: $forbidden\n"); exit(1); }
}
foreach (['function ezConfirm(', "await ezConfirm('Restaurer cette version complète des paroles ?'", "await ezConfirm('Jeter définitivement cette sauvegarde ?'"] as $required) {
    if (strpos($js, $required) === false) { fwrite(STDERR, "Missing modal contract: $required\n"); exit(1); }
}
if (strpos($css, '.ez-modal-backdrop') === false) { fwrite(STDERR, "Missing modal CSS\n"); exit(1); }
echo "R38_15C_NO_BROWSER_ALERT_CONTRACT_OK\n";
