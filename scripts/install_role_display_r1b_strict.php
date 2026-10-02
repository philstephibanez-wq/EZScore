<?php
declare(strict_types=1);

$root = dirname(__DIR__);

function replaceExact(string $path, string $from, string $to): void {
    if (!is_file($path)) {
        throw new RuntimeException("Missing file: ".$path);
    }
    $src = file_get_contents($path);
    if (str_contains($src, $to)) {
        return;
    }
    if (!str_contains($src, $from)) {
        throw new RuntimeException("Expected source pattern not found in ".$path);
    }
    file_put_contents($path, str_replace($from, $to, $src));
}

replaceExact(
    $root.'/src/Domain/User/User.php',
    <<<'OLD'
        $allowed = ['ROLE_ADMIN', 'ROLE_EDITOR', 'ROLE_READER'];
OLD,
    <<<'NEW'
        $allowed = ['ROLE_ADMIN', 'ROLE_EDITOR', 'ROLE_READER', 'ROLE_DISPLAY'];
NEW
);

replaceExact(
    $root.'/src/Domain/User/User.php',
    <<<'OLD'
        foreach (['ROLE_ADMIN', 'ROLE_EDITOR', 'ROLE_READER'] as $role) {
OLD,
    <<<'NEW'
        foreach (['ROLE_ADMIN', 'ROLE_EDITOR', 'ROLE_READER', 'ROLE_DISPLAY'] as $role) {
NEW
);

replaceExact(
    $root.'/src/Service/UserManager.php',
    <<<'OLD'
    public const ROLES = ['ROLE_ADMIN', 'ROLE_EDITOR', 'ROLE_READER'];
OLD,
    <<<'NEW'
    public const ROLES = ['ROLE_ADMIN', 'ROLE_EDITOR', 'ROLE_READER', 'ROLE_DISPLAY'];
NEW
);

replaceExact(
    $root.'/src/Controller/AdminUserController.php',
    <<<'OLD'
        if (in_array($role, ['ROLE_READER', 'ROLE_EDITOR', 'ROLE_ADMIN'], true)) {
OLD,
    <<<'NEW'
        if (in_array($role, ['ROLE_READER', 'ROLE_EDITOR', 'ROLE_ADMIN', 'ROLE_DISPLAY'], true)) {
NEW
);

echo "ROLE_DISPLAY_R1B_STRICT_INSTALL_OK\n";
