<?php
declare(strict_types=1);

namespace App\Service;

use Symfony\Contracts\HttpClient\HttpClientInterface;

final class LyricsOvhClient
{
    private const BASE_URL = 'https://api.lyrics.ovh';

    public function __construct(
        private readonly HttpClientInterface $http,
        private readonly LyricsTextNormalizer $normalizer,
    ) {
    }

    /**
     * @return list<array{artist:string,title:string,album:?string,cover:?string}>
     */
    /**
     * @return list<array{artist:string,title:string,album:?string,cover:?string,available:bool,score:int}>
     */
    public function search(
        string $query,
        int $limit = 8,
        ?string $preferredArtist = null,
        ?string $preferredTitle = null,
    ): array {
        $query = trim($query);
        if ($query === '') {
            return [];
        }

        try {
            $response = $this->http->request(
                'GET',
                self::BASE_URL.'/suggest/'.rawurlencode($query),
                [
                    'timeout' => 8.0,
                    'headers' => ['Accept' => 'application/json'],
                ],
            );

            if ($response->getStatusCode() !== 200) {
                return [];
            }

            $payload = $response->toArray(false);
        } catch (\Throwable) {
            return [];
        }

        $rows = is_array($payload['data'] ?? null) ? $payload['data'] : [];
        $candidates = [];
        $seen = [];

        foreach ($rows as $row) {
            if (!is_array($row)) {
                continue;
            }

            $artist = trim((string) ($row['artist']['name'] ?? ''));
            $title = trim((string) ($row['title'] ?? ''));

            if ($artist === '' || $title === '') {
                continue;
            }

            $key = mb_strtolower($artist."\n".$title);
            if (isset($seen[$key])) {
                continue;
            }
            $seen[$key] = true;

            $candidates[] = [
                'artist' => $artist,
                'title' => $title,
                'album' => isset($row['album']['title']) ? trim((string) $row['album']['title']) : null,
                'cover' => isset($row['album']['cover_small']) ? trim((string) $row['album']['cover_small']) : null,
                'available' => false,
                'score' => $this->relevanceScore($artist, $title, $preferredArtist, $preferredTitle),
            ];

            if (count($candidates) >= 12) {
                break;
            }
        }

        usort(
            $candidates,
            static fn (array $a, array $b): int => ($b['score'] <=> $a['score'])
                ?: strcasecmp($a['artist'].' '.$a['title'], $b['artist'].' '.$b['title']),
        );

        $candidates = array_slice($candidates, 0, max(1, min(12, $limit)));

        $checks = [];
        foreach ($candidates as $index => $candidate) {
            try {
                $checks[$index] = $this->http->request(
                    'GET',
                    self::BASE_URL.'/v1/'.
                        rawurlencode($candidate['artist']).'/'.
                        rawurlencode($candidate['title']),
                    [
                        'timeout' => 6.0,
                        'headers' => ['Accept' => 'application/json'],
                    ],
                );
            } catch (\Throwable) {
                $checks[$index] = null;
            }
        }

        foreach ($candidates as $index => &$candidate) {
            $check = $checks[$index] ?? null;
            if ($check === null) {
                continue;
            }

            try {
                if ($check->getStatusCode() !== 200) {
                    continue;
                }

                $checkPayload = $check->toArray(false);
                $lyrics = trim((string) ($checkPayload['lyrics'] ?? ''));
                $candidate['available'] = $lyrics !== '';
            } catch (\Throwable) {
                $candidate['available'] = false;
            }
        }
        unset($candidate);

        usort(
            $candidates,
            static fn (array $a, array $b): int =>
                ((int) $b['available'] <=> (int) $a['available'])
                ?: ($b['score'] <=> $a['score'])
                ?: strcasecmp($a['artist'].' '.$a['title'], $b['artist'].' '.$b['title']),
        );

        return $candidates;
    }

