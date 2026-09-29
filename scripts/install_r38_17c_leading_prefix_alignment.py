#!/usr/bin/env python3
from __future__ import annotations
import re, sys
from pathlib import Path

ROOT=Path(sys.argv[1] if len(sys.argv)>1 else r"H:\EZScore_v1").resolve()
HERE=Path(__file__).resolve().parent.parent
ANALYSIS=ROOT/"analysis/lyrics_timeline_analysis.py"
RESULT=ROOT/"src/Service/LyricsTimelineResultService.php"
JS=ROOT/"public/assets/js/lyricslab-r37.js"
TWIG=ROOT/"templates/song/lyricslab.html.twig"
PATCH=HERE/"patches/r38_17c_prefix_override.py.txt"
MARK="# R38.17C — leading-prefix-only lyric repair"

def main():
    for p in (ANALYSIS,RESULT,JS,TWIG,PATCH):
        if not p.is_file():
            raise RuntimeError(f"Missing prerequisite: {p}")

    analysis=ANALYSIS.read_text(encoding="utf-8")
    result=RESULT.read_text(encoding="utf-8")
    js=JS.read_text(encoding="utf-8")
    twig=TWIG.read_text(encoding="utf-8")
    override=PATCH.read_text(encoding="utf-8").rstrip()+"\n"

    if MARK not in analysis:
        anchor="\ndef main() -> None:\n"
        if anchor not in analysis:
            raise RuntimeError("lyrics_timeline_analysis.py main anchor not found")
        analysis=analysis.replace(anchor,"\n"+override+anchor,1)

    # Normalize the main align block whether R38.17B is already installed locally or not.
    pattern=re.compile(
        r"""    rows = align_provided_text\(provided, words, vocal_onset_ms\)\n(?:    _r3817_refine_syllable_nuclei\(rows, args\.vocal_audio\)\n)?    anchored_rows = \[row for row in rows if row\.get\('start_ms'\) is not None\]\n"""
    )
    replacement="""    rows = align_provided_text(provided, words, vocal_onset_ms)
    prefix_diagnostics = _r3817c_repair_leading_prefix(
        rows, words, vocal_onset_ms, args.vocal_audio
    )
    _r3817c_refine_syllable_nuclei(rows, args.vocal_audio)
    anchored_rows = [row for row in rows if row.get('start_ms') is not None]
"""
    analysis,n=pattern.subn(replacement,analysis,count=1)
    if n==0 and "prefix_diagnostics = _r3817c_repair_leading_prefix(" not in analysis:
        raise RuntimeError("R38.17C main alignment anchor not found")

    # Ensure current output version.
    analysis=re.sub(
        r"'version': 'r38\.(?:13-canonical-grid-syllabic-timeline|17a-acoustic-syllabic-alignment)',",
        "'version': 'r38.17c-leading-prefix-acoustic-repair',",
        analysis,
        count=1,
    )

    # Add prefix diagnostic without depending on earlier R38.17 deliveries.
    if "'prefix_repair': prefix_diagnostics," not in analysis:
        old="""        'words': payload_words,
"""
        if old not in analysis:
            raise RuntimeError("Lyrics JSON words anchor not found")
        analysis=analysis.replace(old,old+"        'prefix_repair': prefix_diagnostics,\n",1)

    # Persist syllables/cue if not already present locally.
    old_result="""                'confidence'=>isset($word['confidence'])?(float)$word['confidence']:null,
                'analysis_version'=>(string)($result['version']??'r36.0'),
"""
    new_result="""                'confidence'=>isset($word['confidence'])?(float)$word['confidence']:null,
                'alignment'=>isset($word['alignment'])&&is_string($word['alignment'])?$word['alignment']:null,
                'recognized_index'=>isset($word['recognized_index'])?(int)$word['recognized_index']:null,
                'syllables'=>isset($word['syllables'])&&is_array($word['syllables'])?$word['syllables']:[],
                'cue_ms'=>isset($word['syllables'][0]['nucleus_ms'])?(int)$word['syllables'][0]['nucleus_ms']:$start,
                'analysis_version'=>(string)($result['version']??'r36.0'),
"""
    if old_result in result:
        result=result.replace(old_result,new_result,1)
    elif "'cue_ms'=>" not in result:
        raise RuntimeError("LyricsTimelineResultService payload anchor not found")

    # Word remains the visual unit; cue comes from its first syllable nucleus.
    if "const wordCueMs=" not in js:
        old="const words=parse(root.dataset.lyrics).sort((a,b)=>Number(a.start_ms)-Number(b.start_ms));"
        new="""const wordCueMs=w=>{const p=payload(w),s=Array.isArray(p.syllables)?p.syllables:[];const n=Number(p.cue_ms??s[0]?.nucleus_ms??w.start_ms??0);return Number.isFinite(n)?n:Number(w.start_ms||0)};
const words=parse(root.dataset.lyrics).sort((a,b)=>wordCueMs(a)-wordCueMs(b));"""
        if old not in js:
            raise RuntimeError("Lyrics renderer words anchor not found")
        js=js.replace(old,new,1)

    old="function activeWord(ms){let i=-1;for(let k=0;k<words.length;k++){if(Number(words[k].start_ms)<=ms)i=k;else break}return i}"
    if old in js:
        js=js.replace(old,"function activeWord(ms){let i=-1;for(let k=0;k<words.length;k++){if(wordCueMs(words[k])<=ms)i=k;else break}return i}",1)

    old="e.dataset.rawX=String(rawMetric(Number(w.start_ms||0)/1000));"
    if old in js:
        js=js.replace(old,"e.dataset.rawX=String(rawMetric(wordCueMs(w)/1000));",1)

    # Cache-bust from either baseline or R38.17A/B local state.
    twig=re.sub(
        r'<script src="/assets/js/lyricslab-r37\.js\?v=[^"]+"></script>',
        '<script src="/assets/js/lyricslab-r37.js?v=20260929r38_17c"></script>',
        twig,
        count=1,
    )

    # Validate before writes.
    for marker in (
        MARK,
        "prefix_diagnostics = _r3817c_repair_leading_prefix(",
        "'version': 'r38.17c-leading-prefix-acoustic-repair'",
    ):
        if marker not in analysis:
            raise RuntimeError(f"R38.17C validation failed: {marker}")
    if "'cue_ms'=>" not in result:
        raise RuntimeError("R38.17C validation failed: cue_ms")
    if "const wordCueMs=" not in js:
        raise RuntimeError("R38.17C validation failed: wordCueMs")
    if "R38.13 canonical ChordsLab projection." not in js:
        raise RuntimeError("R38.17C refuses to continue: harmonic projection marker missing")

    ANALYSIS.write_text(analysis,encoding="utf-8",newline="\n")
    RESULT.write_text(result,encoding="utf-8",newline="\n")
    JS.write_text(js,encoding="utf-8",newline="\n")
    TWIG.write_text(twig,encoding="utf-8",newline="\n")

    print("R38_17C_LEADING_PREFIX_ALIGNMENT_INSTALL_OK")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
