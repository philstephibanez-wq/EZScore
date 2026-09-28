#!/usr/bin/env python3
from pathlib import Path
import sys
repo=Path(sys.argv[1] if len(sys.argv)>1 else ".").resolve()
twig=repo/"templates"/"song"/"lyricslab.html.twig"
mixer=repo/"public"/"assets"/"js"/"stems-mixer.js"
view=twig.read_text(encoding="utf-8")
view=view.replace("/assets/css/lyricslab-r37.css?v=20260928r37_0","/assets/css/lyricslab-r37.css?v=20260928r38_1").replace("/assets/css/lyricslab-r37.css?v=20260928r38_0b","/assets/css/lyricslab-r37.css?v=20260928r38_1")
view=view.replace("/assets/js/lyricslab-r37.js?v=20260928r37_0","/assets/js/lyricslab-r37.js?v=20260928r38_1").replace("/assets/js/lyricslab-r37.js?v=20260928r38_0b","/assets/js/lyricslab-r37.js?v=20260928r38_1")
twig.write_text(view,encoding="utf-8",newline="\n")
src=mixer.read_text(encoding="utf-8")
if "root.addEventListener('ezscore:request-seek'" not in src:
    needle="    engine.addEventListener('statechange', (event) => {"
    add="    root.addEventListener('ezscore:request-seek', (event) => {\\n        const time=Math.max(0,Number(event.detail?.time||0));\\n        engine.seek(time);\\n        const duration=engine.duration();\\n        if(els.seek&&duration>0) els.seek.value=String(Math.round((time/duration)*1000));\\n    });\\n\\n"
    if needle not in src: raise SystemExit("stems mixer insertion point not found")
    src=src.replace(needle,add+needle,1)
mixer.write_text(src,encoding="utf-8",newline="\n")
print("R38_1_INSTALL_OK")