<?php
declare(strict_types=1);

$root = $argv[1] ?? 'H:\\EZScore_v1';

function fail_contract(string $message): never {
    fwrite(STDERR, $message.PHP_EOL);
    exit(1);
}

$client = @file_get_contents($root.'/src/Service/LyricsOvhClient.php');
$controller = @file_get_contents($root.'/src/Controller/LyricsOvhController.php');
$routes = @file_get_contents($root.'/config/routes.yaml');
$template = @file_get_contents($root.'/templates/song/lyricslab.html.twig');

if ($client === false || $controller === false || $routes === false || $template === false) {
    fail_contract('Missing R38.16i files');
}

foreach ([
    'public function suggestFast(',
    "self::BASE_URL.'/suggest/'",
] as $needle) {
    if (strpos($client, $needle) === false) {
        fail_contract('Fast autocomplete client missing: '.$needle);
    }
}

foreach ([
    "Route('/autocomplete'",
    "name: 'app_song_lyrics_ovh_autocomplete'",
    'suggestFast($query, 6)',
] as $needle) {
    if (strpos($controller, $needle) === false) {
        fail_contract('Autocomplete controller route missing: '.$needle);
    }
}

if (strpos($routes, 'LyricsOvhController.php') === false) {
    fail_contract('LyricsOvhController route import missing');
}

if (strpos($template, 'app_song_lyrics_ovh_autocomplete') === false) {
    fail_contract('Template autocomplete route reference missing');
}

echo "R38_16I1_AUTOCOMPLETE_ROUTE_REPAIR_CONTRACT_OK".PHP_EOL;
