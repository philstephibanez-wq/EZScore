<?php

declare(strict_types=1);

namespace App\Service;

use App\Domain\Song\Song;

final class SongStemPlaybackStorage
{
    public const TRACKS = [
        'original',
'lead_vocals',
        'backing_vocals',
        'drums',
        'bass',
        'guitar',
        'piano',
        'other',
    ];

    public function __construct(
        private readonly SongStemStorage $stems,
    ) {}

    public function playbackPath(Song $song, string $track): ?string
    {
        if (!in_array($track, self::TRACKS, true)) {
            return null;
        }

        $run = $this->currentRunName($song);
        if ($run === null) {
            return null;
        }

        $path = $this->stems->storageRoot($song)
            . DIRECTORY_SEPARATOR . 'playback'
            . DIRECTORY_SEPARATOR . $run
            . DIRECTORY_SEPARATOR . $track . '.opus';

        return is_file($path) && filesize($path) > 0 ? $path : null;
    }

    public function mediaRelativePath(Song $song, string $track): ?string
    {
        if (!in_array($track, self::TRACKS, true)) {
            return null;
        }

        $run = $this->currentRunName($song);
        $hash = $song->getAudioSha256();
        if ($run === null || !is_string($hash) || !preg_match('/^[a-f0-9]{64}$/', $hash)) {
            return null;
        }

        $path = sprintf(
            'song-%d/%s/playback/%s/%s.opus',
            (int) $song->getId(),
            $hash,
            $run,
            $track,
        );

        return $this->playbackPath($song, $track) !== null ? $path : null;
    }

    public function manifest(Song $song): ?array
    {
        $run = $this->currentRunName($song);
        if ($run === null) {
            return null;
        }

        $path = $this->stems->storageRoot($song)
            . DIRECTORY_SEPARATOR . 'playback'
            . DIRECTORY_SEPARATOR . $run
            . DIRECTORY_SEPARATOR . 'manifest.json';

        if (!is_file($path)) {
            return null;
        }

        $payload = json_decode((string) file_get_contents($path), true);

        return is_array($payload) ? $payload : null;
    }

    public function isReady(Song $song): bool
    {
        foreach (self::TRACKS as $track) {
            if ($this->playbackPath($song, $track) === null) {
                return false;
            }
        }

        $manifest = $this->manifest($song);

        return is_array($manifest)
            && ($manifest['codec'] ?? null) === 'opus'
            && ($manifest['source_run'] ?? null) === $this->currentRunName($song);
    }

    private function currentRunName(Song $song): ?string
    {
        $pointer = $this->stems->storageRoot($song)
            . DIRECTORY_SEPARATOR . 'current.json';

        if (!is_file($pointer)) {
            return null;
        }

        $payload = json_decode((string) file_get_contents($pointer), true);
        $run = is_array($payload) ? trim((string) ($payload['run'] ?? '')) : '';

        return preg_match('/^run-[A-Za-z0-9]+$/', $run) ? $run : null;
    }
}
