<?php
$root = $argv[1] ?? 'H:\\EZScore_v1';
$js = $root . '/public/assets/js/lyricslab-r37.js';
$twig = $root . '/templates/song/lyricslab.html.twig';

$src = file_get_contents($js);
$required = [
    'R38.13b: time-signature agnostic continuous projection',
    'displayMeasureIndex=Math.floor(displaySeq/beatsPerMeasure)',
    'displayBeatIndex=displaySeq%beatsPerMeasure',
    'display_start_ms:row.startMs',
    'displaySynthetic:false',
    'displayBeatIndex===0',
];
foreach ($required as $needle) {
    if (strpos($src, $needle) === false) {
        fwrite(STDERR, "Missing invariant: $needle\n");
        exit(1);
    }
}
$forbidden = [
    'const byMeasure=new Map();',
    'selectedStartMs+slot*slotStepMs',
    "id:`synthetic:",
];
foreach ($forbidden as $needle) {
    if (strpos($src, $needle) !== false) {
        fwrite(STDERR, "Forbidden stale/synthetic projection remains: $needle\n");
        exit(1);
    }
}
if (strpos(file_get_contents($twig), '20260928r38_13b') === false) {
    fwrite(STDERR, "Missing JS cache buster r38_13b\n");
    exit(1);
}
echo "R38_13B_CONTINUOUS_GRID_CONTRACT_OK\n";
