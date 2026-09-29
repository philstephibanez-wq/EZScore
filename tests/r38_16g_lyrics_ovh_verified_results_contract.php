<?php
declare(strict_types=1);

$root = $argv[1] ?? 'H:\\EZScore_v1';

function fail_contract(string $message): never {
    fwrite(STDERR, $message.PHP_EOL);
    exit(1);
}

$client = @file_get_contents($root.'/src/Service/LyricsOvhClient.php');
$controller = @file_get_contents($root.'/src/Controller/LyricsOvhController.php');
$js = @file_get_contents($root.'/public/assets/js/lyrics-ovh-r38-16.js');
$template = @file_get_contents($root.'/templates/song/lyricslab.html.twig');

if ($client === false || $controller === false || $js === false || $template === false) {
    fail_contract('Missing Lyrics.ovh files');
}

foreach ([
    "'available' => false",
    'relevanceScore(',
    'normaliseSearchKey(',
    'getStatusCode() !== 200',
] as $needle) {
    if (strpos($client, $needle) === false) {
        fail_contract('LyricsOvhClient missing contract: '.$needle);
    }
}

foreach (['$song->getArtist()', '$song->getTitle()'] as $needle) {
    if (strpos($controller, $needle) === false) {
        fail_contract('Controller ranking hint missing: '.$needle);
    }
}

foreach (['Paroles indisponibles', 'item.available', 'data-lyrics-ovh-use'] as $needle) {
    if (strpos($js, $needle) === false) {
        fail_contract('JS availability UI missing: '.$needle);
    }
}

if (strpos($template, 'lyrics-ovh-r38-16.js?v=20260929r38_16g') === false) {
    fail_contract('R38.16g cache bust missing');
}

echo "R38_16G_LYRICS_OVH_VERIFIED_RESULTS_CONTRACT_OK".PHP_EOL;
