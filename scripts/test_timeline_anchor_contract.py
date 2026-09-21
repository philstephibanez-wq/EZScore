from __future__ import annotations

import ast
import importlib.util
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "ezscore" / "player" / "lyrics_layout.py"


def main() -> int:
    src = TARGET.read_text(encoding="utf-8")
    ast.parse(src, filename=str(TARGET))

    # Structural contract.
    required = [
        'const rawX=timelineVisualXForTime(w.start);',
        'span.style.left=rawX+"px";',
        'span.style.top=(4 + lane*32)+"px";',
        'anchor-timelineVisualXForTime(time)',
        'const slots=[];',
        'slots.push(chord);',
        'slots.push("-");',
        'slot.style.left=((slotIndex/slotCount)*100)+"%";',
        'marker.style.padding="0";',
    ]
    for token in required:
        assert token in src, token

    # Forbidden regression: collision code must not replace rawX by previousRight.
    assert "Math.max(rawX, previousRight" not in src
    assert "leadVisualXs" not in src
    assert "ezVisualXForTime(" not in src

    print("TIMELINE ANCHOR CONTRACT OK")
    print("lyrics X: timestamp only")
    print("lyrics collisions: vertical lanes only")
    print("chord onset X: beat/subdivision start")
    print("G--- semantics: 4 beat slots")
    print("horizontal collision shifting: DISABLED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
