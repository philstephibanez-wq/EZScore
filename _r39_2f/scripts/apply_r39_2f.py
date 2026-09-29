#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else r"H:\EZScore_v1").resolve()
TWIG = ROOT / "templates/song/lyricslab.html.twig"

def rd(p):
    return p.read_text(encoding="utf-8").replace("\r\n","\n").replace("\r","\n")

def wr(p, text):
    tmp = p.with_suffix(p.suffix + ".r39_2f_tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    tmp.replace(p)

def main():
    if not TWIG.is_file():
        raise RuntimeError(f"Missing prerequisite: {TWIG}")

    original = TWIG.read_bytes()
    try:
        s = rd(TWIG)

        include = (
            "{% include 'song/components/_live_visual_settings.html.twig' with {\n"
            "    song:song,\n"
            "    context:'lyrics'\n"
            "} %}"
        )

        if include not in s:
            raise RuntimeError("Lyrics shared visual settings include not found")

        # Remove current placement.
        s = s.replace(include + "\n\n", "", 1)

        anchor = '<section class="panel chordslab-prompter"\n         data-lyricslab'
        if anchor not in s:
            raise RuntimeError("Lyrics timeline panel anchor not found")

        # Reinsert immediately above the timeline/prompter panel.
        s = s.replace(anchor, include + "\n\n" + anchor, 1)

        wr(TWIG, s)
        print("R39_2F_MOVE_VISUAL_SETTINGS_LYRICS_INSTALL_OK")
    except Exception:
        TWIG.write_bytes(original)
        raise

if __name__ == "__main__":
    main()
