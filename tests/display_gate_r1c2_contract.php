<?php
declare(strict_types=1);

$root = dirname(__DIR__);

$required = [
    'src/Controller/LiveRunController.php' => [
        'app_live_display_home',
        'GroupMember::class',
        "'ROLE_DISPLAY'",
        "'group' => \$group",
        "'user' => \$user",
    ],
    'src/EventSubscriber/DisplayUserGateSubscriber.php' => [
        'ROLE_DISPLAY',
        'app_live_display_home',
        'RedirectResponse',
        'Symfony\\Bundle\\SecurityBundle\\Security',
    ],
    'templates/live/display_home.html.twig' => [
        'Aucune session ouverte',
        'data-display-gate',
        'Rejoindre',
    ],
    'templates/live/display.html.twig' => [
        'Sans son',
        'Son local du rétro',
        "Chef d'orchestre pilotera les chansons",
    ],
    'public/assets/js/live/display-gate-r1c2.js' => [
        'setInterval',
        'join_url',
        'Chef d’orchestre',
    ],
];

foreach ($required as $rel => $needles) {
    $path = $root.DIRECTORY_SEPARATOR.str_replace('/', DIRECTORY_SEPARATOR, $rel);
    if (!is_file($path)) {
        fwrite(STDERR, "DISPLAY_GATE_R1C2 missing: {$rel}\n");
        exit(1);
    }
    $text = file_get_contents($path);
    foreach ($needles as $needle) {
        if (!str_contains($text, $needle)) {
            fwrite(STDERR, "DISPLAY_GATE_R1C2 missing contract: {$rel} :: {$needle}\n");
            exit(1);
        }
    }
}

echo "DISPLAY_GATE_R1C2_CONTRACT_OK\n";
