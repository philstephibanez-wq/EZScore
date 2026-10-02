<?php
declare(strict_types=1);

$root = dirname(__DIR__);
$path = $root.'/templates/events/index.html.twig';

if (!is_file($path)) {
    fwrite(STDERR, "SESSION_PLACEHOLDER_R1 missing template\n");
    exit(1);
}

$text = file_get_contents($path);

if (substr_count($text, '<option value="">&mdash;</option>') < 2) {
    fwrite(STDERR, "SESSION_PLACEHOLDER_R1 placeholders not normalized\n");
    exit(1);
}

foreach (['â€”', 'â€“', 'Ã¢', '€', 'œ'] as $bad) {
    if (str_contains($text, $bad)) {
        fwrite(STDERR, "SESSION_PLACEHOLDER_R1 mojibake remains: {$bad}\n");
        exit(1);
    }
}

echo "SESSION_PLACEHOLDER_R1_CONTRACT_OK\n";
