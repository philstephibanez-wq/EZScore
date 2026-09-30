#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else r"H:\EZScore_v1").resolve()
CSS = ROOT / "public/assets/css/chordslab.css"
TWIG = ROOT / "templates/song/chordslab.html.twig"

def rd(p):
    return p.read_text(encoding="utf-8").replace("\r\n","\n").replace("\r","\n")

def wr(p, text):
    tmp = p.with_suffix(p.suffix + ".r39_3a_tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    tmp.replace(p)

def main():
    for p in (CSS, TWIG):
        if not p.is_file():
            raise RuntimeError(f"Missing prerequisite: {p}. STOP.")

    backups = {CSS: CSS.read_bytes(), TWIG: TWIG.read_bytes()}
    try:
        css = rd(CSS)
        twig = rd(TWIG)

        # Strictly target the consolidated R39.3 local source state.
        if "/* R39.3 — consolidated fixed-focus prompter." not in css:
            raise RuntimeError("R39.3 consolidated CSS baseline missing. STOP.")
        if "/assets/css/chordslab.css?v=20260930r39_3" not in twig:
            raise RuntimeError("R39.3 chordslab.css asset baseline missing. STOP.")
        if 'data-chord-analyze-dialog' not in twig:
            raise RuntimeError("Chord analyze dialog baseline missing. STOP.")

        marker = "/* R39.3A — closed dialogs must never participate in layout */"
        if marker in css:
            raise RuntimeError("R39.3A already appears installed. STOP.")

        css = css.rstrip() + """

/* R39.3A — closed dialogs must never participate in layout */
dialog.ez-modal:not([open]),
dialog[data-chord-analyze-dialog]:not([open]){
    display:none!important;
}
dialog.ez-modal[open],
dialog[data-chord-analyze-dialog][open]{
    display:block;
}
"""

        twig = twig.replace(
            "/assets/css/chordslab.css?v=20260930r39_3",
            "/assets/css/chordslab.css?v=20260930r39_3a",
            1
        )

        wr(CSS, css)
        wr(TWIG, twig)

        print("R39_3A_MODAL_HIDDEN_INSTALL_OK")

    except Exception:
        for p, data in backups.items():
            p.write_bytes(data)
        raise

if __name__ == "__main__":
    main()