    private function relevanceScore(
        string $artist,
        string $title,
        ?string $preferredArtist,
        ?string $preferredTitle,
    ): int {
        $score = 0;
        $artistNeedle = $this->normaliseSearchKey($preferredArtist ?? '');
        $titleNeedle = $this->normaliseSearchKey($preferredTitle ?? '');
        $artistKey = $this->normaliseSearchKey($artist);
        $titleKey = $this->normaliseSearchKey($title);

        if ($artistNeedle !== '') {
            if ($artistKey === $artistNeedle) {
                $score += 100;
            } elseif (str_contains($artistKey, $artistNeedle) || str_contains($artistNeedle, $artistKey)) {
                $score += 60;
            } else {
                similar_text($artistKey, $artistNeedle, $pct);
                $score += (int) round($pct * 0.35);
            }
        }

        if ($titleNeedle !== '') {
            if ($titleKey === $titleNeedle) {
                $score += 100;
            } elseif (str_contains($titleKey, $titleNeedle) || str_contains($titleNeedle, $titleKey)) {
                $score += 70;
            } else {
                similar_text($titleKey, $titleNeedle, $pct);
                $score += (int) round($pct * 0.35);
            }
        }

        return $score;
    }

    private function normaliseSearchKey(string $value): string
    {
        $value = mb_strtolower(trim($value));
        $value = iconv('UTF-8', 'ASCII//TRANSLIT//IGNORE', $value) ?: $value;
        $value = preg_replace('/[^a-z0-9]+/', ' ', $value) ?? $value;
        return trim(preg_replace('/\s+/', ' ', $value) ?? $value);
    }


    /**
     * Lightweight suggestions for live autocomplete.
     * No /v1 lyrics availability checks are performed here.
     *
     * @return list<array{artist:string,title:string,album:?string,cover:?string}>
     */
    public function suggestFast(string $query, int $limit = 6): array
    {
        $query = trim($query);
        if (mb_strlen($query) < 2) {
            return [];
        }

        try {
            $response = $this->http->request(
                'GET',
                self::BASE_URL.'/suggest/'.rawurlencode($query),
                [
                    'timeout' => 4.0,
                    'headers' => ['Accept' => 'application/json'],
                ],
            );
            if ($response->getStatusCode() !== 200) {
                return [];
            }
            $payload = $response->toArray(false);
        } catch (\Throwable) {
            return [];
        }

        $rows = is_array($payload['data'] ?? null) ? $payload['data'] : [];
        $results = [];
        $seen = [];

        foreach ($rows as $row) {
            if (!is_array($row)) {
                continue;
            }
            $artist = trim((string) ($row['artist']['name'] ?? ''));
            $title = trim((string) ($row['title'] ?? ''));
            if ($artist === '' || $title === '') {
                continue;
            }
            $key = mb_strtolower($artist."\\n".$title);
            if (isset($seen[$key])) {
                continue;
            }
            $seen[$key] = true;
            $results[] = [
                'artist' => $artist,
                'title' => $title,
                'album' => isset($row['album']['title']) ? trim((string) $row['album']['title']) : null,
                'cover' => isset($row['album']['cover_small']) ? trim((string) $row['album']['cover_small']) : null,
            ];
            if (count($results) >= max(1, min(8, $limit))) {
                break;
            }
        }
        return $results;
    }

    public function fetchLyrics(string $artist, string $title): ?string
    {
        $artist = trim($artist);
        $title = trim($title);

        if ($artist === '' || $title === '') {
            return null;
        }

        try {
            $response = $this->http->request(
                'GET',
                self::BASE_URL.'/v1/'.rawurlencode($artist).'/'.rawurlencode($title),
                [
                    'timeout' => 10.0,
                    'headers' => ['Accept' => 'application/json'],
                ],
            );

            if ($response->getStatusCode() !== 200) {
                return null;
            }

            $payload = $response->toArray(false);
        } catch (\Throwable) {
            return null;
        }

        $lyrics = str_replace(["\r\n", "\r"], "\n", (string) ($payload['lyrics'] ?? ''));
        if (trim($lyrics) === '') {
            return null;
        }

        return $this->normalizer->normaliseImportedLyrics($lyrics);
    }
}
