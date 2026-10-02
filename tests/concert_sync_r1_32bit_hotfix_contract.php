<?php

declare(strict_types=1);

require dirname(__DIR__) . '/vendor/autoload.php';

use App\Domain\User\User;
use App\Kernel;
use App\Service\ConcertSessionStore;

$kernel = new Kernel('dev', true);
$user = (new User())->setDisplayName('Concert 32-bit test');
$store = new ConcertSessionStore($kernel);
$result = $store->create($user);
$session = $result['session'] ?? null;
if (!is_array($session)) { fwrite(STDERR, "FAILED: session missing\n"); exit(1); }
foreach ([
    'server_now_ms' => $session['server_now_ms'] ?? null,
    'expires_at_ms' => $session['expires_at_ms'] ?? null,
    'updated_at_ms' => $session['state']['updated_at_ms'] ?? null,
] as $name => $value) {
    if (!is_float($value) || $value < 1000000000000) { fwrite(STDERR, "FAILED: {$name} invalid\n"); exit(1); }
}
$id = (string) ($session['id'] ?? '');
if (preg_match('/^[a-f0-9]{32}$/', $id)) @unlink(dirname(__DIR__) . '/var/concert_sessions/' . $id . '.json');
echo "CONCERT_SYNC_R1_32BIT_HOTFIX_OK\n";
