<?php
declare(strict_types=1);

$root = $argv[1] ?? 'H:\\EZScore_v1';
$js = @file_get_contents($root.'/public/assets/js/lyrics-ovh-r38-16.js');
$css = @file_get_contents($root.'/public/assets/css/lyrics-ovh-r38-16.css');
$template = @file_get_contents($root.'/templates/song/lyricslab.html.twig');

if ($js === false || $css === false || $template === false) {
    fwrite(STDERR, "Missing autocomplete files\n");
    exit(1);
}

foreach ([
    'function autocompleteSearch()',
    'setTimeout(autocompleteSearch, 300)',
    "event.key === 'ArrowDown'",
    "event.key === 'ArrowUp'",
    "event.key === 'Escape'",
    'data-lyrics-ovh-autocomplete-item',
] as $needle) {
    if (strpos($js, $needle) === false) {
        fwrite(STDERR, "Missing JS contract: ".$needle.PHP_EOL);
        exit(1);
    }
}

foreach ([
    'data-lyrics-ovh-autocomplete',
    'lyrics-ovh-r38-16.js?v=20260929r38_16h',
    'lyrics-ovh-r38-16.css?v=20260929r38_16h',
] as $needle) {
    if (strpos($template, $needle) === false) {
        fwrite(STDERR, "Missing template contract: ".$needle.PHP_EOL);
        exit(1);
    }
}

if (strpos($css, '.lyrics-ovh-autocomplete') === false) {
    fwrite(STDERR, "Autocomplete CSS missing\n");
    exit(1);
}

echo "R38_16H_LYRICS_OVH_AUTOCOMPLETE_CONTRACT_OK".PHP_EOL;
