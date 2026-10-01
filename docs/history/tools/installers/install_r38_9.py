#!/usr/bin/env python3
from __future__ import annotations
from datetime import datetime
from pathlib import Path
import re, shutil, sys

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parents[1]
BACKUP = ROOT / "var" / "backup" / ("r38-9-" + datetime.now().strftime("%Y%m%d-%H%M%S"))

def read(rel):
    p=ROOT/rel
    if not p.is_file():
        raise RuntimeError(f"Missing required file: {rel}")
    return p.read_text(encoding="utf-8")

def backup(p):
    if not p.exists(): return
    dst=BACKUP/p.relative_to(ROOT)
    dst.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(p,dst)

def save(rel,text):
    p=ROOT/rel
    old=p.read_text(encoding="utf-8") if p.exists() else None
    if old==text:
        print(f"[OK] {rel}: already applied"); return
    if p.exists(): backup(p)
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(text,encoding="utf-8",newline="\n")
    print(f"[OK] {rel}")

def replace_function(text,name,replacement):
    m=re.search(rf"(?m)^def {re.escape(name)}\s*\(",text)
    if not m: return text,False
    nxt=re.search(r"(?m)^def [A-Za-z_]\w*\s*\(",text[m.end():])
    end=m.end()+nxt.start() if nxt else len(text)
    return text[:m.start()]+replacement.rstrip()+"\n\n"+text[end:],True

LEGACY_HELPERS = r'''
def _r389_legacy_interpolate(rows: list[dict]) -> list[dict]:
    known=[i for i,row in enumerate(rows) if row.get("start_ms") is not None]
    if not known:
        raise RuntimeError("No reliable legacy lyric/audio anchor found")
    first_known=known[0]
    if first_known>0:
        anchor=int(rows[first_known]["start_ms"])
        word_ms=190
        base=max(0,anchor-first_known*word_ms)
        for i in range(first_known):
            start=base+i*word_ms
            rows[i].update(start_ms=start,end_ms=min(anchor,start+150),confidence=0.12,language=None)
    known=[i for i,row in enumerate(rows) if row.get("start_ms") is not None]
    for i,row in enumerate(rows):
        if row.get("start_ms") is not None:
            continue
        left=max((k for k in known if k<i),default=None)
        right=min((k for k in known if k>i),default=None)
        if left is not None and right is not None:
            span=max(1,right-left)
            ratio=(i-left)/span
            a=int(rows[left]["end_ms"]); b=int(rows[right]["start_ms"])
            t=int(round(a+(b-a)*ratio))
            row.update(start_ms=t,end_ms=t+120,confidence=0.30)
        elif left is not None:
            t=int(rows[left]["end_ms"])+max(80,(i-left-1)*180)
            row.update(start_ms=t,end_ms=t+160,confidence=0.20)
    return rows

def _r389_legacy_align(provided: list[dict], recognized: list[dict]) -> list[dict]:
    a=[row["norm"] for row in provided]
    b=[row["norm"] for row in recognized]
    matcher=difflib.SequenceMatcher(a=a,b=b,autojunk=False)
    rows=[dict(row,start_ms=None,end_ms=None,confidence=0.0,language=None) for row in provided]
    reliable=[block for block in matcher.get_matching_blocks() if block.size>=2]
    if not reliable:
        singles=[
            block for block in matcher.get_matching_blocks()
            if block.size==1 and float(recognized[block.b].get("confidence",0.0) or 0.0)>=0.80
        ]
        if not singles:
            raise RuntimeError("No reliable exact lyric/audio anchor found")
        singles.sort(key=lambda block:(float(recognized[block.b].get("confidence",0.0) or 0.0),-int(recognized[block.b].get("start_ms",0))),reverse=True)
        reliable=[singles[0]]
    for block in reliable:
        for off in range(block.size):
            pi=block.a+off; ri=block.b+off; src=recognized[ri]
            rows[pi].update(start_ms=src["start_ms"],end_ms=src["end_ms"],confidence=src.get("confidence",0.0),language=src.get("language"))
    return _r389_legacy_interpolate(rows)
'''

