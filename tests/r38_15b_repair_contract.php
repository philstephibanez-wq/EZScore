<?php
declare(strict_types=1);

$root = $argv[1] ?? 'H:\\EZScore_v1';

function contract_fail(string $message): never
{
    fwrite(STDERR, $message.PHP_EOL);
    exit(1);
}

$controller = @file_get_contents($root.'/src/Controller/SongLabController.php');
$template = @file_get_contents($root.'/templates/song/lyricslab.html.twig');
$routes = @file_get_contents($root.'/config/routes.yaml');

if ($controller === false || $template === false || $routes === false) {
    contract_fail('Missing application file required by R38.15b');
}

$controllerChecks = [
    'LyricsSourceHistoryService $lyricsHistory',
    'Sauvegarde automatique avant extraction Whisper.',
    '$jobs->queue($song, $user, \'extract\');',
];

foreach ($controllerChecks as $needle) {
    if (strpos($controller, $needle) === false) {
        contract_fail('SongLabController missing: '.$needle);
    }
}

$templateChecks = [
    'data-lyrics-history',
    'Commentaire personnel',
    'Lyrics.ovh',
    'lyrics-history-r38-15.js',
    'lyrics-history-r38-15.css',
];

foreach ($templateChecks as $needle) {
    if (strpos($template, $needle) === false) {
        contract_fail('LyricsLab template missing: '.$needle);
    }
}

if (substr_count($template, 'data-lyrics-history') !== 1) {
    contract_fail('LyricsLab history UI must be present exactly once');
}

if (strpos($routes, 'localized_lyrics_history:') === false ||
    strpos($routes, 'LyricsHistoryController.php') === false) {
    contract_fail('LyricsHistoryController route import missing');
}

$historyController = @file_get_contents($root.'/src/Controller/LyricsHistoryController.php');
if ($historyController === false) {
    contract_fail('LyricsHistoryController.php missing');
}

foreach ([
    'app_song_lyrics_history',
    'app_song_lyrics_history_save',
    'app_song_lyrics_history_restore',
    'app_song_lyrics_history_delete',
] as $routeName) {
    if (strpos($historyController, $routeName) === false) {
        contract_fail('Missing history route name: '.$routeName);
    }
}

$repository = @file_get_contents($root.'/src/Domain/Song/LyricsSourceRevisionRepository.php');
if ($repository === false || strpos($repository, 'setMaxResults(10)') !== false) {
    contract_fail('Lyrics history must remain unlimited');
}

echo "R38_15B_REPAIR_CONTRACT_OK".PHP_EOL;
