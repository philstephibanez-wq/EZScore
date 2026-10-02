<?php
declare(strict_types=1);

$root = dirname(__DIR__);
$path = $root.'/src/Domain/Event/LiveRun.php';

if (!is_file($path)) {
    fwrite(STDERR, "LIVERUN_EVENT_EAGER_R1C2A missing LiveRun.php\n");
    exit(1);
}

$src = file_get_contents($path);

if (!str_contains($src, "#[ORM\\ManyToOne(targetEntity: Event::class, fetch: 'EAGER')]")) {
    fwrite(STDERR, "LIVERUN_EVENT_EAGER_R1C2A eager relation missing\n");
    exit(1);
}

if (str_contains($src, "#[ORM\\ManyToOne(targetEntity: Event::class)]")) {
    fwrite(STDERR, "LIVERUN_EVENT_EAGER_R1C2A old lazy relation still present\n");
    exit(1);
}

echo "LIVERUN_EVENT_EAGER_R1C2A_CONTRACT_OK\n";
