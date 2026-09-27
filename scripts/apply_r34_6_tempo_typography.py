#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
BACKUP = ROOT / "var" / "backup" / ("r34-6-tempo-typography-" + datetime.now().strftime("%Y%m%d-%H%M%S"))

def backup(path: Path) -> None:
    if not path.exists():
        return
    dst = BACKUP / path.relative_to(ROOT)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dst)

def save(path: Path, text: str, label: str) -> None:
    old = path.read_text(encoding="utf-8")
    if old == text:
        print(f"[OK] {label}: already applied")
        return
    backup(path)
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"[OK] {label}")

def patch_main_js() -> None:
    path = ROOT / "public/assets/js/chordslab.js"
    text = path.read_text(encoding="utf-8")

    # R34.4 appended a second runtime tempo renderer to chordslab.js.
    # Remove it: R34.5/R34.6 keeps one tempo owner in chordslab-r33-1.js.
    pattern = re.compile(
        r"\n?/\* R34\.4 tempo display: derived from canonical beat timeline, no reanalysis required \*/\n"
        r"\(function installTempoDisplay\(\)\{.*?\}\)\(\);\n?",
        re.S,
    )
    text, count = pattern.subn("\n", text, count=1)
    if count:
        print("[OK] duplicate R34.4 tempo renderer removed from chordslab.js")
    elif "R34.4 tempo display: derived from canonical beat timeline" in text:
        raise RuntimeError("Unable to remove R34.4 tempo renderer structurally.")

    save(path, text, "single tempo owner")

def patch_secondary_js() -> None:
    path = ROOT / "public/assets/js/chordslab-r33-1.js"
    text = path.read_text(encoding="utf-8")

    # Make tempo idempotent even if an older renderer remains in cache or source.
    text = text.replace(
        "if(!card||card.querySelector('[data-chordslab-tempo-runtime]'))return;",
        "if(!card)return;\n"
        "    const existingTempo=card.querySelectorAll('.chordslab-tempo-value,[data-chordslab-tempo-runtime]');\n"
        "    if(existingTempo.length){\n"
        "        existingTempo.forEach((node,index)=>{if(index>0)node.remove()});\n"
        "        return;\n"
        "    }",
        1,
    )

    # Typography: root a little larger, suffix small but on the same baseline.
    replacements = {
        "font-size:15px!important;": "font-size:17px!important;",
        "font-size:11px!important;": "font-size:12px!important;",
        "font-size:8px!important;": "font-size:10px!important;",
        "vertical-align:super!important;": "vertical-align:baseline!important;",
    }
    for old, new in replacements.items():
        if old in text:
            text = text.replace(old, new, 1)

    # Align root + suffix on baseline inside the slot.
    old_css = """.chord-measure-notation .chord-slot .chord-label-root{
    font-size:17px!important;
    font-weight:800!important;
    line-height:1!important;
    flex:0 0 auto!important;
}"""
    new_css = """.chord-measure-notation .chord-slot{
    align-items:baseline!important;
}
.chord-measure-notation .chord-slot .chord-label-root{
    font-size:17px!important;
    font-weight:800!important;
    line-height:1!important;
    flex:0 0 auto!important;
}"""
    if old_css in text and ".chord-measure-notation .chord-slot{\n    align-items:baseline!important;" not in text:
        text = text.replace(old_css, new_css, 1)

    # Cache/version-independent marker.
    if "R34.6 — single tempo + baseline chord suffixes" not in text:
        text = text.replace(
            "/* R34.5 — final high-priority ChordsLab visual corrections */",
            "/* R34.5 — final high-priority ChordsLab visual corrections */\n"
            "/* R34.6 — single tempo + baseline chord suffixes */",
            1,
        )

    save(path, text, "tempo de-dup + chord typography")

def patch_css() -> None:
    path = ROOT / "public/assets/css/chordslab.css"
    text = path.read_text(encoding="utf-8")
    marker = "/* R34.6 — chord baseline final override */"
    if marker not in text:
        text = text.rstrip() + """

/* R34.6 — chord baseline final override */
.chord-measure-notation .chord-slot{
    align-items:baseline!important;
}
.chord-measure-notation .chord-slot.is-long,
.chord-measure-notation .chord-slot.is-very-long{
    font-size:16px!important;
    letter-spacing:normal!important;
}
.chord-measure-notation .chord-slot .chord-label-root{
    font-size:17px!important;
    line-height:1!important;
}
.chord-measure-notation .chord-slot .chord-label-suffix{
    font-size:12px!important;
    line-height:1!important;
    vertical-align:baseline!important;
}
.chord-measure-notation .chord-slot .chord-quality-maj{
    font-size:10px!important;
    line-height:1!important;
    vertical-align:baseline!important;
    position:relative!important;
    top:0!important;
}
.chord-measure-notation .chord-slot .chord-label-bass{
    font-size:11px!important;
    line-height:1!important;
    vertical-align:baseline!important;
}
"""
    save(path, text + ("\n" if not text.endswith("\n") else ""), "R34.6 CSS override")

def patch_template() -> None:
    path = ROOT / "templates/song/chordslab.html.twig"
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"chordslab\.css\?v=[^\"']+", "chordslab.css?v=20260927r34_6", text, count=1)
    text = re.sub(r"chordslab\.js\?v=[^\"']+", "chordslab.js?v=20260927r34_6", text, count=1)
    text = re.sub(r"chordslab-r33-1\.js\?v=[^\"']+", "chordslab-r33-1.js?v=20260927r34_6", text, count=1)
    save(path, text, "R34.6 asset cache bust")

def main() -> None:
    patch_main_js()
    patch_secondary_js()
    patch_css()
    patch_template()
    print(f"[OK] Backup: {BACKUP}")
    print("[OK] R34.6 applied.")

if __name__ == "__main__":
    main()
