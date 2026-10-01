#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT=Path(sys.argv[1] if len(sys.argv)>1 else r"H:\EZScore_v1").resolve()
TARGET=ROOT/"analysis/chord_timeline_analysis.py"
text=TARGET.read_text(encoding="utf-8-sig")

assert 'def detect_key_from_segments(segments,chroma_mean=None):' in text
assert 'lv-chordia-duration+chroma-tiebreak' in text
assert 'key,_,key_confidence,key_method=detect_key_from_segments(segments,chroma_mean)' in text
assert '"key_confidence":round(float(key_confidence),4)' in text
assert '"key_method":key_method' in text
assert '"version":"r41.0j-hq-key-from-chords"' in text

# Existing HQ chord pipeline must remain intact.
assert 'raw_segments=chord_recognition(' in text
assert 'chord_dict_name=CHORD_DICTIONARY' in text
assert 'def chord_for_interval(segments,start,end):' in text
assert 'def project_profile(level,segments,beat_times,bpm,phase,tempo):' in text
assert 'Legacy chroma chord decoder disabled' in text

# Import module without running CLI.
sys.path.insert(0,str(ROOT/"analysis"))
spec=importlib.util.spec_from_file_location("ezscore_r41j_key",TARGET)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def segs(items):
    out=[]
    t=0.0
    for chord,duration in items:
        out.append({"start":t,"end":t+duration,"chord":chord})
        t+=duration
    return out

# Relative-major ambiguity: harmonic minor dominant B7 must make E minor beat G major.
e_minor=segs([
    ("Em",10),("B7",8),("Em",10),("C",8),("G",8),("Am",8),("B7",8),("Em",10),
])
key,info,confidence,method=mod.detect_key_from_segments(e_minor,None)
assert key=="Em",(key,info,confidence,method)
assert method=="lv-chordia-duration+chroma-tiebreak"
assert confidence>0.10,confidence

# Major reference.
c_major=segs([
    ("C",10),("F",7),("G7",8),("C",10),("Am",5),("Dm",5),("G7",7),("C",10),
])
key,_,confidence,_=mod.detect_key_from_segments(c_major,None)
assert key=="C",(key,confidence)

# Another relative-major/minor case.
a_minor=segs([
    ("Am",10),("E7",8),("Am",10),("F",7),("C",7),("Dm",7),("E7",8),("Am",10),
])
key,_,confidence,_=mod.detect_key_from_segments(a_minor,None)
assert key=="Am",(key,confidence)

# Only the analysis file may be modified.
p=subprocess.run(
    ["git","diff","--name-only"],
    cwd=str(ROOT),
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    encoding="utf-8",
    errors="replace",
    check=True,
)
changed={x.strip() for x in p.stdout.splitlines() if x.strip()}
assert changed=={"analysis/chord_timeline_analysis.py"},sorted(changed)

subprocess.run([sys.executable,"-m","py_compile",str(TARGET)],check=True)
print("R41_0J2_HQ_SONG_KEY_CONTRACT_OK")
