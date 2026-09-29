#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else r"H:\EZScore_v1").resolve()
NORMALIZER = ROOT / "src/Service/LyricsTextNormalizer.php"

TARGETED_METHOD = r'''    private function applyLyricsOvhTargetedRepairs(string $text): string
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

'''

def main() -> int:
    if not NORMALIZER.is_file():
        raise RuntimeError(f"Missing prerequisite: {NORMALIZER}")

    text = NORMALIZER.read_text(encoding="utf-8")

    if "private function applyLyricsOvhTargetedRepairs" not in text:
        anchor = '''    public function normaliseImportedLyrics(string $text): string
    {
        $text = str_replace(["\\r\\n", "\\r"], "\\n", $text);
'''
        replacement = '''    public function normaliseImportedLyrics(string $text): string
    {
        $text = str_replace(["\\r\\n", "\\r"], "\\n", $text);

        // Lyrics.ovh can return already-damaged text where the original byte
        // sequence can no longer be reconstructed generically.
        $text = $this->applyLyricsOvhTargetedRepairs($text);
'''
        if anchor not in text:
            raise RuntimeError("LyricsTextNormalizer normaliseImportedLyrics anchor not found")
        text = text.replace(anchor, replacement, 1)

        method_anchor = '''    private function repairLine(string $line): string
    {
'''
        if method_anchor not in text:
            raise RuntimeError("LyricsTextNormalizer repairLine anchor not found")
        text = text.replace(method_anchor, TARGETED_METHOD + method_anchor, 1)

    NORMALIZER.write_text(text, encoding="utf-8", newline="\n")
    print("R38_16E_LYRICS_TARGETED_MOJIBAKE_INSTALL_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
