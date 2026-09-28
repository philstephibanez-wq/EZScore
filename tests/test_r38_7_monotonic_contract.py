from pathlib import Path
import importlib.util
import sys

root=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parents[1]
path=root/'analysis'/'lyrics_timeline_analysis.py'
spec=importlib.util.spec_from_file_location('lyrics_r387',path)
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

provided=[{'text':w,'norm':mod.normalise_token(w),'line_break_after':False,'section_label':None,'section_type':None} for w in ['Je','vous','parle','dun','temps']]
recognized=[
 {'text':'Je','norm':'je','start_ms':83000,'end_ms':83200,'confidence':.99,'language':'fr'},
 {'text':'vous','norm':'vous','start_ms':83300,'end_ms':83500,'confidence':.99,'language':'fr'},
 {'text':'parle','norm':'parle','start_ms':83600,'end_ms':83900,'confidence':.99,'language':'fr'},
]
rows=mod.align_provided_text(provided,recognized,12340)
assert rows[0]['start_ms']==12340, rows[0]
assert all(rows[i]['start_ms']<=rows[i+1]['start_ms'] for i in range(len(rows)-1)), rows
assert rows[1]['start_ms'] < 83000, 'first source phrase was allowed to jump to the late repetition'
print('R38_7_MONOTONIC_CONTRACT_OK')
