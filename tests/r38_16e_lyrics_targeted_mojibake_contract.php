<?php
declare(strict_types=1);

$root = $argv[1] ?? 'H:\\EZScore_v1';
$normalizerPath = $root.'/src/Service/LyricsTextNormalizer.php';

if (!is_file($normalizerPath)) {
    fwrite(STDERR, "Missing LyricsTextNormalizer.php\n");
    exit(1);
}

require_once $normalizerPath;
$service = new \App\Service\LyricsTextNormalizer();

$cases = [
    'Je me suis assis prâ¨s de son âgme' => 'Je me suis assis près de son âme',
    'Je me suis assis prâˆšs de son âˆšme' => 'Je me suis assis près de son âme',
    'Je suis assis pr√®s de toi' => 'Je suis assis près de toi',
    'Déjà près de son âme' => 'Déjà près de son âme',
];

foreach ($cases as $input => $expected) {
    $actual = $service->normaliseImportedLyrics($input);
    if ($actual !== $expected) {
        fwrite(
            STDERR,
            "Targeted mojibake repair failed.\nINPUT: ".$input.
            "\nEXPECTED: ".$expected.
            "\nACTUAL: ".$actual.PHP_EOL
        );
        exit(1);
    }
}

$source = file_get_contents($normalizerPath);
foreach ([
    'applyLyricsOvhTargetedRepairs',
    "'prâ¨s' => 'près'",
    "'âgme' => 'âme'",
] as $needle) {
    if (strpos($source, $needle) === false) {
        fwrite(STDERR, "Missing targeted repair contract: ".$needle.PHP_EOL);
        exit(1);
    }
}

echo "R38_16E_LYRICS_TARGETED_MOJIBAKE_CONTRACT_OK".PHP_EOL;
