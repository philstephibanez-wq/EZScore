#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv)>1 else r"H:\EZScore_v1").resolve()
HERE = Path(__file__).resolve().parent.parent
ANALYSIS = ROOT/"analysis/lyrics_timeline_analysis.py"
RESULT = ROOT/"src/Service/LyricsTimelineResultService.php"
JS = ROOT/"public/assets/js/lyricslab-r37.js"
TWIG = ROOT/"templates/song/lyricslab.html.twig"
PATCH_FILE = HERE/"patches/r38_17a_python_override.py.txt"
MARK = "# R38.17A acoustic syllabic alignment correction"

def main():
    for p in (ANALYSIS, RESULT, JS, TWIG, PATCH_FILE):
        if not p.is_file():
            raise RuntimeError(f"Missing prerequisite: {p}")

    analysis = ANALYSIS.read_text(encoding="utf-8")
    result = RESULT.read_text(encoding="utf-8")
    js = JS.read_text(encoding="utf-8")
    twig = TWIG.read_text(encoding="utf-8")
    override = PATCH_FILE.read_text(encoding="utf-8").rstrip() + "\n"

    if MARK not in analysis:
        anchor = "\ndef main() -> None:\n"
        if anchor not in analysis:
            raise RuntimeError("lyrics_timeline_analysis.py main anchor not found")
        analysis = analysis.replace(anchor, "\n" + override + anchor, 1)

    old = """    rows = align_provided_text(provided, words, vocal_onset_ms)
    anchored_rows = [row for row in rows if row.get('start_ms') is not None]
"""
    new = """    rows = align_provided_text(provided, words, vocal_onset_ms)
    _r3817_refine_syllable_nuclei(rows, args.vocal_audio)
    anchored_rows = [row for row in rows if row.get('start_ms') is not None]
"""
    if old in analysis:
        analysis = analysis.replace(old, new, 1)
    elif "_r3817_refine_syllable_nuclei(rows, args.vocal_audio)" not in analysis:
        raise RuntimeError("nucleus refinement anchor not found")

    analysis = analysis.replace(
        "'version': 'r38.13-canonical-grid-syllabic-timeline',",
        "'version': 'r38.17a-acoustic-syllabic-alignment',",
        1,
    )

    old = """        'words': payload_words,
    })
"""
    new = """        'words': payload_words,
        'timing_diagnostics': (rows[0].get('_r3817_timing') if rows else None),
    })
"""
    if old in analysis and "'timing_diagnostics':" not in analysis:
        analysis = analysis.replace(old, new, 1)

    old = """                'confidence'=>isset($word['confidence'])?(float)$word['confidence']:null,
                'analysis_version'=>(string)($result['version']??'r36.0'),
"""
    new = """                'confidence'=>isset($word['confidence'])?(float)$word['confidence']:null,
                'alignment'=>isset($word['alignment'])&&is_string($word['alignment'])?$word['alignment']:null,
                'recognized_index'=>isset($word['recognized_index'])?(int)$word['recognized_index']:null,
                'syllables'=>isset($word['syllables'])&&is_array($word['syllables'])?$word['syllables']:[],
                'cue_ms'=>isset($word['syllables'][0]['nucleus_ms'])?(int)$word['syllables'][0]['nucleus_ms']:$start,
                'analysis_version'=>(string)($result['version']??'r36.0'),
"""
    if old in result:
        result = result.replace(old, new, 1)
    elif "'cue_ms'=>" not in result:
        raise RuntimeError("LyricsTimelineResultService payload anchor not found")

    old = "const words=parse(root.dataset.lyrics).sort((a,b)=>Number(a.start_ms)-Number(b.start_ms));"
    new = """const wordCueMs=w=>{const p=payload(w),s=Array.isArray(p.syllables)?p.syllables:[];const n=Number(p.cue_ms??s[0]?.nucleus_ms??w.start_ms??0);return Number.isFinite(n)?n:Number(w.start_ms||0)};
const words=parse(root.dataset.lyrics).sort((a,b)=>wordCueMs(a)-wordCueMs(b));"""
    if old in js:
        js = js.replace(old, new, 1)
    elif "const wordCueMs=" not in js:
        raise RuntimeError("renderer words anchor not found")

    old = "function activeWord(ms){let i=-1;for(let k=0;k<words.length;k++){if(Number(words[k].start_ms)<=ms)i=k;else break}return i}"
    new = "function activeWord(ms){let i=-1;for(let k=0;k<words.length;k++){if(wordCueMs(words[k])<=ms)i=k;else break}return i}"
    if old in js:
        js = js.replace(old, new, 1)
    elif "if(wordCueMs(words[k])<=ms)" not in js:
        raise RuntimeError("renderer activeWord anchor not found")

    old = "e.dataset.rawX=String(rawMetric(Number(w.start_ms||0)/1000));"
    new = "e.dataset.rawX=String(rawMetric(wordCueMs(w)/1000));"
    if old in js:
        js = js.replace(old, new, 1)
    elif "rawMetric(wordCueMs(w)/1000)" not in js:
        raise RuntimeError("renderer word-position anchor not found")

    js = js.replace(
        "const end=Math.max(starts.at(-1)||0,Number(words.at(-1)?.end_ms||0)/1000);",
        "const end=Math.max(starts.at(-1)||0,Number(words.at(-1)?.end_ms||wordCueMs(words.at(-1)||{}))/1000);",
        1,
    )

    old = '<script src="/assets/js/lyricslab-r37.js?v=20260928r38_13c"></script>'
    new = '<script src="/assets/js/lyricslab-r37.js?v=20260929r38_17a"></script>'
    if old in twig:
        twig = twig.replace(old, new, 1)
    elif "lyricslab-r37.js?v=20260929r38_17a" not in twig:
        raise RuntimeError("LyricsLab JS cache-bust anchor not found")

    # Validate all anchors before writing anything.
    required_analysis = [
        MARK,
        "_r3817_effective_t0",
        "_r3817_refine_syllable_nuclei(rows, args.vocal_audio)",
        "'version': 'r38.17a-acoustic-syllabic-alignment'",
    ]
    for marker in required_analysis:
        if marker not in analysis:
            raise RuntimeError(f"validation failed: {marker}")
    if "'cue_ms'=>" not in result:
        raise RuntimeError("validation failed: cue_ms")
    if "const wordCueMs=" not in js:
        raise RuntimeError("validation failed: wordCueMs")

    ANALYSIS.write_text(analysis, encoding="utf-8", newline="\n")
    RESULT.write_text(result, encoding="utf-8", newline="\n")
    JS.write_text(js, encoding="utf-8", newline="\n")
    TWIG.write_text(twig, encoding="utf-8", newline="\n")

    print("R38_17A_ACOUSTIC_SYLLABIC_ALIGNMENT_REPAIR_INSTALL_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
