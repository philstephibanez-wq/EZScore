#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT=Path(sys.argv[1] if len(sys.argv)>1 else r"H:\EZScore_v1").resolve()
JS=ROOT/"public/assets/js/lyrics-dirty-guard-r38-16j.js"
TWIG=ROOT/"templates/song/lyricslab.html.twig"

def main():
    for p in (JS,TWIG):
        if not p.is_file():
            raise RuntimeError(f"Missing prerequisite: {p}")

    js=JS.read_text(encoding="utf-8")
    twig=TWIG.read_text(encoding="utf-8")

    old="""document.addEventListener('submit',event=>{if(!dirty)return;const form=event.target;if(!(form instanceof HTMLFormElement)||form===saveForm)return;if(form.dataset.lyricsDirtyBypass==='1'){delete form.dataset.lyricsDirtyBypass;return}event.preventDefault();event.stopPropagation();showDirtyModal({kind:'form',form,submitter:event.submitter instanceof HTMLElement?event.submitter:null})},true);"""
    new="""document.addEventListener('submit',event=>{if(!dirty)return;const form=event.target;if(!(form instanceof HTMLFormElement)||form===saveForm||form.id==='lyrics-analyze-form')return;if(form.dataset.lyricsDirtyBypass==='1'){delete form.dataset.lyricsDirtyBypass;return}event.preventDefault();event.stopPropagation();showDirtyModal({kind:'form',form,submitter:event.submitter instanceof HTMLElement?event.submitter:null})},true);"""

    if old in js:
        js=js.replace(old,new,1)
    elif "form.id==='lyrics-analyze-form'" not in js:
        raise RuntimeError("Dirty-guard submit anchor not found")

    old_src='<script src="/assets/js/lyrics-dirty-guard-r38-16j.js?v=20260929r38_16j"></script>'
    new_src='<script src="/assets/js/lyrics-dirty-guard-r38-16j.js?v=20260929r38_16m2"></script>'
    if old_src in twig:
        twig=twig.replace(old_src,new_src,1)
    elif "20260929r38_16m2" not in twig:
        raise RuntimeError("Lyrics dirty-guard asset anchor not found")

    JS.write_text(js,encoding="utf-8",newline="\n")
    TWIG.write_text(twig,encoding="utf-8",newline="\n")
    print("R38_16M2_ANALYZE_DIRTY_GUARD_FIX_INSTALL_OK")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
