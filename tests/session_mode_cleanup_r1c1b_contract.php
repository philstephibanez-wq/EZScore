<?php
declare(strict_types=1);

$root = dirname(__DIR__);

$mustExist = [
    'migrations/Version20261002201000.php' => ['DROP COLUMN mode'],
    'templates/base.html.twig' => ["path('app_events'"],
    'templates/events/show.html.twig' => ['Tester la session'],
    'src/Domain/Event/LiveRun.php' => ['final class LiveRun'],
];

foreach ($mustExist as $rel => $needles) {
    $path = $root.DIRECTORY_SEPARATOR.str_replace('/', DIRECTORY_SEPARATOR, $rel);
    if (!is_file($path)) {
        fwrite(STDERR, "SESSION_MODE_CLEANUP_R1C1B missing file: {$rel}\n");
        exit(1);
    }
    $text = file_get_contents($path);
    foreach ($needles as $needle) {
        if (!str_contains($text, $needle)) {
            fwrite(STDERR, "SESSION_MODE_CLEANUP_R1C1B missing contract: {$rel} :: {$needle}\n");
            exit(1);
        }
    }
}

$mustBeAbsent = [
    'src/Domain/Event/Event.php' => ['EventMode', 'getMode(', 'setMode(', '$mode'],
    'src/Controller/EventController.php' => ['EventMode', "get('mode'", 'e.mode = :mode'],
    'templates/events/index.html.twig' => ['event.fields.mode', 'event.mode.', 'filters.mode', 'name="mode"'],
    'templates/events/show.html.twig' => ['event.fields.mode', 'event.mode.', 'name="mode"'],
    'templates/base.html.twig' => ["path('app_concert_control')"],
];

foreach ($mustBeAbsent as $rel => $needles) {
    $path = $root.DIRECTORY_SEPARATOR.str_replace('/', DIRECTORY_SEPARATOR, $rel);
    $text = file_get_contents($path);
    foreach ($needles as $needle) {
        if (str_contains($text, $needle)) {
            fwrite(STDERR, "SESSION_MODE_CLEANUP_R1C1B residual: {$rel} :: {$needle}\n");
            exit(1);
        }
    }
}

if (is_file($root.'/src/Domain/Event/EventMode.php')) {
    fwrite(STDERR, "SESSION_MODE_CLEANUP_R1C1B residual EventMode.php\n");
    exit(1);
}

echo "SESSION_MODE_CLEANUP_R1C1B_CONTRACT_OK\n";
