<?php
declare(strict_types=1);

$root = $argv[1] ?? 'H:\\EZScore_v1';
$client = $root.'/src/Service/LyricsOvhClient.php';

if (!is_file($client)) {
    fwrite(STDERR, "Missing LyricsOvhClient.php\n");
    exit(1);
}

$source = file_get_contents($client);

if (strpos($source, 'catch (\\\\Throwable)') !== false) {
    fwrite(STDERR, "Double-escaped Throwable still present\n");
    exit(1);
}

if (strpos($source, 'catch (\\Throwable)') === false) {
    fwrite(STDERR, "Valid Throwable catch not found\n");
    exit(1);
}

echo "R38_16I2_THROWABLE_ESCAPE_REPAIR_CONTRACT_OK\n";
