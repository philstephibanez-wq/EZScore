<?php
$root = $argv[1] ?? 'H:\\EZScore_v1';
$js = $root . '/public/assets/js/lyricslab-r37.js';
$twig = $root . '/templates/song/lyricslab.html.twig';
$src = file_get_contents($js);

$required = [
    'R38.13b: time-signature agnostic continuous projection',
    'R38.13c: restore chord lane runtime declaration',
    'const left=xBeat(i),next=',
];
foreach ($required as $needle) {
    if (strpos($src, $needle) === false) {
        fwrite(STDERR, "Missing invariant: $needle\n");
        exit(1);
    }
}
if (strpos($src, ';left=xBeat(i),next=') !== false) {
    fwrite(STDERR, "Broken undeclared left assignment still present\n");
    exit(1);
}
if (strpos(file_get_contents($twig), '20260928r38_13c') === false) {
    fwrite(STDERR, "Missing JS cache buster r38_13c\n");
    exit(1);
}
echo "R38_13C_RESTORE_CHORDS_CONTRACT_OK\n";
