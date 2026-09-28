#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else r"H:\EZScore_v1").resolve()
JS = ROOT / "public" / "assets" / "js" / "lyricslab-r37.js"
TWIG = ROOT / "templates" / "song" / "lyricslab.html.twig"

NEW_PROJECTION = r"""function buildCanonicalProjection(inputBeats){
 // R38.13b: time-signature agnostic continuous projection.
 // The display measure is representation only: never rebuild/synthesize timing
 // from stale source measure_index / beat_index values.
 const timeSignature=String(root.dataset.timeSignature||'4/4');
 const beatsPerMeasure=Math.max(1,Number(timeSignature.split('/')[0])||4);
 const ordered=(inputBeats||[])
  .map((event,sourceSeq)=>({event,sourceSeq,startMs:Number(event.start_ms??0)}))
  .filter(row=>Number.isFinite(row.startMs))
  .sort((a,b)=>a.startMs-b.startMs||a.sourceSeq-b.sourceSeq);

 const projectionBeats=ordered.map((row,displaySeq)=>{
  const displayMeasureIndex=Math.floor(displaySeq/beatsPerMeasure);
  const displayBeatIndex=displaySeq%beatsPerMeasure;
  return {
   ...row.event,
   display_seq:displaySeq,
   display_measure_index:displayMeasureIndex,
   display_beat_index:displayBeatIndex,
   display_start_ms:row.startMs,
   displaySynthetic:false
  };
 });

 const projectionMeasures=[];
 for(let first=0;first<projectionBeats.length;first+=beatsPerMeasure){
  projectionMeasures.push({
   source_measure_index:Number(projectionBeats[first]?.measure_index??projectionMeasures.length),
   first_display_beat_index:first,
   beats_per_measure:beatsPerMeasure
  });
 }

 return {beats:projectionBeats,measures:projectionMeasures,beatsPerMeasure};
}"""

def main() -> int:
    if not JS.is_file():
        raise SystemExit(f"Missing: {JS}")
    if not TWIG.is_file():
        raise SystemExit(f"Missing: {TWIG}")

    src = JS.read_text(encoding="utf-8")

    if "R38.13b: time-signature agnostic continuous projection" in src:
        print("R38_13B_JS_ALREADY_INSTALLED")
    else:
        if "R38.13 canonical ChordsLab projection" not in src:
            raise RuntimeError("R38.13 projection not found; refusing to patch an unexpected LyricsLab")

        pattern = re.compile(
            r"function buildCanonicalProjection\(inputBeats\)\{.*?\n\}"
            r"(?=\nconst canonicalProjection=buildCanonicalProjection\(sourceBeats\);)",
            re.S,
        )
        src, count = pattern.subn(NEW_PROJECTION, src, count=1)
        if count != 1:
            raise RuntimeError(f"canonical projection replacement: expected 1, found {count}")

        # At a display-measure boundary, chord repetition must follow the DISPLAY
        # measure, never stale source beat_index.
        old = "else if(bn===0)text=shown(ac?.effective||ac?.original||'.');const displayBeatIndex=Number(b.display_beat_index??bn),"
        new = "const displayBeatIndex=Number(b.display_beat_index??bn);if(!ex&&(ac?.effective||ac?.original||'')!=='.'&&displayBeatIndex===0)text=shown(ac?.effective||ac?.original||'.');"
        if old in src:
            src = src.replace(old, new, 1)
        else:
            # Support a slightly reformatted local R38.13 while staying strict.
            old2 = "else if(bn===0)text=shown(ac?.effective||ac?.original||'.');const displayBeatIndex=Number(b.display_beat_index??bn)"
            new2 = "const displayBeatIndex=Number(b.display_beat_index??bn);if(!ex&&(ac?.effective||ac?.original||'')!=='.'&&displayBeatIndex===0)text=shown(ac?.effective||ac?.original||'.')"
            if old2 in src:
                src = src.replace(old2, new2, 1)
            else:
                raise RuntimeError("buildChords display-boundary anchor not found")

        JS.write_text(src, encoding="utf-8")
        print("R38_13B_JS_OK")

    twig = TWIG.read_text(encoding="utf-8")
    if "20260928r38_13b" not in twig:
        twig, count = re.subn(
            r"(/assets/js/lyricslab-r37\.js\?v=)[^\"']+",
            r"\g<1>20260928r38_13b",
            twig,
            count=1,
        )
        if count != 1:
            raise RuntimeError(f"Twig cache buster: expected 1, found {count}")
        TWIG.write_text(twig, encoding="utf-8")
        print("R38_13B_TWIG_OK")
    else:
        print("R38_13B_TWIG_ALREADY_INSTALLED")

    print("R38_13B_INSTALL_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
