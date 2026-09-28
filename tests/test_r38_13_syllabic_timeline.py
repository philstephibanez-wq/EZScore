#!/usr/bin/env python3
import importlib.util,sys
from pathlib import Path
root=Path(sys.argv[1] if len(sys.argv)>1 else r"H:\EZScore_v1")
p=root/'analysis/lyrics_timeline_analysis.py'
spec=importlib.util.spec_from_file_location('m',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
assert m._r3813_syllabify_french(':')==[]
assert m._r3813_syllabify_french('!')==[]
assert len(m._r3813_syllabify_french('Aline'))>=2
assert len(m._r3813_syllabify_french('dessiné'))>=2
src=m.source_tokens("Et j'ai crié, crié : Aline !\n")
assert not any(r['text'] in {':','!'} for r in src),src
provided=m.source_tokens("J'avais dessiné sur le sable son doux visage")
recognized=[{'text':'visage','norm':'visage','start_ms':10000,'end_ms':10500,'confidence':.99,'language':'fr'}]
rows=m.align_provided_text(provided,recognized,1000)
assert rows[0]['start_ms']==1000
flat=[s for r in rows for s in r.get('syllables',[])]
assert flat and flat[0]['start_ms']==1000
starts=[s['start_ms'] for s in flat]
assert all(b>a for a,b in zip(starts,starts[1:])),starts
assert all(s['start_ms']<=s['nucleus_ms']<=s['end_ms'] for s in flat)
for r in rows:
    syl=r.get('syllables') or []
    if syl:
        assert r['start_ms']==syl[0]['start_ms']; assert r['end_ms']==syl[-1]['end_ms']
gaps=[rows[i+1]['start_ms']-rows[i]['start_ms'] for i in range(len(rows)-1)]
assert len(set(gaps[:min(6,len(gaps))]))>1,gaps
print('R38_13_SYLLABIC_TIMELINE_OK')
