#!/usr/bin/env python3
from pathlib import Path
import re, shutil, sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else r"H:\EZScore_v1").resolve()
HERE = Path(__file__).resolve().parent.parent

BASE = "bcd7448da6e7e0b81d950859545043e9f80da504"

JS = ROOT/"public/assets/js/chordslab.js"
CSS = ROOT/"public/assets/css/chordslab.css"
TWIG = ROOT/"templates/song/chordslab.html.twig"

FOCUS = ROOT/"public/assets/js/components/ezscore-focus-track.js"
DIAGJS = ROOT/"public/assets/js/components/ezscore-chord-diagram.js"
DIAGCSS = ROOT/"public/assets/css/components/ezscore-chord-diagram.css"

PATCH_FOCUS = HERE/"patches/public/assets/js/components/ezscore-focus-track.js"
PATCH_DIAGJS = HERE/"patches/public/assets/js/components/ezscore-chord-diagram.js"
PATCH_DIAGCSS = HERE/"patches/public/assets/css/components/ezscore-chord-diagram.css"

def rd(p):
    return p.read_text(encoding="utf-8").replace("\r\n","\n").replace("\r","\n")

def wr(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix+".r39_3_tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    tmp.replace(p)

def once(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise RuntimeError(f"{label}: expected 1 anchor, found {n}. STOP.")
    return text.replace(old,new,1)

def main():
    for p in (JS,CSS,TWIG,PATCH_FOCUS,PATCH_DIAGJS,PATCH_DIAGCSS):
        if not p.is_file():
            raise RuntimeError(f"Missing prerequisite: {p}. STOP.")

    js, css, twig = rd(JS), rd(CSS), rd(TWIG)

    # Strict clean R39.2F baseline checks BEFORE any write.
    baseline_checks = [
        ("timeline core", "EZScoreTimelineCoreR39?.create" in js),
        ("static diagram", "const diagramEl=root.querySelector('[data-chord-diagram]');" in js),
        ("render baseline", "box.appendChild(notation);measuresEl.appendChild(box);" in js),
        ("highlight baseline", "root.dispatchEvent(new CustomEvent('ezscore:chord-current'" in js),
        ("twig baseline css", "/assets/css/chordslab.css?v=20260928r35_8a" in twig),
        ("twig baseline js", "/assets/js/chordslab.js?v=20260929r39_0" in twig),
        ("static diagram twig", '<div class="chord-diagram" data-chord-diagram hidden></div>' in twig),
        ("profile status", '<div class="chord-profile-status">' in twig),
    ]
    bad = [name for name, ok in baseline_checks if not ok]
    if bad:
        raise RuntimeError("Unexpected baseline: "+", ".join(bad)+". STOP.")

    # Ensure consolidated files don't already exist.
    for p in (FOCUS,DIAGJS,DIAGCSS):
        if p.exists():
            raise RuntimeError(f"Unexpected existing generated component: {p}. STOP.")

    backups = {JS:JS.read_bytes(), CSS:CSS.read_bytes(), TWIG:TWIG.read_bytes()}
    created = []

    try:
        # --- JS: remove local shape table; rendering becomes shared.
        js, n = re.subn(
            r"const SHAPES=\{\n.*?\n\};\n\n",
            "",
            js,
            count=1,
            flags=re.S
        )
        if n != 1:
            raise RuntimeError("SHAPES block anchor mismatch. STOP.")

        # Render measures inside one moving track.
        js = once(
            js,
            """function render(){
 measuresEl.innerHTML='';
 for(const measure of buildProjection()){""",
            """function render(){
 measuresEl.innerHTML='';
 const track=document.createElement('div');
 track.className='chordslab-measures-track';
 track.dataset.chordslabMeasuresTrack='1';
 measuresEl.appendChild(track);
 for(const measure of buildProjection()){""",
            "render track creation"
        )
        js = once(
            js,
            "box.appendChild(notation);measuresEl.appendChild(box);",
            "box.appendChild(notation);track.appendChild(box);",
            "render track append"
        )

        # Insert shared controllers before highlightAt.
        anchor = "\nfunction highlightAt(seconds){"
        if js.count(anchor) != 1:
            raise RuntimeError("highlightAt anchor mismatch. STOP.")
        shared_block = r"""
const focusTrack = new window.EZScoreFocusTrack(measuresEl,{
 track:()=>measuresEl.querySelector('[data-chordslab-measures-track]'),
 target:()=>diagramEl,
 fallbackRatio:()=>{
  if(window.matchMedia('(max-width:640px)').matches)return .38;
  if(window.matchMedia('(max-width:900px)').matches)return .30;
  return .25;
 }
});

function alignCurrentTime(slot,seq,ms){
 if(!slot)return;
 const next=measuresEl.querySelector(`.chord-slot[data-beat-seq="${seq+1}"]`);
 const t0=Number(slot.dataset.startMs||ms);
 const t1=next?Number(next.dataset.startMs||t0):t0;
 const progress=next&&t1>t0?Math.max(0,Math.min(1,(ms-t0)/(t1-t0))):0;
 focusTrack.alignBetween(slot,next,progress);
}
"""
        js = js.replace(anchor, "\n"+shared_block+anchor, 1)

        # Highlight now drives the track continuously from canonical audio time.
        old = """if(slot){slot.classList.add('is-current');const m=slot.closest('.chord-measure');m?.classList.add('is-current');root.dispatchEvent(new CustomEvent('ezscore:chord-current',{detail:{beatSeq:seq,timeMs:ms}}))}"""
        new = """if(slot){slot.classList.add('is-current');const m=slot.closest('.chord-measure');m?.classList.add('is-current');alignCurrentTime(slot,seq,ms);root.dispatchEvent(new CustomEvent('ezscore:chord-current',{detail:{beatSeq:seq,timeMs:ms}}))}"""
        js = once(js, old, new, "highlight focus")

        # Replace local diagram renderer by shared renderer.
        start = js.find("function updateDiagram(chord){")
        end = js.find("\nfunction escapeHtml", start)
        if start < 0 or end < 0:
            raise RuntimeError("updateDiagram block anchor mismatch. STOP.")
        new_update = """function updateDiagram(chord){
 if(!diagramEl||!diagramToggle?.checked||!chord||chord==='.'){
  if(diagramEl){diagramEl.hidden=true;diagramEl.innerHTML=''}
  return;
 }
 diagramEl.classList.add('ez-chord-diagram');
 window.EZScoreChordDiagram.render(diagramEl,chord);
}
"""
        js = js[:start] + new_update + js[end:]

        # Shared visual settings toggle: immediately show/hide without reload.
        toggle_anchor = "diagramToggle?.addEventListener('change',"
        if toggle_anchor in js:
            # keep existing listener
            pass
        else:
            insert_at = js.rfind("\nrender();")
            if insert_at < 0:
                raise RuntimeError("render tail anchor missing. STOP.")
            listener = """
diagramToggle?.addEventListener('change',()=>{
 const mixer=document.querySelector('[data-stem-mixer]');
 const time=Number(mixer?.querySelector('[data-mixer-seek]')?.value||0);
 if(!diagramToggle.checked&&diagramEl){diagramEl.hidden=true;diagramEl.innerHTML=''}
});
"""
            js = js[:insert_at] + "\n" + listener + js[insert_at:]

        # --- CSS: append a single final ownership layer.
        css += r"""

/* R39.3 — consolidated fixed-focus prompter.
   Historical architecture: fixed viewport + translate3d track. */
.chordslab-stage{
    --chord-focus-x:25%;
    position:relative!important;
    display:block!important;
    overflow:hidden!important;
    padding-top:164px!important;
    min-height:220px;
}
.chordslab-stage .chord-diagram{
    position:absolute!important;
    top:0!important;
    left:var(--chord-focus-x)!important;
    transform:translateX(-50%)!important;
    z-index:5!important;
}
.chordslab-stage .chordslab-measures{
    display:block!important;
    position:relative!important;
    width:100%!important;
    overflow:hidden!important;
    overflow-x:hidden!important;
    overflow-y:hidden!important;
    padding:4px 0 10px!important;
    margin:0!important;
    scroll-snap-type:none!important;
    scroll-behavior:auto!important;
    scrollbar-width:none!important;
}
.chordslab-stage .chordslab-measures::-webkit-scrollbar{display:none!important}
.chordslab-measures-track{
    display:flex;
    gap:8px;
    width:max-content;
    padding:0 12px;
    box-sizing:border-box;
    will-change:transform;
    transform:translate3d(0,0,0);
    transition:none!important;
}
@media(max-width:900px){
    .chordslab-stage{--chord-focus-x:30%}
}
@media(max-width:640px){
    .chordslab-stage{
        --chord-focus-x:38%;
        padding-top:152px!important;
    }
    .chordslab-measures-track{padding-inline:8px}
}
"""

        # --- Twig: remove redundant "Profil affiché".
        twig, n = re.subn(
            r"\n\s*<div class=\"chord-profile-status\">.*?</div>\n",
            "\n",
            twig,
            count=1,
            flags=re.S
        )
        if n != 1:
            raise RuntimeError("profile status block mismatch. STOP.")

        # Add shared diagram CSS.
        twig = once(
            twig,
            '<link rel="stylesheet" href="/assets/css/chordslab.css?v=20260928r35_8a">',
            '<link rel="stylesheet" href="/assets/css/chordslab.css?v=20260930r39_3">\n<link rel="stylesheet" href="/assets/css/components/ezscore-chord-diagram.css?v=20260930r39_3">',
            "twig css assets"
        )

        # Add shared JS before chordslab.js.
        twig = once(
            twig,
            '<script src="/assets/js/chordslab.js?v=20260929r39_0"></script>',
            '<script src="/assets/js/components/ezscore-chord-diagram.js?v=20260930r39_3"></script>\n<script src="/assets/js/components/ezscore-focus-track.js?v=20260930r39_3"></script>\n<script src="/assets/js/chordslab.js?v=20260930r39_3"></script>',
            "twig js assets"
        )

        # Final structural validation before writes.
        required_js = [
            "new window.EZScoreFocusTrack(measuresEl",
            "data-chordslab-measures-track",
            "alignCurrentTime(slot,seq,ms)",
            "window.EZScoreChordDiagram.render",
        ]
        for token in required_js:
            if token not in js:
                raise RuntimeError(f"Generated JS missing {token}. STOP.")

        if "scrollIntoView(" in js or ".scrollTo(" in js or ".scrollBy(" in js:
            raise RuntimeError("Native realtime scroll logic found in generated chordslab.js. STOP.")

        # Write created components + modified files atomically-ish with rollback.
        for src, dst in ((PATCH_FOCUS,FOCUS),(PATCH_DIAGJS,DIAGJS),(PATCH_DIAGCSS,DIAGCSS)):
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src,dst)
            created.append(dst)

        wr(JS,js); wr(CSS,css); wr(TWIG,twig)

        print("R39_3_CONSOLIDATED_PROMPTER_INSTALL_OK")

    except Exception:
        for p,data in backups.items():
            p.write_bytes(data)
        for p in created:
            if p.exists():
                p.unlink()
        raise

if __name__ == "__main__":
    main()
