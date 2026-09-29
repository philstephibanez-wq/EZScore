<?php
declare(strict_types=1);
$root = $argv[1] ?? 'H:\\EZScore_v1';
$template = @file_get_contents($root.'/templates/song/lyricslab.html.twig');
$js = @file_get_contents($root.'/public/assets/js/lyrics-ovh-r38-16.js');

if ($template === false || $js === false) {
    fwrite(STDERR, "Missing Lyrics.ovh files\n");
    exit(1);
}

if (substr_count($template, 'class="lyrics-ovh-toolbar"') !== 1) {
    fwrite(STDERR, "Expected one top Lyrics.ovh toolbar\n");
    exit(1);
}
if (strpos($template, 'class="lyrics-ovh-search"') !== false) {
    fwrite(STDERR, "Legacy search block still present\n");
    exit(1);
}
if (substr_count($template, 'data-lyrics-ovh-results') !== 1 ||
    substr_count($template, 'data-lyrics-ovh-status') !== 1) {
    fwrite(STDERR, "Expected one Lyrics.ovh output block\n");
    exit(1);
}

$output = strpos($template, 'data-lyrics-ovh-output');
$textarea = strpos($template, '<textarea data-lyrics-source');
if ($output === false || $textarea === false || $output > $textarea) {
    fwrite(STDERR, "Lyrics.ovh result list must be above the lyrics textarea\n");
    exit(1);
}

if (strpos($js, "const resultsHost = document.querySelector('[data-lyrics-ovh-results]');") === false ||
    strpos($js, "const status = document.querySelector('[data-lyrics-ovh-status]');") === false) {
    fwrite(STDERR, "JS output selectors not repaired\n");
    exit(1);
}

if (strpos($template, 'lyrics-ovh-r38-16.js?v=20260929r38_16c2') === false) {
    fwrite(STDERR, "Cache bust missing\n");
    exit(1);
}

echo "R38_16C2_LYRICS_OVH_RESULTS_ABOVE_CONTRACT_OK\n";
