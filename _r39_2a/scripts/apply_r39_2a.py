#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path.cwd()
JS = ROOT / "public/assets/js/stems-mixer.js"
CSS = ROOT / "public/assets/css/stems.css"
TEMPLATES = [
    ROOT / "templates/stems/index.html.twig",
    ROOT / "templates/song/chordslab.html.twig",
    ROOT / "templates/song/lyricslab.html.twig",
]

def rd(p):
    return p.read_text(encoding="utf-8").replace("\r\n","\n").replace("\r","\n")

def wr(p, s):
    tmp = p.with_suffix(p.suffix + ".r39_2a_tmp")
    tmp.write_text(s, encoding="utf-8", newline="\n")
    tmp.replace(p)

def main():
    for p in [JS, CSS, *TEMPLATES]:
        if not p.is_file():
            raise RuntimeError(f"Missing expected file: {p}")

    backups = {p: p.read_bytes() for p in [JS, CSS, *TEMPLATES]}
    try:
        js = rd(JS)
        old = '''        if (track.status) {
            track.status.textContent =
                state === 'loading' ? 'chargement' :
                state === 'buffering' ? 'buffering' :
                state === 'error' ? 'erreur' :
                state === 'playing' ? 'lecture' :
                state === 'ready' ? 'prêt' : '';
        }'''
        new = '''        if (track.status) {
            track.status.textContent =
                state === 'loading' ? 'chargement' :
                state === 'buffering' ? 'buffering' :
                state === 'error' ? 'erreur' :
                state === 'playing' ? 'lecture' :
                state === 'ready' ? 'prêt' : '';
            track.status.dataset.state = state || 'idle';
        }'''
        if "track.status.dataset.state = state || 'idle';" not in js:
            if old not in js:
                raise RuntimeError("track status anchor missing in stems-mixer.js")
            js = js.replace(old, new, 1)
        wr(JS, js)

        css = rd(CSS)
        marker = "/* R39.2A compact readable track state */"
        if marker not in css:
            css += '''

/* R39.2A compact readable track state
   Keep existing R29/R39.2 mixer proportions unchanged. */
.stem-track-load-status{
    min-width:34px!important;
    max-width:52px!important;
    overflow:visible!important;
    text-overflow:clip!important;
    white-space:nowrap!important;
    padding:2px 5px!important;
    border:1px solid #36515d;
    border-radius:999px;
    background:rgba(27,47,58,.28);
    color:#9fc5d2!important;
    font-size:8px!important;
    font-weight:800!important;
    line-height:1.15!important;
    letter-spacing:.02em!important;
    text-transform:uppercase;
    text-align:center;
}
.stem-track-load-status:empty{
    padding:0!important;
    border:0!important;
    background:transparent!important;
    min-width:0!important;
}
.stem-track-load-status[data-state="ready"]{
    border-color:#365f6f;
    color:#9ed7ee!important;
    background:rgba(31,75,94,.18);
}
.stem-track-load-status[data-state="playing"]{
    border-color:#3e735f;
    color:#a8e4c1!important;
    background:rgba(45,111,81,.16);
}
.stem-track-load-status[data-state="loading"],
.stem-track-load-status[data-state="buffering"]{
    border-color:#75623d;
    color:#e7cb8a!important;
    background:rgba(110,82,31,.16);
}
.stem-track-load-status[data-state="error"]{
    border-color:#7d4141;
    color:#f0aaaa!important;
    background:rgba(120,48,48,.16);
}
'''
        wr(CSS, css)

        for p in TEMPLATES:
            s = rd(p)
            s = re.sub(r'(/assets/css/stems\.css\?v=)[^"]+', r'\g<1>20260929r39_2a', s, count=1)
            s = re.sub(r'(/assets/js/stems-mixer\.js\?v=)[^"]+', r'\g<1>20260929r39_2a', s, count=1)
            wr(p, s)

        print("R39.2A_TRACK_READY_BADGE_APPLIED")
    except Exception:
        for p, data in backups.items():
            p.write_bytes(data)
        raise

if __name__ == "__main__":
    main()
