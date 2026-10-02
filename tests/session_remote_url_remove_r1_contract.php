<?php
declare(strict_types=1);

$root = dirname(__DIR__);

$mustNotContain = [
    'src/Domain/Event/Event.php' => ['remoteUrl', 'remote_url'],
    'src/Controller/EventController.php' => ['remoteUrl', 'remote_url'],
    'templates/events/index.html.twig' => ['remote_url', 'Lien distant'],
    'templates/events/show.html.twig' => ['remoteUrl', 'remote_url', 'Lien distant'],
    'translations/event.fr.yaml' => ['remote_url:'],
    'translations/event.en.yaml' => ['remote_url:'],
];

foreach ($mustNotContain as $rel => $needles) {
    $path = $root.DIRECTORY_SEPARATOR.str_replace('/', DIRECTORY_SEPARATOR, $rel);
    if (!is_file($path)) {
        fwrite(STDERR, "MISSING_FILE {$rel}\n");
        exit(1);
    }
    $text = file_get_contents($path);
    foreach ($needles as $needle) {
        if (str_contains($text, $needle)) {
            fwrite(STDERR, "REMOTE_URL_REMAINS {$rel} :: {$needle}\n");
            exit(1);
        }
    }
}

$migration = file_get_contents($root.'/migrations/Version20261002183000.php');
if (!str_contains($migration, 'DROP COLUMN remote_url')) {
    fwrite(STDERR, "MIGRATION_DOES_NOT_DROP_REMOTE_URL\n");
    exit(1);
}

echo "SESSION_REMOTE_URL_REMOVE_R1_CONTRACT_OK\n";
