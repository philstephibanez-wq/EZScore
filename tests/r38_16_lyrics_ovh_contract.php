<?php
declare(strict_types=1);

$root = $argv[1] ?? 'H:\\EZScore_v1';

function fail_contract(string $message): never
{
    fwrite(STDERR, $message.PHP_EOL);
    exit(1);
}

$required = [
    'src/Service/LyricsOvhClient.php',
    'src/Controller/LyricsOvhController.php',
    'public/assets/js/lyrics-ovh-r38-16.js',
    'public/assets/css/lyrics-ovh-r38-16.css',
];

foreach ($required as $relative) {
    if (!is_file($root.'/'.$relative)) {
        fail_contract('Missing file: '.$relative);
    }
}

$client = file_get_contents($root.'/src/Service/LyricsOvhClient.php');
foreach (['https://api.lyrics.ovh', '/suggest/', '/v1/', 'HttpClientInterface'] as $needle) {
    if (strpos($client, $needle) === false) {
        fail_contract('LyricsOvhClient missing: '.$needle);
    }
}

$controller = file_get_contents($root.'/src/Controller/LyricsOvhController.php');
foreach (['app_song_lyrics_ovh_search', 'app_song_lyrics_ovh_import', 'LyricsSourceHistoryService', "'lyrics_ovh'", 'Sauvegarde automatique avant recherche Lyrics.ovh.'] as $needle) {
    if (strpos($controller, $needle) === false) {
        fail_contract('LyricsOvhController missing: '.$needle);
    }
}

$template = file_get_contents($root.'/templates/song/lyricslab.html.twig');
foreach (['data-lyrics-ovh', 'Chercher les paroles', 'data-lyrics-ovh-query', 'lyrics-ovh-r38-16.js', 'lyrics-ovh-r38-16.css'] as $needle) {
    if (strpos($template, $needle) === false) {
        fail_contract('LyricsLab template missing: '.$needle);
    }
}

$routes = file_get_contents($root.'/config/routes.yaml');
if (strpos($routes, 'LyricsOvhController.php') === false) {
    fail_contract('LyricsOvhController is not imported in routes.yaml');
}

$js = file_get_contents($root.'/public/assets/js/lyrics-ovh-r38-16.js');
foreach (['confirm(', 'alert(', 'prompt('] as $forbidden) {
    if (strpos($js, $forbidden) !== false) {
        fail_contract('Native browser dialog forbidden: '.$forbidden);
    }
}

echo "R38_16_LYRICS_OVH_CONTRACT_OK".PHP_EOL;
