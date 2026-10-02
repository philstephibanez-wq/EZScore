<?php
declare(strict_types=1);

$root = dirname(__DIR__);
$checks = [
    'src/Domain/User/User.php' => ["'ROLE_DISPLAY'"],
    'src/Service/UserManager.php' => ["'ROLE_DISPLAY'"],
    'src/Controller/AdminUserController.php' => ["'ROLE_DISPLAY'"],
    'templates/admin/users.html.twig' => ['ROLE_DISPLAY', 'role.ROLE_DISPLAY'],
    'translations/messages.fr.yaml' => ['ROLE_DISPLAY: Passif'],
    'translations/messages.en.yaml' => ['ROLE_DISPLAY: Passive display'],
];

foreach ($checks as $rel => $needles) {
    $path = $root.DIRECTORY_SEPARATOR.str_replace('/', DIRECTORY_SEPARATOR, $rel);
    if (!is_file($path)) {
        fwrite(STDERR, "ROLE_DISPLAY_R1 missing file: {$rel}\n");
        exit(1);
    }
    $text = file_get_contents($path);
    foreach ($needles as $needle) {
        if (!str_contains($text, $needle)) {
            fwrite(STDERR, "ROLE_DISPLAY_R1 missing contract: {$rel} :: {$needle}\n");
            exit(1);
        }
    }
}
echo "ROLE_DISPLAY_R1_CONTRACT_OK\n";
