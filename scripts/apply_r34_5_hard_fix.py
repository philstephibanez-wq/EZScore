#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
BACKUP = ROOT / "var" / "backup" / ("r34-5-hard-fix-" + datetime.now().strftime("%Y%m%d-%H%M%S"))

CSS_MARKER = "/* R34.5 — hard visual override */"
CSS = r"""
/* R34.5 — hard visual override */
.chord-measure-notation .chord-slot.is-long,
.chord-measure-notation .chord-slot.is-very-long {
    font-size: 14px !important;
    letter-spacing: normal !important;
}
.chord-measure-notation .chord-slot .chord-label-root {
    font-size: 15px !important;
    font-weight: 800 !important;
    line-height: 1 !important;
}
.chord-measure-notation .chord-slot .chord-label-suffix {
    font-size: 11px !important;
    line-height: 1 !important;
}
.chord-measure-notation .chord-slot .chord-quality-maj {
    font-size: 8px !important;
    vertical-align: super !important;
    line-height: 1 !important;
    letter-spacing: 0 !important;
}
.chordslab-settings-grid .chordslab-diagram-toggle,
.chordslab-settings-grid .chordslab-diagram-inline {
    grid-column: 1 / -1 !important;
    display: flex !important;
    grid-template-columns: none !important;
    align-items: center !important;
    gap: 8px !important;
    width: max-content !important;
    max-width: 100% !important;
    padding: 0 !important;
}
.chordslab-settings-grid .chordslab-diagram-toggle > span,
.chordslab-settings-grid .chordslab-diagram-inline > span {
    display: inline !important;
    white-space: nowrap !important;
    margin: 0 !important;
    font-size: 13px !important;
    line-height: 1.2 !important;
    font-weight: 600 !important;
    text-transform: none !important;
    letter-spacing: 0 !important;
}
.chordslab-settings-save-state {
    grid-column: 1 / -1 !important;
    min-width: 0 !important;
    margin-top: -3px !important;
}
.chordslab-song-card {
    grid-template-columns: 2fr 1.5fr repeat(4, minmax(90px, .7fr));
}
@media(max-width:1024px) {
    .chordslab-song-card { grid-template-columns: repeat(3, 1fr); }
}
@media(max-width:640px) {
    .chordslab-settings-grid .chordslab-diagram-toggle,
    .chordslab-settings-grid .chordslab-diagram-inline { width: 100% !important; }
    .chordslab-settings-grid .chordslab-diagram-toggle > span,
    .chordslab-settings-grid .chordslab-diagram-inline > span { white-space: normal !important; }
}
"""

def backup(path: Path) -> None:
    if not path.exists():
        return
    dst = BACKUP / path.relative_to(ROOT)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dst)

def patch_css() -> None:
    path = ROOT / "public/assets/css/chordslab.css"
    text = path.read_text(encoding="utf-8")
    if CSS_MARKER not in text:
        backup(path)
        path.write_text(text.rstrip() + "\n\n" + CSS.strip() + "\n", encoding="utf-8", newline="\n")
        print("[OK] modified public/assets/css/chordslab.css")
    else:
        print("[OK] public/assets/css/chordslab.css already patched")

def patch_template() -> None:
    path = ROOT / "templates/song/chordslab.html.twig"
    text = path.read_text(encoding="utf-8")
    original = text

    text = text.replace(
        "/assets/css/chordslab.css?v=20260927r34_1",
        "/assets/css/chordslab.css?v=20260927r34_5",
    )
    text = text.replace(
        "/assets/css/chordslab.css?v=20260927r34_4",
        "/assets/css/chordslab.css?v=20260927r34_5",
    )
    text = text.replace(
        "/assets/js/chordslab-r33-1.js?v=20260926r33_1a",
        "/assets/js/chordslab-r33-1.js?v=20260927r34_5",
    )
    text = text.replace(
        "/assets/js/chordslab-r33-1.js?v=20260927r34_3",
        "/assets/js/chordslab-r33-1.js?v=20260927r34_5",
    )

    # Also bust the main ChordsLab renderer cache, because it provides rich chord markup.
    text = text.replace(
        "/assets/js/chordslab.js?v=20260927r34_1",
        "/assets/js/chordslab.js?v=20260927r34_5",
    )

    if text == original:
        if "20260927r34_5" in text:
            print("[OK] template cache versions already patched")
            return
        raise RuntimeError("ChordsLab asset version anchors not found in template.")

    backup(path)
    path.write_text(text, encoding="utf-8", newline="\n")
    print("[OK] modified templates/song/chordslab.html.twig")

def main() -> None:
    patch_css()
    patch_template()
    print("[OK] direct replacements already extracted:")
    print("     public/assets/js/chordslab-r33-1.js")
    print("     translations/stems.fr.yaml")
    print("[OK] Backup:", BACKUP)
    print("[OK] R34.5 applied.")

if __name__ == "__main__":
    main()
