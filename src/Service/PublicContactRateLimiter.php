<?php
declare(strict_types=1);

namespace App\Service;

use Symfony\Component\DependencyInjection\Attribute\Autowire;

final class PublicContactRateLimiter
{
    private string $stateFile;

    public function __construct(
        #[Autowire('%kernel.project_dir%')] string $projectDir,
    ) {
        $directory = $projectDir.'/var/security';
        if (!is_dir($directory)) {
            @mkdir($directory, 0775, true);
        }
        $this->stateFile = $directory.'/public-contact-rate.json';
    }

    public function consume(string $ip, string $email): bool
    {
        $now = time();
        $ipKey = 'ip:'.hash('sha256', mb_strtolower(trim($ip)));
        $emailKey = 'mail:'.hash('sha256', mb_strtolower(trim($email)));
        $globalKey = 'global';

        $handle = @fopen($this->stateFile, 'c+');
        if ($handle === false) {
            return false;
        }

        try {
            if (!flock($handle, LOCK_EX)) {
                return false;
            }

            rewind($handle);
            $raw = stream_get_contents($handle);
            $state = is_string($raw) && trim($raw) !== '' ? json_decode($raw, true) : [];
            if (!is_array($state)) {
                $state = [];
            }

            foreach ($state as $key => $timestamps) {
                if (!is_array($timestamps)) {
                    unset($state[$key]);
                    continue;
                }
                $state[$key] = array_values(array_filter(
                    $timestamps,
                    static fn ($ts): bool => is_int($ts) && $ts > ($now - 86400),
                ));
                if ($state[$key] === []) {
                    unset($state[$key]);
                }
            }

            $allowed =
                $this->under($state[$ipKey] ?? [], $now, 900, 3) &&
                $this->under($state[$ipKey] ?? [], $now, 86400, 10) &&
                $this->under($state[$emailKey] ?? [], $now, 900, 3) &&
                $this->under($state[$emailKey] ?? [], $now, 86400, 5) &&
                $this->under($state[$globalKey] ?? [], $now, 3600, 20) &&
                $this->under($state[$globalKey] ?? [], $now, 86400, 50);

            if (!$allowed) {
                return false;
            }

            $state[$ipKey][] = $now;
            $state[$emailKey][] = $now;
            $state[$globalKey][] = $now;

            rewind($handle);
            ftruncate($handle, 0);
            fwrite($handle, json_encode($state, JSON_THROW_ON_ERROR));
            fflush($handle);

            return true;
        } catch (\Throwable) {
            return false;
        } finally {
            flock($handle, LOCK_UN);
            fclose($handle);
        }
    }

    private function under(array $timestamps, int $now, int $windowSeconds, int $limit): bool
    {
        $count = 0;
        $threshold = $now - $windowSeconds;
        foreach ($timestamps as $timestamp) {
            if (is_int($timestamp) && $timestamp > $threshold) {
                ++$count;
            }
        }
        return $count < $limit;
    }
}
