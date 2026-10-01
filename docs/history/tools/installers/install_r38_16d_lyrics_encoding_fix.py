#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else r"H:\EZScore_v1").resolve()
CLIENT = ROOT / "src/Service/LyricsOvhClient.php"
NORMALIZER = ROOT / "src/Service/LyricsTextNormalizer.php"

def main() -> int:
    if not CLIENT.is_file():
        raise RuntimeError(f"Missing prerequisite: {CLIENT}")
    if not NORMALIZER.is_file():
        raise RuntimeError(f"Missing payload: {NORMALIZER}")

    text = CLIENT.read_text(encoding="utf-8")

    old_ctor = """    public function __construct(private readonly HttpClientInterface $http)
    {
    }
"""
    new_ctor = """    public function __construct(
        private readonly HttpClientInterface $http,
        private readonly LyricsTextNormalizer $normalizer,
    ) {
    }
"""

    if "private readonly LyricsTextNormalizer $normalizer" not in text:
        if old_ctor not in text:
            raise RuntimeError("LyricsOvhClient constructor anchor not found")
        text = text.replace(old_ctor, new_ctor, 1)

    old_return = """        $lyrics = str_replace(["\\r\\n", "\\r"], "\\n", (string) ($payload['lyrics'] ?? ''));
        return trim($lyrics) === '' ? null : $lyrics;
"""
    new_return = """        $lyrics = str_replace(["\\r\\n", "\\r"], "\\n", (string) ($payload['lyrics'] ?? ''));
        if (trim($lyrics) === '') {
            return null;
        }

        return $this->normalizer->normaliseImportedLyrics($lyrics);
"""

    if "normaliseImportedLyrics($lyrics)" not in text:
        if old_return not in text:
            raise RuntimeError("LyricsOvhClient return anchor not found")
        text = text.replace(old_return, new_return, 1)

    CLIENT.write_text(text, encoding="utf-8", newline="\n")
    print("R38_16D_LYRICS_ENCODING_FIX_INSTALL_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
