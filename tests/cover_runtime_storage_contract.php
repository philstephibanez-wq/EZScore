<?php
$path = dirname(__DIR__) . '/src/Service/SongImportStorage.php';
$source = file_get_contents($path);
if (!is_string($source)) { fwrite(STDERR, "Cannot read SongImportStorage.php\n"); exit(1); }

$required = [
    "DIRECTORY_SEPARATOR . 'var'",
    "DIRECTORY_SEPARATOR . 'storage'",
    "DIRECTORY_SEPARATOR . 'covers'",
    "return '/uploads/covers/' . \$storedName;",
];

foreach ($required as $needle) {
    if (!str_contains($source, $needle)) {
        fwrite(STDERR, "Missing cover runtime contract: {$needle}\n");
        exit(1);
    }
}

if (str_contains($source, "DIRECTORY_SEPARATOR . 'public'\n            . DIRECTORY_SEPARATOR . 'uploads'\n            . DIRECTORY_SEPARATOR . 'covers'")) {
    fwrite(STDERR, "Legacy public/uploads/covers write path still active\n");
    exit(1);
}

echo "EZSCORE_COVER_RUNTIME_STORAGE_OK\n";
