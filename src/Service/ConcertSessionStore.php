<?php

declare(strict_types=1);

namespace App\Service;

use App\Domain\User\User;
use Symfony\Component\HttpKernel\KernelInterface;

final class ConcertSessionStore
{
    private const TTL_SECONDS = 14400;
    private const MAX_PARTICIPANTS = 64;
    private readonly string $directory;

    public function __construct(KernelInterface $kernel)
    {
        $this->directory = $kernel->getProjectDir() . '/var/concert_sessions';
    }

    public function create(User $master): array
    {
        $this->ensureDirectory();
        $this->purgeExpired();
        $sessionId = bin2hex(random_bytes(16));
        $masterKey = bin2hex(random_bytes(24));
        $inviteToken = bin2hex(random_bytes(16));
        $now = $this->nowMs();
        $session = [
            'id' => $sessionId,
            'master_user_id' => (int) $master->getId(),
            'master_name' => $master->getDisplayName(),
            'master_key_hash' => hash('sha256', $masterKey),
            'invite_hash' => hash('sha256', $inviteToken),
            'created_at_ms' => $now,
            'expires_at_ms' => $now + self::TTL_SECONDS * 1000,
            'revision' => 1,
            'state' => [
                'song_id' => null,
                'song_title' => '',
                'playing' => false,
                'position_ms' => 0,
                'tempo' => 1.0,
                'updated_at_ms' => $now,
            ],
            'participants' => [
                'master' => [
                    'client_id' => 'master',
                    'user_id' => (int) $master->getId(),
                    'role' => 'master',
                    'name' => $master->getDisplayName(),
                    'device_type' => 'browser',
                    'capabilities' => ['transport' => true],
                    'connected_at_ms' => $now,
                    'last_seen_ms' => $now,
                    'client_key_hash' => null,
                ],
            ],
        ];
        $this->writeNew($sessionId, $session);
        return ['session' => $this->publicSession($session), 'master_key' => $masterKey, 'invite_token' => $inviteToken];
    }

    public function canJoin(string $sessionId, string $inviteToken): bool
    {
        $session = $this->load($sessionId);
        if ($session === null || $inviteToken === '') return false;
        return hash_equals((string) ($session['invite_hash'] ?? ''), hash('sha256', $inviteToken));
    }

    public function join(string $sessionId, string $inviteToken, string $name, string $deviceType = 'browser'): array
    {
        $clientId = bin2hex(random_bytes(8));
        $clientKey = bin2hex(random_bytes(24));
        $now = $this->nowMs();
        $session = $this->mutate($sessionId, function (array $session) use ($inviteToken, $name, $deviceType, $clientId, $clientKey, $now): array {
            if (!hash_equals((string) ($session['invite_hash'] ?? ''), hash('sha256', $inviteToken))) throw new \RuntimeException('INVALID_INVITE');
            if (count($session['participants'] ?? []) >= self::MAX_PARTICIPANTS) throw new \RuntimeException('SESSION_FULL');
            $session['participants'][$clientId] = [
                'client_id' => $clientId,
                'user_id' => null,
                'role' => 'follower_local',
                'name' => $this->cleanLabel($name, 'Follower'),
                'device_type' => $this->cleanLabel($deviceType, 'browser'),
                'capabilities' => ['transport' => false],
                'connected_at_ms' => $now,
                'last_seen_ms' => $now,
                'client_key_hash' => hash('sha256', $clientKey),
            ];
            $session['expires_at_ms'] = $now + self::TTL_SECONDS * 1000;
            $session['revision'] = ((int) ($session['revision'] ?? 0)) + 1;
            return $session;
        });
        return ['session' => $this->publicSession($session), 'client_id' => $clientId, 'client_key' => $clientKey];
    }

