<?php
declare(strict_types=1);

$root = dirname(__DIR__);
$required = [
    $root . '/public/assets/js/cast/ezscore-cast.js',
    $root . '/public/assets/js/cast/ezscore-cast-native-bridge.js',
    $root . '/public/assets/js/cast/ezscore-cast-ui.js',
    $root . '/public/assets/css/cast/ezscore-cast.css',
];

foreach ($required as $file) {
    if (!is_file($file)) {
        fwrite(STDERR, "MISSING: {$file}\n");
        exit(1);
    }
}

$core = file_get_contents($required[0]);
$native = file_get_contents($required[1]);
$ui = file_get_contents($required[2]);

$checks = [
    'window.EZScoreCast' => str_contains($core, 'window.EZScoreCast'),
    'registerProvider' => str_contains($core, 'registerProvider'),
    'scan() abstraction' => str_contains($core, 'async scan'),
    'connect() abstraction' => str_contains($core, 'async connect'),
    'disconnect() abstraction' => str_contains($core, 'async disconnect'),
    'native bridge' => str_contains($native, 'window.EZScoreNativeCast'),
    'no fake Miracast browser implementation' => !str_contains($core . $native . $ui, 'WiFiDirect'),
    'UI hidden without provider' => str_contains($ui, 'if (await cast.available()) createUi()'),
];

foreach ($checks as $label => $ok) {
    if (!$ok) {
        fwrite(STDERR, "FAILED: {$label}\n");
        exit(1);
    }
}

$forbidden = [
    $root . '/public/assets/js/audio/ezscore-audio-engine.js',
    $root . '/public/assets/js/ezscore-timeline-core-r39.js',
    $root . '/analysis/chord_timeline_analysis.py',
];

foreach ($forbidden as $file) {
    if (is_file($file) && str_contains(file_get_contents($file), 'EZScoreCast')) {
        fwrite(STDERR, "FORBIDDEN COUPLING: {$file}\n");
        exit(1);
    }
}

echo "CAST_R1_CONTRACT_OK\n";
