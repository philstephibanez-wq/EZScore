#!/usr/bin/env python3
from pathlib import Path
import re
import sys

repo = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()

def load(rel):
    p = repo / rel
    if not p.is_file():
        raise SystemExit(f'ABSENT: {p}')
    return p, p.read_text(encoding='utf-8')

def save(p, text):
    p.write_text(text, encoding='utf-8', newline='\n')

# ----------------------------------------------------------------------
# 1. Generic source sections + robust first acoustic anchor.
# ----------------------------------------------------------------------
p, py = load('analysis/lyrics_timeline_analysis.py')

section_fn = r"""def section_label(line: str) -> str | None:
    s = line.strip()
    if not s:
        return None

    # Declarative sections: no whitelist and no implicit sections.
    m = re.fullmatch(r'\[([^\[\]\r\n]{1,120})\]', s)
    if m:
        label = m.group(1).strip()
        return label or None

    m = re.fullmatch(r'([^\r\n:]{1,120}):', s)
    if m:
        label = m.group(1).strip()
        return label or None

    return None
"""
pat = re.compile(
    r"def section_label\(line: str\) -> str \| None:\n.*?(?=\n_CHORD_TOKEN_RE=)",
    re.S,
)
if not pat.search(py):
    raise SystemExit('section_label function not found')
py = pat.sub(section_fn.rstrip() + '\n', py, count=1)

alignment_block = r"""def _token_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return difflib.SequenceMatcher(a=a, b=b, autojunk=False).ratio()


def _first_acoustic_anchor(provided: list[dict], recognized: list[dict]) -> tuple[int, int] | None:
    # Search the recording chronologically instead of letting a global LCS jump
    # to a later repeated verse/refrain. An isolated "Je" is insufficient:
    # require a local phrase cluster around the candidate.
    a = [row['norm'] for row in provided]
    b = [row['norm'] for row in recognized]
    if not a or not b:
        return None

    max_source_skip = min(3, len(a) - 1)

    for ri in range(len(b)):
        for pi in range(max_source_skip + 1):
            total = min(5, len(a) - pi, len(b) - ri)
            if total < 2:
                continue

            matches = 0
            consecutive = 0
            best_consecutive = 0
            confidences = []

            for off in range(total):
                sim = _token_similarity(a[pi + off], b[ri + off])
                conf = float(recognized[ri + off].get('confidence', 0.0) or 0.0)
                confidences.append(conf)

                if sim >= 0.82:
                    matches += 1
                    consecutive += 1
                    best_consecutive = max(best_consecutive, consecutive)
                else:
                    consecutive = 0

            avg_conf = sum(confidences) / max(1, len(confidences))

            # Strong phrase cluster. This rejects an isolated intro hallucination,
            # but accepts e.g. "Je vous parle" at the real vocal entrance.
            if best_consecutive >= 2 and matches >= min(3, total) and avg_conf >= 0.25:
                return pi, ri

    # Last resort: exact 2-word pair with reasonable confidence.
    for ri in range(max(0, len(b) - 1)):
        for pi in range(max_source_skip + 1):
            if pi + 1 >= len(a):
                continue
            if a[pi] == b[ri] and a[pi + 1] == b[ri + 1]:
                c1 = float(recognized[ri].get('confidence', 0.0) or 0.0)
                c2 = float(recognized[ri + 1].get('confidence', 0.0) or 0.0)
                if (c1 + c2) / 2 >= 0.20:
                    return pi, ri

    return None


def interpolate_unmatched(rows: list[dict]) -> list[dict]:
    known = [i for i, row in enumerate(rows) if row.get('start_ms') is not None]
    if not known:
        return rows

    first_known = known[0]

    # Only recover a tiny missing prefix immediately before the real first
    # acoustic phrase. Never spread lyrics backwards through an instrumental intro.
    if 0 < first_known <= 3:
        anchor = int(rows[first_known]['start_ms'])
        step = 190
        base = max(0, anchor - first_known * step)
        for i in range(first_known):
            start = base + i * step
            rows[i].update(
                start_ms=start,
                end_ms=min(anchor, start + 150),
                confidence=0.12,
                language=None,
            )

    known = [i for i, row in enumerate(rows) if row.get('start_ms') is not None]

    for i, row in enumerate(rows):
        if row.get('start_ms') is not None:
            continue

        left = max((k for k in known if k < i), default=None)
        right = min((k for k in known if k > i), default=None)

        if left is None:
            continue

        if right is not None:
            left_end = int(rows[left]['end_ms'])
            right_start = int(rows[right]['start_ms'])
            ratio = (i - left) / max(1, right - left)
            t = int(round(left_end + (right_start - left_end) * ratio))
            row.update(start_ms=t, end_ms=t + 120, confidence=0.30)
        else:
            t = int(rows[left]['end_ms']) + max(80, (i - left - 1) * 180)
            row.update(start_ms=t, end_ms=t + 160, confidence=0.20)

    return rows


def align_provided_text(provided: list[dict], recognized: list[dict]) -> list[dict]:
    rows = [
        dict(row, start_ms=None, end_ms=None, confidence=0.0, language=None)
        for row in provided
    ]

    anchor = _first_acoustic_anchor(provided, recognized)
    if anchor is None:
        raise RuntimeError('No reliable local lyric/audio anchor found')

    source_start, recognized_start = anchor

    # Align only from the first real acoustic phrase onward. This prevents
    # SequenceMatcher from selecting a later repeated chorus while ignoring the
    # beginning of the song.
    a = [row['norm'] for row in provided[source_start:]]
    b = [row['norm'] for row in recognized[recognized_start:]]
    matcher = difflib.SequenceMatcher(a=a, b=b, autojunk=False)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        abs_i1 = source_start + i1
        abs_j1 = recognized_start + j1

        if tag == 'equal':
            for off in range(i2 - i1):
                src = recognized[abs_j1 + off]
                rows[abs_i1 + off].update(
                    start_ms=src['start_ms'],
                    end_ms=src['end_ms'],
                    confidence=src.get('confidence', 0.0),
                    language=src.get('language'),
                )

        elif tag == 'replace':
            n = min(i2 - i1, j2 - j1)
            for off in range(n):
                pi = abs_i1 + off
                ri = abs_j1 + off
                sim = _token_similarity(provided[pi]['norm'], recognized[ri]['norm'])
                conf = float(recognized[ri].get('confidence', 0.0) or 0.0)

                # Fuzzy replacements are accepted only when they are genuinely
                # similar words. No arbitrary positional replacement anchors.
                if sim < 0.82 or conf < 0.30:
                    continue

                src = recognized[ri]
                rows[pi].update(
                    start_ms=src['start_ms'],
                    end_ms=src['end_ms'],
                    confidence=max(0.20, conf * 0.75),
                    language=src.get('language'),
                )

    return interpolate_unmatched(rows)
"""

