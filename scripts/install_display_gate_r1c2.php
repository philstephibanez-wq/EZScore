<?php
declare(strict_types=1);

$root = dirname(__DIR__);
$payload = __DIR__.'/../payload';

function copyStrict(string $from, string $to): void {
    if (!is_file($from)) throw new RuntimeException('Missing payload: '.$from);
    $dir = dirname($to);
    if (!is_dir($dir) && !mkdir($dir, 0777, true) && !is_dir($dir)) {
        throw new RuntimeException('Cannot create dir: '.$dir);
    }
    if (!copy($from, $to)) throw new RuntimeException('Copy failed: '.$to);
}

foreach ([
    'src/Controller/LiveRunController.php',
    'src/EventSubscriber/DisplayUserGateSubscriber.php',
    'templates/live/display_home.html.twig',
    'templates/live/display.html.twig',
    'public/assets/js/live/display-gate-r1c2.js',
    'public/assets/css/live/display-gate-r1c2.css',
] as $rel) {
    copyStrict($payload.'/'.$rel, $root.'/'.$rel);
}

echo "DISPLAY_GATE_R1C2_INSTALL_OK\n";