    public function updateState(string $sessionId, int $masterUserId, string $masterKey, array $patch): array
    {
        $now = $this->nowMs();
        $session = $this->mutate($sessionId, function (array $session) use ($masterUserId, $masterKey, $patch, $now): array {
            if ((int) ($session['master_user_id'] ?? 0) !== $masterUserId) throw new \RuntimeException('NOT_MASTER');
            if (!hash_equals((string) ($session['master_key_hash'] ?? ''), hash('sha256', $masterKey))) throw new \RuntimeException('INVALID_MASTER_KEY');
            $state = $session['state'] ?? [];
            if (array_key_exists('song_id', $patch)) { $value = $patch['song_id']; $state['song_id'] = $value === null || $value === '' ? null : max(1, (int) $value); }
            if (array_key_exists('song_title', $patch)) $state['song_title'] = $this->cleanLabel((string) $patch['song_title'], '');
            if (array_key_exists('playing', $patch)) $state['playing'] = (bool) $patch['playing'];
            if (array_key_exists('position_ms', $patch)) $state['position_ms'] = max(0, min(86_400_000, (int) $patch['position_ms']));
            if (array_key_exists('tempo', $patch)) $state['tempo'] = max(0.25, min(2.0, (float) $patch['tempo']));
            $state['updated_at_ms'] = $now;
            $session['state'] = $state;
            $session['expires_at_ms'] = $now + self::TTL_SECONDS * 1000;
            $session['revision'] = ((int) ($session['revision'] ?? 0)) + 1;
            if (isset($session['participants']['master'])) $session['participants']['master']['last_seen_ms'] = $now;
            return $session;
        });
        return $this->publicSession($session);
    }

    public function stateForClient(string $sessionId, string $clientId, string $clientKey): array
    {
        $session = $this->load($sessionId);
        if ($session === null) throw new \RuntimeException('SESSION_NOT_FOUND');
        $this->assertClient($session, $clientId, $clientKey);
        return $this->publicSession($session);
    }

    public function heartbeat(string $sessionId, string $clientId, string $clientKey): array
    {
        $now = $this->nowMs();
        $session = $this->mutate($sessionId, function (array $session) use ($clientId, $clientKey, $now): array {
            $this->assertClient($session, $clientId, $clientKey);
            $session['participants'][$clientId]['last_seen_ms'] = $now;
            $session['expires_at_ms'] = $now + self::TTL_SECONDS * 1000;
            return $session;
        });
        return $this->publicSession($session);
    }

    public function publicStateForMaster(string $sessionId, int $masterUserId, string $masterKey): ?array
    {
        $session = $this->load($sessionId);
        if ($session === null) return null;
        if ((int) ($session['master_user_id'] ?? 0) !== $masterUserId) throw new \RuntimeException('NOT_MASTER');
        if (!hash_equals((string) ($session['master_key_hash'] ?? ''), hash('sha256', $masterKey))) throw new \RuntimeException('INVALID_MASTER_KEY');
        return $this->publicSession($session);
    }

    private function assertClient(array $session, string $clientId, string $clientKey): void
    {
        $participant = $session['participants'][$clientId] ?? null;
        if (!is_array($participant) || !is_string($participant['client_key_hash'] ?? null)) throw new \RuntimeException('INVALID_CLIENT');
        if (!hash_equals((string) $participant['client_key_hash'], hash('sha256', $clientKey))) throw new \RuntimeException('INVALID_CLIENT_KEY');
    }

    private function publicSession(array $session): array
    {
        $participants = [];
        foreach (($session['participants'] ?? []) as $participant) {
            if (!is_array($participant)) continue;
            $participants[] = [
                'client_id' => (string) ($participant['client_id'] ?? ''),
                'role' => (string) ($participant['role'] ?? ''),
                'name' => (string) ($participant['name'] ?? ''),
                'device_type' => (string) ($participant['device_type'] ?? ''),
                'capabilities' => $participant['capabilities'] ?? [],
                'connected_at_ms' => (float) ($participant['connected_at_ms'] ?? 0),
                'last_seen_ms' => (float) ($participant['last_seen_ms'] ?? 0),
            ];
        }
        return [
            'id' => (string) $session['id'],
            'master_name' => (string) ($session['master_name'] ?? ''),
            'revision' => (int) ($session['revision'] ?? 0),
            'expires_at_ms' => (float) ($session['expires_at_ms'] ?? 0),
            'server_now_ms' => $this->nowMs(),
            'state' => [
                'song_id' => $session['state']['song_id'] ?? null,
                'song_title' => (string) ($session['state']['song_title'] ?? ''),
                'playing' => (bool) ($session['state']['playing'] ?? false),
                'position_ms' => (int) ($session['state']['position_ms'] ?? 0),
                'tempo' => (float) ($session['state']['tempo'] ?? 1.0),
                'updated_at_ms' => (float) ($session['state']['updated_at_ms'] ?? 0),
            ],
            'participants' => $participants,
        ];
    }

