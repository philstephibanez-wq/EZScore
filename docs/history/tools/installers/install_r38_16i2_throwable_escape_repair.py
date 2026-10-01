#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else r"H:\EZScore_v1").resolve()
CLIENT = ROOT / "src/Service/LyricsOvhClient.php"

def main() -> int:
    if not CLIENT.is_file():
        raise RuntimeError(f"Missing prerequisite: {CLIENT}")

    text = CLIENT.read_text(encoding="utf-8")

    # R38.16i1 accidentally wrote PHP namespace separators twice in catch clauses:
    #     catch (\\Throwable)
    # PHP expects:
    #     catch (\Throwable)
    count = text.count(r'\\Throwable')
    if count == 0:
        if r'\Throwable' not in text:
            raise RuntimeError("No Throwable catch clauses found in LyricsOvhClient.php")
        print("R38_16I2_THROWABLE_ESCAPE_REPAIR_ALREADY_OK")
        return 0

    text = text.replace(r'\\Throwable', r'\Throwable')
    CLIENT.write_text(text, encoding="utf-8", newline="\n")

    remaining = text.count(r'\\Throwable')
    if remaining:
        raise RuntimeError(f"Double-escaped Throwable remains: {remaining}")

    print(f"R38_16I2_THROWABLE_ESCAPE_REPAIR_OK ({count} replacement(s))")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
