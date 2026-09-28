<?php
declare(strict_types=1);

$root = $argv[1] ?? 'H:\\EZScore_v1';

function fail_contract(string $message): never {
    fwrite(STDERR, $message."\n");
    exit(1);
}

$controller = @file_get_contents($root.'/src/Controller/SongLabController.php');
$template = @file_get_contents($root.'/templates/song/lyricslab.html.twig');
$routes = @file_get_contents($root.'/config/routes.yaml');

if ($controller === false || $template === false || $routes === false) {
    fail_contract('Missing application file required by R38.15a');
}

foreach ([
    'LyricsSourceHistoryService $lyricsHistory',
    'Sauvegarde automatique avant extraction Whisper.',
    "$jobs->queue($song, $user, 'extract');",
] as $needle) {
    if (strpos($controller, $needle) === false) {
        fail_contract("SongLabController missing: $needle");
    }
}

foreach ([
    'data-lyrics-history',
    'Commentaire personnel',
    'Lyrics.ovh',
    'lyrics-history-r38-15.js',
    'lyrics-history-r38-15.css',
] as $needle) {
    if (strpos($template, $needle) === false) {
        fail_contract("LyricsLab template missing: $needle");
    }
}

if (substr_count($template, 'data-lyrics-history') !== 1) {
    fail_contract('LyricsLab history UI must be installed exactly once');
}

if (strpos($routes, 'LyricsHistoryController.php') === false ||
    strpos($routes, 'localized_lyrics_history:') === false) {
    fail_contract('LyricsHistoryController is not imported in config/routes.yaml');
}

$historyController = @file_get_contents($root.'/src/Controller/LyricsHistoryController.php');
if ($historyController === false ||
    strpos($historyController, 'app_song_lyrics_history') === false ||
    strpos($historyController, 'app_song_lyrics_history_save') === false ||
    strpos($historyController, 'app_song_lyrics_history_restore') === false ||
    strpos($historyController, 'app_song_lyrics_history_delete') === false) {
    fail_contract('Lyrics history routes contract missing');
}

$repo = @file_get_contents($root.'/src/Domain/Song/LyricsSourceRevisionRepository.php');
if ($repo === false || strpos($repo, 'setMaxResults(10)') !== false) {
    fail_contract('History must remain unlimited');
}

echo "R38_15A_REPAIR_CONTRACT_OK\n";
