<?php

declare(strict_types=1);

use App\Service\AnalysisCapabilityState;

require dirname(__DIR__).'/vendor/autoload.php';

function fail_contract(string $message): never {
    fwrite(STDERR, $message.PHP_EOL);
    exit(1);
}

$root = sys_get_temp_dir().DIRECTORY_SEPARATOR.'ezscore-capability-'.bin2hex(random_bytes(6));
$dir = $root.DIRECTORY_SEPARATOR.'var'.DIRECTORY_SEPARATOR.'runtime'.DIRECTORY_SEPARATOR.'orchestrator';
if (!mkdir($dir, 0777, true) && !is_dir($dir)) {
    fail_contract('cannot create temp capability directory');
}
$path = $dir.DIRECTORY_SEPARATOR.'analysis-capability.json';

$old = getenv('EZSCORE_INSTANCE');
putenv('EZSCORE_INSTANCE=dev');
$_SERVER['EZSCORE_INSTANCE'] = 'dev';
$_ENV['EZSCORE_INSTANCE'] = 'dev';

try {
    $state = new AnalysisCapabilityState($root);

    $missing = $state->publicStatus();
    if (($missing['available'] ?? null) !== false || ($missing['reason'] ?? '') !== 'capability_missing') {
        fail_contract('missing capability must be unavailable');
    }

    file_put_contents($path, json_encode([
        'schema' => AnalysisCapabilityState::SCHEMA_VERSION,
        'target' => 'dev',
        'available' => true,
        'state' => 'idle',
        'service_scope' => 'all',
        'queued' => 0,
        'active_target' => null,
        'at' => (new DateTimeImmutable())->format(DATE_ATOM),
    ], JSON_PRETTY_PRINT));

    $online = $state->publicStatus();
    if (($online['available'] ?? null) !== true || ($online['online'] ?? null) !== true) {
        fail_contract('fresh DEV capability must be available');
    }

    file_put_contents($path, json_encode([
        'schema' => AnalysisCapabilityState::SCHEMA_VERSION,
        'target' => 'prod',
        'available' => true,
        'state' => 'idle',
        'service_scope' => 'all',
        'at' => (new DateTimeImmutable())->format(DATE_ATOM),
    ]));

    $cross = $state->publicStatus();
    if (($cross['available'] ?? null) !== false || ($cross['reason'] ?? '') !== 'capability_target_mismatch') {
        fail_contract('DEV must reject a PROD capability snapshot');
    }

    file_put_contents($path, json_encode([
        'schema' => AnalysisCapabilityState::SCHEMA_VERSION,
        'target' => 'dev',
        'available' => true,
        'state' => 'idle',
        'service_scope' => 'all',
        'at' => (new DateTimeImmutable('-30 seconds'))->format(DATE_ATOM),
    ]));

    $stale = $state->publicStatus();
    if (($stale['available'] ?? null) !== false || ($stale['reason'] ?? '') !== 'capability_stale') {
        fail_contract('stale capability must be unavailable');
    }
} finally {
    if ($old === false) {
        putenv('EZSCORE_INSTANCE');
        unset($_SERVER['EZSCORE_INSTANCE'], $_ENV['EZSCORE_INSTANCE']);
    } else {
        putenv('EZSCORE_INSTANCE='.$old);
        $_SERVER['EZSCORE_INSTANCE'] = $old;
        $_ENV['EZSCORE_INSTANCE'] = $old;
    }
    @unlink($path);
    @rmdir($dir);
    @rmdir(dirname($dir));
    @rmdir(dirname(dirname($dir)));
    @rmdir($root);
}

echo "EZSCORE_ANALYSIS_CAPABILITY_CONTRACT_OK".PHP_EOL;
