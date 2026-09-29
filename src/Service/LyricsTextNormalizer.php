<?php
declare(strict_types=1);

namespace App\Service;

final class LyricsTextNormalizer
{
    /**
     * Conservative repair for mojibake commonly found in third-party lyrics.
     *
     * The source may contain UTF-8 bytes that were previously decoded as
     * Windows-1252 / ISO-8859-1 / MacRoman. We only accept a repaired candidate
     * when its mojibake score is strictly better than the original line.
     */
    public function normaliseImportedLyrics(string $text): string
    {
        $text = str_replace(["\r\n", "\r"], "\n", $text);

        // Lyrics.ovh can return already-damaged text where the original byte
        // sequence can no longer be reconstructed generically.
        $text = $this->applyLyricsOvhTargetedRepairs($text);
        $lines = explode("\n", $text);

        foreach ($lines as $index => $line) {
            $lines[$index] = $this->repairLine($line);
        }

        $text = implode("\n", $lines);

        // Harmless typography cleanup after encoding repair.
        $text = str_replace(
            ["\u{00A0}", "\u{202F}", "\u{FEFF}"],
            [' ', ' ', ''],
            $text,
        );

        return trim($text);
    }

    private function applyLyricsOvhTargetedRepairs(string $text): string
    {
        return strtr($text, [
            // Real Lyrics.ovh samples observed on Christophe - Aline.
            'prâ¨s' => 'près',
            'prâˆšs' => 'près',
            'pr√®s' => 'près',
            'âgme' => 'âme',
            'âˆšme' => 'âme',

            // Same corruption family, kept deliberately narrow.
            'â©' => 'é',
            'â¨' => 'è',
            'âª' => 'ê',
            'â§' => 'ç',
            'â´' => 'ô',
            'â¹' => 'ù',
        ]);
    }

    private function repairLine(string $line): string
    {
        if ($line === '' || !$this->looksSuspicious($line)) {
            return $line;
        }

        $candidates = [$line];

        foreach (['Windows-1252', 'ISO-8859-1', 'Macintosh'] as $legacyEncoding) {
            $candidate = $this->reverseLegacyDecode($line, $legacyEncoding);
            if ($candidate !== null && $candidate !== $line) {
                $candidates[] = $candidate;
            }
        }

        $best = $line;
        $bestScore = $this->mojibakeScore($line);

        foreach ($candidates as $candidate) {
            $score = $this->mojibakeScore($candidate);
            if ($score < $bestScore) {
                $best = $candidate;
                $bestScore = $score;
            }
        }

        return $best;
    }

    private function reverseLegacyDecode(string $text, string $legacyEncoding): ?string
    {
        if (!function_exists('mb_convert_encoding') || !mb_check_encoding($text, 'UTF-8')) {
            return null;
        }

        try {
            // Re-create the original byte sequence, then interpret it as UTF-8.
            $bytes = mb_convert_encoding($text, $legacyEncoding, 'UTF-8');
            if (!mb_check_encoding($bytes, 'UTF-8')) {
                return null;
            }

            $candidate = mb_convert_encoding($bytes, 'UTF-8', 'UTF-8');
            return $candidate === '' ? null : $candidate;
        } catch (\Throwable) {
            return null;
        }
    }

    private function looksSuspicious(string $text): bool
    {
        foreach ([
            'Ã', 'Â', 'â€', 'â€™', 'â€œ', 'â€', 'â€“', 'â€”', 'âˆ',
            '√', '�', '¬', '¢', '®',
        ] as $marker) {
            if (str_contains($text, $marker)) {
                return true;
            }
        }

        return false;
    }

    private function mojibakeScore(string $text): int
    {
        $score = 0;

        $weights = [
            '�' => 20,
            'Ã' => 8,
            'Â' => 8,
            'â€' => 8,
            'â€™' => 8,
            'â€œ' => 8,
            'â€' => 8,
            'â€“' => 8,
            'â€”' => 8,
            'âˆ' => 8,
            '√' => 6,
            '¬' => 4,
            '¢' => 3,
            '®' => 3,
        ];

        foreach ($weights as $marker => $weight) {
            $score += substr_count($text, $marker) * $weight;
        }

        return $score;
    }
}
