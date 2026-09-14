"""Guitar voicing catalogue and scalable SVG chord diagrams."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape


@dataclass(frozen=True)
class Voicing:
    name: str
    frets: tuple[int | None, int | None, int | None, int | None, int | None, int | None]
    fingers: tuple[int | None, int | None, int | None, int | None, int | None, int | None]
    barre_fret: int | None = None
    barre_from: int | None = None
    barre_to: int | None = None


VOICINGS: dict[str, tuple[Voicing, ...]] = {
    "A": (
        Voicing("Ouvert", (None, 0, 2, 2, 2, 0), (None, None, 1, 2, 3, None)),
        Voicing("Barré V", (5, 7, 7, 6, 5, 5), (1, 3, 4, 2, 1, 1), 5, 6, 1),
    ),
    "Am": (
        Voicing("Ouvert", (None, 0, 2, 2, 1, 0), (None, None, 2, 3, 1, None)),
        Voicing("Barré V", (5, 7, 7, 5, 5, 5), (1, 3, 4, 1, 1, 1), 5, 6, 1),
    ),
    "C": (
        Voicing("Ouvert", (None, 3, 2, 0, 1, 0), (None, 3, 2, None, 1, None)),
        Voicing("Barré VIII", (8, 10, 10, 9, 8, 8), (1, 3, 4, 2, 1, 1), 8, 6, 1),
    ),
    "D": (
        Voicing("Ouvert", (None, None, 0, 2, 3, 2), (None, None, None, 1, 3, 2)),
        Voicing("Barré V", (None, 5, 7, 7, 7, 5), (None, 1, 3, 3, 3, 1), 5, 5, 1),
    ),
    "Dm": (
        Voicing("Ouvert", (None, None, 0, 2, 3, 1), (None, None, None, 2, 3, 1)),
        Voicing("Barré V", (None, 5, 7, 7, 6, 5), (None, 1, 3, 4, 2, 1), 5, 5, 1),
    ),
    "E": (
        Voicing("Ouvert", (0, 2, 2, 1, 0, 0), (None, 2, 3, 1, None, None)),
        Voicing("Barré XII", (12, 14, 14, 13, 12, 12), (1, 3, 4, 2, 1, 1), 12, 6, 1),
    ),
    "Em": (
        Voicing("Ouvert", (0, 2, 2, 0, 0, 0), (None, 2, 3, None, None, None)),
        Voicing("Barré XII", (12, 14, 14, 12, 12, 12), (1, 3, 4, 1, 1, 1), 12, 6, 1),
    ),
    "F": (
        Voicing("Barré I", (1, 3, 3, 2, 1, 1), (1, 3, 4, 2, 1, 1), 1, 6, 1),
        Voicing("Simplifié", (None, None, 3, 2, 1, 1), (None, None, 3, 2, 1, 1)),
    ),
    "G": (
        Voicing("Ouvert", (3, 2, 0, 0, 0, 3), (2, 1, None, None, None, 3)),
        Voicing("Barré III", (3, 5, 5, 4, 3, 3), (1, 3, 4, 2, 1, 1), 3, 6, 1),
    ),
}


_PITCHES = {
    "C": 0, "B#": 0,
    "C#": 1, "Db": 1,
    "D": 2,
    "D#": 3, "Eb": 3,
    "E": 4, "Fb": 4,
    "F": 5, "E#": 5,
    "F#": 6, "Gb": 6,
    "G": 7,
    "G#": 8, "Ab": 8,
    "A": 9,
    "A#": 10, "Bb": 10,
    "B": 11, "Cb": 11,
}


def _fallback_barre_voicing(symbol: str) -> tuple[Voicing, ...]:
    text = str(symbol or "").strip()
    if not text:
        return ()

    import re

    match = re.fullmatch(r"([A-G](?:#|b)?)(m?)", text)
    if not match:
        return ()

    root, minor_flag = match.groups()
    pitch = _PITCHES.get(root)
    if pitch is None:
        return ()

    # E-shape barre. Use fret 12 for E/Em to avoid a zero-fret barre.
    fret = (int(pitch) - 4) % 12
    if fret == 0:
        fret = 12

    if minor_flag:
        frets = (fret, fret + 2, fret + 2, fret, fret, fret)
        fingers = (1, 3, 4, 1, 1, 1)
    else:
        frets = (fret, fret + 2, fret + 2, fret + 1, fret, fret)
        fingers = (1, 3, 4, 2, 1, 1)

    return (
        Voicing(
            f"Barré {fret}",
            frets,
            fingers,
            fret,
            6,
            1,
        ),
    )


def choices(symbol: str) -> tuple[Voicing, ...]:
    text = str(symbol or "").strip()
    explicit = VOICINGS.get(text)
    if explicit:
        return explicit
    return _fallback_barre_voicing(text)


def get_voicing(symbol: str, name: str | None = None) -> Voicing | None:
    available = choices(symbol)
    if not available:
        return None
    if name:
        for item in available:
            if item.name == name:
                return item
    return available[0]


def _display_base_fret(voicing: Voicing) -> int:
    positive = [fret for fret in voicing.frets if isinstance(fret, int) and fret > 0]
    if not positive:
        return 1
    highest = max(positive)
    if highest <= 4:
        return 1
    if voicing.barre_fret:
        return int(voicing.barre_fret)
    return max(1, min(positive))


def svg(symbol: str, voicing: Voicing, width: int = 150, height: int = 190) -> str:
    """Render an accessible guitar chord diagram as inline SVG."""
    xs = [35 + index * 16 for index in range(6)]
    y0 = 52
    fret_gap = 22
    base = _display_base_fret(voicing)

    parts = [
        (
            f'<svg viewBox="0 0 130 170" width="{int(width)}" height="{int(height)}" '
            'role="img" xmlns="http://www.w3.org/2000/svg" '
            'style="color:#f4f7fb;background:#171b24;border:1px solid #3b4352;border-radius:10px" '
            f'aria-label="Accord {escape(symbol)} — {escape(voicing.name)}">'
        ),
        f'<text x="65" y="23" text-anchor="middle" font-size="24" font-weight="800" fill="#f4f7fb">{escape(symbol)}</text>',
        f'<text x="65" y="39" text-anchor="middle" font-size="10" font-weight="700" fill="#c2ccda">{escape(voicing.name)}</text>',
    ]

    for x in xs:
        parts.append(
            f'<line x1="{x}" y1="{y0}" x2="{x}" y2="{y0 + 88}" '
            'stroke="#dbe4f0" stroke-width="1.35"/>'
        )

    for fret_index in range(5):
        weight = 3 if fret_index == 0 and base == 1 else 1
        y = y0 + fret_index * fret_gap
        parts.append(
            f'<line x1="35" y1="{y}" x2="115" y2="{y}" '
            f'stroke="#dbe4f0" stroke-width="{weight}"/>'
        )

    if base > 1:
        parts.append(
            f'<text x="20" y="{y0 + 16}" text-anchor="middle" font-size="12" font-weight="800" fill="#f4f7fb">{base}</text>'
        )

    if (
        voicing.barre_fret is not None
        and voicing.barre_from is not None
        and voicing.barre_to is not None
    ):
        row = int(voicing.barre_fret) - base + 1
        if 1 <= row <= 4:
            string_a = 6 - int(voicing.barre_from)
            string_b = 6 - int(voicing.barre_to)
            x1 = xs[min(string_a, string_b)]
            x2 = xs[max(string_a, string_b)]
            cy = y0 + (row - 0.5) * fret_gap
            parts.append(
                f'<line x1="{x1}" y1="{cy}" x2="{x2}" y2="{cy}" '
                'stroke="#f4f7fb" stroke-width="14" stroke-linecap="round"/>'
            )
            parts.append(
                f'<text x="{(x1 + x2) / 2}" y="{cy + 3.5}" text-anchor="middle" '
                'font-size="9" font-weight="700" fill="#11151c">1</text>'
            )

    for index, fret in enumerate(voicing.frets):
        x = xs[index]
        finger = voicing.fingers[index]

        if fret is None:
            parts.append(
                f'<text x="{x}" y="47" text-anchor="middle" font-size="17" font-weight="800" fill="#f4f7fb">×</text>'
            )
            continue

        if fret == 0:
            parts.append(
                f'<circle cx="{x}" cy="43" r="4" fill="none" stroke="#f4f7fb" stroke-width="2"/>'
            )
            continue

        if voicing.barre_fret == fret and finger == 1:
            continue

        row = int(fret) - base + 1
        if not 1 <= row <= 4:
            continue

        cy = y0 + (row - 0.5) * fret_gap
        parts.append(
            f'<circle cx="{x}" cy="{cy}" r="8" fill="#f4f7fb" stroke="#11151c" stroke-width="1"/>'
        )
        if finger is not None:
            parts.append(
                f'<text x="{x}" y="{cy + 3.5}" text-anchor="middle" '
                'font-size="9" font-weight="700" fill="var(--ez-diagram-dot-text,#fff)">'
                f'{int(finger)}</text>'
            )

    parts.append("</svg>")
    return "".join(parts)
