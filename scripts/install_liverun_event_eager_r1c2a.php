<?php
declare(strict_types=1);

$root = dirname(__DIR__);
$path = $root.'/src/Domain/Event/LiveRun.php';

if (!is_file($path)) {
    throw new RuntimeException('Missing LiveRun.php');
}

$src = file_get_contents($path);

$from = "#[ORM\\ManyToOne(targetEntity: Event::class)]";
$to   = "#[ORM\\ManyToOne(targetEntity: Event::class, fetch: 'EAGER')]";

if (!str_contains($src, $to)) {
    if (!str_contains($src, $from)) {
        throw new RuntimeException('LiveRun Event relation anchor not found');
    }
    $src = str_replace($from, $to, $src);
    file_put_contents($path, $src);
}

echo "LIVERUN_EVENT_EAGER_R1C2A_INSTALL_OK\n";