ALIGN = r'''
def align_provided_text(provided: list[dict], recognized: list[dict], first_vocal_onset_ms: int | None = None) -> list[dict]:
    if not provided:
        return []
    if not recognized:
        raise RuntimeError("Whisper returned no timed words")
    rows=_r389_legacy_align(provided,recognized)
    if first_vocal_onset_ms is None:
        first_vocal_onset_ms=int(recognized[0]["start_ms"])
    first_index=next((i for i,row in enumerate(rows) if row.get("start_ms") is not None),None)
    if first_index is None:
        raise RuntimeError("Legacy alignment produced no timed lyric row")
    legacy_t0=int(rows[first_index]["start_ms"])
    acoustic_t0=max(0,int(first_vocal_onset_ms))
    offset_ms=acoustic_t0-legacy_t0
    for row in rows:
        if row.get("start_ms") is None:
            continue
        old_start=int(row["start_ms"])
        old_end=int(row.get("end_ms") or old_start+120)
        start=max(acoustic_t0,old_start+offset_ms)
        end=max(start+40,old_end+offset_ms)
        row["start_ms"]=start
        row["end_ms"]=end
        row["timeline_offset_ms"]=offset_ms
    rows[0]["start_ms"]=acoustic_t0
    rows[0]["end_ms"]=max(acoustic_t0+80,int(rows[0].get("end_ms") or acoustic_t0+160))
    rows[0]["anchor"]="acoustic_trigger_global_offset"
    prev=acoustic_t0
    for row in rows:
        if row.get("start_ms") is None:
            continue
        if int(row["start_ms"])<prev:
            delta=prev-int(row["start_ms"])
            row["start_ms"]=prev
            row["end_ms"]=max(prev+40,int(row.get("end_ms") or prev+120)+delta)
        prev=int(row["start_ms"])
    return rows
'''

def patch_analyzer():
    rel="analysis/lyrics_timeline_analysis.py"
    text=read(rel)
    for name in ("_r389_legacy_interpolate","_r389_legacy_align"):
        text,_=replace_function(text,name,"")
    text,ok=replace_function(text,"align_provided_text",ALIGN)
    if not ok:
        raise RuntimeError("align_provided_text() not found; no unsafe edit applied.")
    pos=text.find("def align_provided_text(")
    text=text[:pos]+LEGACY_HELPERS.rstrip()+"\n\n"+text[pos:]
    calls=list(re.finditer(r"(?m)^(?P<i>\s*)rows\s*=\s*align_provided_text\(provided,\s*words(?:,\s*([A-Za-z_]\w*))?\)\s*$",text))
    if not calls:
        raise RuntimeError("Analyzer align call not found.")
    c=calls[-1]; indent=c.group("i")
    repl=indent+"rows = align_provided_text(provided, words, vocal_onset_ms)"
    text=text[:c.start()]+repl+text[c.end():]
    if "[LYRICS] Global lyric offset:" not in text:
        needle=repl
        diag=needle+"\n"+indent+"if rows:\n"+indent+"    print(f\"[LYRICS] Global lyric offset: {rows[0].get('timeline_offset_ms', 0)} ms; trigger={rows[0].get('start_ms')} ms\", flush=True)"
        text=text.replace(needle,diag,1)
    text=text.replace("'version': 'r38.8-acoustic-anchor'","'version': 'r38.9-legacy-plus-acoustic-offset'")
    save(rel,text)

def patch_error_ui():
    rel="public/assets/js/lyricslab-r37.js"
    text=read(rel)
    # Replace the raw backend error assignment if present.
    candidates=[
        r"progressLabel\.textContent\s*=\s*data\.error\s*\|\|\s*'[^']*';",
        r"progressLabel\.textContent\s*=\s*data\?\.error\s*\|\|\s*'[^']*';",
        r"progressLabel\.textContent\s*=\s*String\(data\.error[^;]*;"
    ]
    done=False
    for pat in candidates:
        new,n=re.subn(pat,"progressLabel.textContent='Analyse des paroles en échec. Voir le journal du Worker.';",text,count=1)
        if n:
            text=new; done=True; break
    if not done and "R38.9 concise error UI" not in text:
        text += '''
\n/* R38.9 concise error UI */
(() => {
 const label=document.querySelector('[data-lyrics-progress-text]');
 if(!label)return;
 const clean=()=>{
  const v=String(label.textContent||'');
  if(v.includes('lyrics_python_exit_')||v.includes('Traceback')||v.includes('RuntimeError:')||v.includes('lyrics_timeline_analysis.py')){
   label.textContent='Analyse des paroles en échec. Voir le journal du Worker.';
  }
 };
 new MutationObserver(clean).observe(label,{childList:true,subtree:true,characterData:true});
 clean();
})();
'''
    save(rel,text)

def patch_cache():
    rel="templates/song/lyricslab.html.twig"
    text=read(rel)
    text=re.sub(r"lyricslab-r37\.js\?v=[^\"']+","lyricslab-r37.js?v=20260928r38_9",text,count=1)
    save(rel,text)

def main():
    patch_analyzer()
    patch_error_ui()
    patch_cache()
    print(f"[OK] Backup: {BACKUP}")
    print("R38_9_INSTALL_OK")

if __name__=="__main__":
    main()
