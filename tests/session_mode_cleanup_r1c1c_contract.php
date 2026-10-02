<?php
declare(strict_types=1);

$root = dirname(__DIR__);

$absent = [
    'src/Domain/Event/Event.php' => ['EventMode', '$mode', 'getMode(', 'setMode('],
    'src/Controller/EventController.php' => ['EventMode', "get('mode'", 'e.mode = :mode'],
    'templates/events/index.html.twig' => ['event.fields.mode', 'event.mode.', 'filters.mode', 'name="mode"'],
    'templates/events/show.html.twig' => ['event.fields.mode', 'event.mode.', 'name="mode"'],
    'templates/base.html.twig' => ["path('app_concert_control')"],
];

foreach ($absent as $rel => $needles) {
    $path = $root.DIRECTORY_SEPARATOR.str_replace('/', DIRECTORY_SEPARATOR, $rel);
    if (!is_file($path)) {
        fwrite(STDERR, "SESSION_MODE_CLEANUP_R1C1C missing: {$rel}\n");
        exit(1);
    }
    $text = file_get_contents($path);
    foreach ($needles as $needle) {
        if (str_contains($text, $needle)) {
            fwrite(STDERR, "SESSION_MODE_CLEANUP_R1C1C residual: {$rel} :: {$needle}\n");
            exit(1);
        }
    }
}

if (is_file($root.'/src/Domain/Event/EventMode.php')) {
    fwrite(STDERR, "SESSION_MODE_CLEANUP_R1C1C residual EventMode.php\n");
    exit(1);
}

$required = [
    'templates/base.html.twig' => ["path('app_events'"],
    'templates/events/show.html.twig' => ['Tester la session'],
    'src/Domain/Event/LiveRun.php' => ['final class LiveRun'],
    'migrations/Version20261002201000.php' => ['DROP COLUMN mode'],
];

foreach ($required as $rel => $needles) {
    $path = $root.DIRECTORY_SEPARATOR.str_replace('/', DIRECTORY_SEPARATOR, $rel);
    if (!is_file($path)) {
        fwrite(STDERR, "SESSION_MODE_CLEANUP_R1C1C required missing: {$rel}\n");
        exit(1);
    }
    $text = file_get_contents($path);
    foreach ($needles as $needle) {
        if (!str_contains($text, $needle)) {
            fwrite(STDERR, "SESSION_MODE_CLEANUP_R1C1C required token missing: {$rel} :: {$needle}\n");
            exit(1);
        }
    }
}

echo "SESSION_MODE_CLEANUP_R1C1C_CONTRACT_OK\n";