start = py.find('def interpolate_unmatched(rows: list[dict]) -> list[dict]:')
align = py.find('def align_provided_text(provided: list[dict], recognized: list[dict]) -> list[dict]:')
main = py.find('\ndef main() -> None:', align)
if start < 0 or align < 0 or main < 0:
    raise SystemExit('lyrics alignment block not found')
py = py[:start] + alignment_block.rstrip() + '\n' + py[main + 1:]
save(p, py)

# ----------------------------------------------------------------------
# 2. LyricsLab sections come from the editable source declarations.
# ----------------------------------------------------------------------
p, js = load('public/assets/js/lyricslab-r37.js')

section_start = js.find(
    "const panel=root.closest('section'),title=panel?.querySelector('.chordslab-prompter-head h2'),sections=[];"
)
section_end = js.find(
    "\n\nconst header=root.querySelector('.chordslab-prompter-head');",
    section_start,
)
if section_start < 0 or section_end < 0:
    raise SystemExit('LyricsLab section navigation block not found')

section_js = r"""const panel=root.closest('section'),title=panel?.querySelector('.chordslab-prompter-head h2');
const sourceBox=document.querySelector('[data-lyrics-source]');

function declaredSections(text){
 const result=[];
 String(text||'').replace(/\r\n?/g,'\n').split('\n').forEach(line=>{
   const s=line.trim();
   if(!s)return;
   let m=/^\[([^\[\]\r\n]{1,120})\]$/.exec(s);
   if(!m)m=/^([^\r\n:]{1,120}):$/.exec(s);
   if(m&&m[1].trim())result.push({label:m[1].trim(),start:null});
 });
 return result;
}

function nextBeatAtOrAfter(sec){
 const ms=Math.max(0,Number(sec||0)*1000);
 for(const b of beats){
   if(Number(b.start_ms)>=ms)return Number(b.start_ms)/1000;
 }
 return Number(sec||0);
}

function buildSections(){
 const declared=declaredSections(sourceBox?.value||'');
 if(!declared.length)return[];

 // Timed section transitions carried by anchored lyric words.
 const transitions=[];
 let previous='';
 words.forEach((w,i)=>{
   const label=String(payload(w).section_label||'').trim();
   if(label&&label!==previous){
     transitions.push({label,start:Number(w.start_ms||0)/1000,index:i});
     previous=label;
   }
 });

 let cursor=0;

 declared.forEach((section,index)=>{
   // Match in declaration order, not globally by label. Repeated labels remain valid.
   for(let j=cursor;j<transitions.length;j++){
     if(transitions[j].label===section.label){
       section.start=transitions[j].start;
       cursor=j+1;
       break;
     }
   }

   // A declared instrumental section has no lyric event. Infer only its temporal
   // boundary; never invent the section itself.
   if(section.start==null){
     if(index===0){
       section.start=0;
     }else{
       const previousSection=declared[index-1];
       let previousEnd=Number(previousSection.start||0);

       for(const w of words){
         if(String(payload(w).section_label||'').trim()===previousSection.label){
           previousEnd=Math.max(
             previousEnd,
             Number(w.end_ms||w.start_ms||0)/1000
           );
         }
       }

       section.start=nextBeatAtOrAfter(previousEnd);
     }
   }
 });

 for(let i=1;i<declared.length;i++){
   declared[i].start=Math.max(
     Number(declared[i-1].start||0),
     Number(declared[i].start||0)
   );
 }

 return declared;
}

let sections=buildSections();

function renderSectionNav(){
 if(!title)return;

 let nav=panel.querySelector('[data-section-nav]');
 if(!nav){
   nav=document.createElement('div');
   nav.className='lyrics-section-nav';
   nav.dataset.sectionNav='';
   title.insertAdjacentElement('afterend',nav);
 }

 nav.innerHTML='';

 sections.forEach((s,i)=>{
   const b=document.createElement('button');
   b.type='button';
   b.className='lyrics-section-chip';
   b.dataset.sectionIndex=String(i);
   b.textContent=s.label;
   b.onclick=()=>{
     renderAt(s.start,true);
     document.querySelector('[data-stem-mixer]')?.dispatchEvent(
       new CustomEvent('ezscore:request-seek',{detail:{time:s.start}})
     );
   };
   nav.appendChild(b);
 });
}

renderSectionNav();
"""

js = js[:section_start] + section_js + js[section_end:]

source_listener = (
    "source?.addEventListener('input',()=>{if(state)state.textContent='Modifié…';"
    "clearTimeout(timer);timer=setTimeout(save,450)});"
)
source_listener_new = """source?.addEventListener('input',()=>{
 if(state)state.textContent='Modifié…';
 clearTimeout(timer);
 timer=setTimeout(save,450);
 sections=buildSections();
 renderSectionNav();
 renderAt(lastTime,true);
});"""
if source_listener in js:
    js = js.replace(source_listener, source_listener_new, 1)
else:
    raise SystemExit('Lyrics source autosave listener not found')

save(p, js)

# ----------------------------------------------------------------------
# 3. Keep R38.3 player fix, only bump cache to force the new JS.
#    Progress polling is deliberately untouched.
# ----------------------------------------------------------------------
p, twig = load('templates/song/lyricslab.html.twig')
twig = re.sub(
    r'/assets/js/lyricslab-r37\.js\?v=[^"\']+',
    '/assets/js/lyricslab-r37.js?v=20260928r38_4',
    twig,
)
save(p, twig)

print('R38_4_INSTALL_OK')
