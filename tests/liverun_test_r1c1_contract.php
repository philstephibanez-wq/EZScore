<?php
declare(strict_types=1);

$root = dirname(__DIR__);

$checks = [
    'src/Domain/Event/LiveRun.php' => ['final class LiveRun', "private string \$status = 'live'", 'private bool $testMode = true'],
    'src/Controller/LiveRunController.php' => ['app_live_test_start', 'app_live_test_stop', 'app_live_open', 'app_live_display', 'ROLE_DISPLAY'],
    'migrations/Version20261002194500.php' => ['CREATE TABLE live_runs', 'event_id', 'conductor_user_id'],
    'config/routes.yaml' => ['live_run_controller:', 'LiveRunController.php'],
    'templates/base.html.twig' => ['data-live-notification', 'app_live_open', 'live-notification-r1c1.js'],
    'templates/events/show.html.twig' => ['Tester la session', 'app_live_test_start', 'app_live_test_stop'],
    'templates/live/display.html.twig' => ['Display passif connecté.', 'local_display', 'conductor_local'],
];

foreach ($checks as $rel => $needles) {
    $path = $root.DIRECTORY_SEPARATOR.str_replace('/', DIRECTORY_SEPARATOR, $rel);
    if (!is_file($path)) {
        fwrite(STDERR, "LIVERUN_TEST_R1C1 missing file: {$rel}\n");
        exit(1);
    }
    $text = file_get_contents($path);
    foreach ($needles as $needle) {
        if (!str_contains($text, $needle)) {
            fwrite(STDERR, "LIVERUN_TEST_R1C1 missing contract: {$rel} :: {$needle}\n");
            exit(1);
        }
    }
}

echo "LIVERUN_TEST_R1C1_CONTRACT_OK\n";
