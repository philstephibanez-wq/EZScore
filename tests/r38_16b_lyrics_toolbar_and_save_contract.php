<?php
declare(strict_types=1);

$root = $argv[1] ?? 'H:\\EZScore_v1';
$template = @file_get_contents($root.'/templates/song/lyricslab.html.twig');

if ($template === false) {
    fwrite(STDERR, "Missing LyricsLab template\n");
    exit(1);
}

foreach ([
    'class="lyrics-ovh-toolbar"',
    'data-lyrics-ovh-query',
    'Chercher les paroles',
    'data-lyrics-ovh-results',
    'data-lyrics-history-savebar',
    'Sauvegarder cette version',
    'Historique des paroles',
] as $needle) {
    if (strpos($template, $needle) === false) {
        fwrite(STDERR, "Missing UI contract: $needle\n");
        exit(1);
    }
}

$actions = strpos($template, 'chordslab-prompter-actions lyricslab-actions');
$search = strpos($template, 'class="lyrics-ovh-toolbar"');
$extract = strpos($template, 'Extraire les paroles');
$analyze = strpos($template, 'Analyser les paroles');

if ($actions === false || $search === false || $extract === false || $analyze === false) {
    fwrite(STDERR, "Unable to locate top action toolbar\n");
    exit(1);
}

$textarea = strpos($template, '</textarea>');
$savebar = strpos($template, 'data-lyrics-history-savebar');
$details = strpos($template, '<details class="lyrics-history"');

if ($textarea === false || $savebar === false || $details === false || !($textarea < $savebar && $savebar < $details)) {
    fwrite(STDERR, "Save controls must stay visible below textarea, before collapsible history\n");
    exit(1);
}

echo "R38_16B_LYRICS_TOOLBAR_AND_SAVE_CONTRACT_OK\n";
