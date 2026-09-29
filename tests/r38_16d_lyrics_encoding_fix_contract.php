<?php
declare(strict_types=1);

$root = $argv[1] ?? 'H:\\EZScore_v1';

function fail_contract(string $message): never {
    fwrite(STDERR, $message.PHP_EOL);
    exit(1);
}

$normalizerPath = $root.'/src/Service/LyricsTextNormalizer.php';
$clientPath = $root.'/src/Service/LyricsOvhClient.php';

if (!is_file($normalizerPath) || !is_file($clientPath)) {
    fail_contract('R38.16d files missing');
}

$normalizer = file_get_contents($normalizerPath);
$client = file_get_contents($clientPath);

foreach ([
    'Windows-1252',
    'ISO-8859-1',
    'Macintosh',
    'mojibakeScore',
    'normaliseImportedLyrics',
] as $needle) {
    if (strpos($normalizer, $needle) === false) {
        fail_contract('Normalizer contract missing: '.$needle);
    }
}

foreach ([
    'LyricsTextNormalizer $normalizer',
    'normaliseImportedLyrics($lyrics)',
] as $needle) {
    if (strpos($client, $needle) === false) {
        fail_contract('LyricsOvhClient contract missing: '.$needle);
    }
}

/*
 * Realistic mojibake probes:
 * - UTF-8 decoded as Windows-1252: "FranÃ§ais" -> "Français"
 * - UTF-8 decoded as MacRoman: "pr√®s" -> "près"
 */
require_once $normalizerPath;

$service = new \App\Service\LyricsTextNormalizer();

$windows = $service->normaliseImportedLyrics('FranÃ§ais');
if ($windows !== 'Français') {
    fail_contract('Windows-1252 repair failed: '.$windows);
}

$mac = $service->normaliseImportedLyrics('Je suis assis pr√®s de toi');
if ($mac !== 'Je suis assis près de toi') {
    fail_contract('MacRoman repair failed: '.$mac);
}

$clean = "Déjà près de l'âme";
if ($service->normaliseImportedLyrics($clean) !== $clean) {
    fail_contract('Clean UTF-8 text must remain unchanged');
}

echo "R38_16D_LYRICS_ENCODING_FIX_CONTRACT_OK".PHP_EOL;