    private function ensureDirectory(): void
    {
        if (!is_dir($this->directory) && !@mkdir($this->directory, 0775, true) && !is_dir($this->directory)) throw new \RuntimeException('Unable to create concert session directory.');
    }

    private function purgeExpired(): void
    {
        if (!is_dir($this->directory)) return;
        $now = $this->nowMs();
        foreach (glob($this->directory . '/*.json') ?: [] as $file) {
            $raw = @file_get_contents($file);
            if ($raw === false) continue;
            $session = json_decode($raw, true);
            if (is_array($session) && (float) ($session['expires_at_ms'] ?? 0) < $now) @unlink($file);
        }
    }

    private function load(string $sessionId): ?array
    {
        if (!$this->validSessionId($sessionId)) return null;
        $this->ensureDirectory();
        $path = $this->path($sessionId);
        if (!is_file($path)) return null;
        $handle = fopen($path, 'rb');
        if ($handle === false) return null;
        try {
            if (!flock($handle, LOCK_SH)) return null;
            $raw = stream_get_contents($handle);
            flock($handle, LOCK_UN);
        } finally { fclose($handle); }
        $session = json_decode((string) $raw, true);
        if (!is_array($session)) return null;
        if ((float) ($session['expires_at_ms'] ?? 0) < $this->nowMs()) { @unlink($path); return null; }
        return $session;
    }

    private function mutate(string $sessionId, callable $mutator): array
    {
        if (!$this->validSessionId($sessionId)) throw new \RuntimeException('SESSION_NOT_FOUND');
        $this->ensureDirectory();
        $path = $this->path($sessionId);
        $handle = @fopen($path, 'c+');
        if ($handle === false) throw new \RuntimeException('SESSION_NOT_FOUND');
        try {
            if (!flock($handle, LOCK_EX)) throw new \RuntimeException('SESSION_LOCK_FAILED');
            rewind($handle);
            $raw = stream_get_contents($handle);
            $session = json_decode((string) $raw, true);
            if (!is_array($session) || (float) ($session['expires_at_ms'] ?? 0) < $this->nowMs()) throw new \RuntimeException('SESSION_NOT_FOUND');
            $session = $mutator($session);
            rewind($handle);
            ftruncate($handle, 0);
            fwrite($handle, json_encode($session, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR));
            fflush($handle);
            flock($handle, LOCK_UN);
            return $session;
        } finally { fclose($handle); }
    }

    private function writeNew(string $sessionId, array $session): void
    {
        $handle = fopen($this->path($sessionId), 'x+b');
        if ($handle === false) throw new \RuntimeException('Unable to create concert session.');
        try {
            if (!flock($handle, LOCK_EX)) throw new \RuntimeException('SESSION_LOCK_FAILED');
            fwrite($handle, json_encode($session, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR));
            fflush($handle);
            flock($handle, LOCK_UN);
        } finally { fclose($handle); }
    }

    private function path(string $sessionId): string { return $this->directory . '/' . $sessionId . '.json'; }
    private function validSessionId(string $sessionId): bool { return (bool) preg_match('/^[a-f0-9]{32}$/', $sessionId); }
    private function cleanLabel(string $value, string $fallback): string
    {
        $value = trim(preg_replace('/\s+/u', ' ', $value) ?? '');
        return $value === '' ? $fallback : mb_substr($value, 0, 120);
    }
    private function nowMs(): float { return floor(microtime(true) * 1000); }
}
