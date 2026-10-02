<?php
declare(strict_types=1);

$root = dirname(__DIR__);

function rw(string $path, callable $fn): void {
    if (!is_file($path)) {
        throw new RuntimeException("Missing file: ".$path);
    }
    $src = file_get_contents($path);
    $dst = $fn($src);
    if ($dst === $src) {
        return;
    }
    file_put_contents($path, $dst);
}

rw($root.'/src/Domain/User/User.php', function(string $s): string {
    $s = preg_replace(
        "/\\$allowed\\s*=\\s*\\['ROLE_ADMIN',\\s*'ROLE_EDITOR',\\s*'ROLE_READER'(?:,\\s*'ROLE_DISPLAY')?\\];/",
        "\$allowed = ['ROLE_ADMIN', 'ROLE_EDITOR', 'ROLE_READER', 'ROLE_DISPLAY'];",
        $s
    ) ?? $s;

    $s = preg_replace(
        "/foreach\\s*\\(\\['ROLE_ADMIN',\\s*'ROLE_EDITOR',\\s*'ROLE_READER'(?:,\\s*'ROLE_DISPLAY')?\\]\\s+as\\s+\\$role\\)/",
        "foreach (['ROLE_ADMIN', 'ROLE_EDITOR', 'ROLE_READER', 'ROLE_DISPLAY'] as \$role)",
        $s
    ) ?? $s;

    return $s;
});

rw($root.'/src/Service/UserManager.php', function(string $s): string {
    $s = preg_replace(
        "/public const ROLES\\s*=\\s*\\['ROLE_ADMIN',\\s*'ROLE_EDITOR',\\s*'ROLE_READER'(?:,\\s*'ROLE_DISPLAY')?\\];/",
        "public const ROLES = ['ROLE_ADMIN', 'ROLE_EDITOR', 'ROLE_READER', 'ROLE_DISPLAY'];",
        $s
    ) ?? $s;
    return $s;
});

rw($root.'/src/Controller/AdminUserController.php', function(string $s): string {
    $s = preg_replace(
        "/in_array\\(\\$role,\\s*\\['ROLE_READER',\\s*'ROLE_EDITOR',\\s*'ROLE_ADMIN'(?:,\\s*'ROLE_DISPLAY')?\\],\\s*true\\)/",
        "in_array(\$role, ['ROLE_READER', 'ROLE_EDITOR', 'ROLE_ADMIN', 'ROLE_DISPLAY'], true)",
        $s
    ) ?? $s;
    return $s;
});

echo "ROLE_DISPLAY_R1A_PERSIST_INSTALL_OK\n";
