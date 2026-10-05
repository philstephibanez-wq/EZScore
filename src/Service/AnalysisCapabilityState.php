<?php

declare(strict_types=1);

namespace App\Service;

use Symfony\Component\DependencyInjection\Attribute\Autowire;

final class AnalysisCapabilityState
{
    public const SCHEMA_VERSION = 'ezs.analysis-capability.v1';
    public const FRESH_AFTER_SECONDS = 10;

    public function __construct(
        #[Autowire('%kernel.project_dir%')]
        private readonly string $projectDir,
    ) {
    }

    public function isAvailable(): bool
    {
        return ($this->publicStatus()['available'] ?? false) === true;
    }

    /**
     * @return array{
     *   online:bool,
     *   available:bool,
     *   status:string,
     *   target:?string,
     *   service_scope:?string,
     *   queued:?int,
     *   active_target:?string,
     *   last_seen_at:?string,
     *   last_seen_age_seconds:?int,
     *   reason:?string
     * }
     */
    public function publicStatus(): array
    {
        $payload = $this->readPayload();
        if ($payload === null) {
            return $this->offline('capability_missing');
        }

        if (($payload['schema'] ?? null) !== self::SCHEMA_VERSION) {
            return $this->offline('capability_schema_mismatch', $payload);
        }

        $target = trim((string) ($payload['target'] ?? ''));
        $expected = $this->expectedTarget();
        if ($expected !== null && $target !== $expected) {
            return $this->offline('capability_target_mismatch', $payload);
        }

        $at = trim((string) ($payload['at'] ?? ''));
        $age = $this->ageSeconds($at);
        if ($age === null || $age > self::FRESH_AFTER_SECONDS) {
            return $this->offline('capability_stale', $payload, $age);
        }

        $available = ($payload['available'] ?? false) === true;

        return [
            // `online` remains as a compatibility alias for the existing JS.
            'online' => $available,
            'available' => $available,
            'status' => trim((string) ($payload['state'] ?? ($available ? 'available' : 'unavailable'))),
            'target' => $target !== '' ? $target : null,
            'service_scope' => isset($payload['service_scope']) ? (string) $payload['service_scope'] : null,
            'queued' => isset($payload['queued']) && is_numeric($payload['queued']) ? (int) $payload['queued'] : null,
            'active_target' => isset($payload['active_target']) && $payload['active_target'] !== null
                ? (string) $payload['active_target']
                : null,
            'last_seen_at' => $at !== '' ? $at : null,
            'last_seen_age_seconds' => $age,
            'reason' => $available ? null : (isset($payload['error']) && $payload['error'] !== null ? (string) $payload['error'] : 'orchestrator_unavailable'),
        ];
    }

    private function expectedTarget(): ?string
    {
        $instance = strtolower(trim((string) (
            $_SERVER['EZSCORE_INSTANCE']
            ?? $_ENV['EZSCORE_INSTANCE']
            ?? getenv('EZSCORE_INSTANCE')
            ?: ''
        )));

        return match ($instance) {
            'dev' => 'dev',
            'prod', 'online' => 'prod',
            default => null,
        };
    }

    private function path(): string
    {
        return $this->projectDir
            .DIRECTORY_SEPARATOR.'var'
            .DIRECTORY_SEPARATOR.'runtime'
            .DIRECTORY_SEPARATOR.'orchestrator'
            .DIRECTORY_SEPARATOR.'analysis-capability.json';
    }

    /**
     * @return array<string,mixed>|null
     */
    private function readPayload(): ?array
    {
        $path = $this->path();
        if (!is_file($path)) {
            return null;
        }

        $decoded = json_decode((string) file_get_contents($path), true);

        return is_array($decoded) ? $decoded : null;
    }

    private function ageSeconds(string $at): ?int
    {
        if ($at === '') {
            return null;
        }

        try {
            $instant = new \DateTimeImmutable($at);
        } catch (\Throwable) {
            return null;
        }

        $age = time() - $instant->getTimestamp();

        return $age >= 0 ? $age : null;
    }

    /**
     * @param array<string,mixed>|null $payload
     * @return array<string,mixed>
     */
    private function offline(
        string $reason,
        ?array $payload = null,
        ?int $age = null,
    ): array {
        return [
            'online' => false,
            'available' => false,
            'status' => 'unavailable',
            'target' => isset($payload['target']) ? (string) $payload['target'] : null,
            'service_scope' => isset($payload['service_scope']) ? (string) $payload['service_scope'] : null,
            'queued' => isset($payload['queued']) && is_numeric($payload['queued']) ? (int) $payload['queued'] : null,
            'active_target' => isset($payload['active_target']) && $payload['active_target'] !== null
                ? (string) $payload['active_target']
                : null,
            'last_seen_at' => isset($payload['at']) ? (string) $payload['at'] : null,
            'last_seen_age_seconds' => $age,
            'reason' => $reason,
        ];
    }
}
