from pathlib import Path
import importlib.util,sys
root=Path(sys.argv[1] if len(sys.argv)>1 else '.').resolve(); p=root/'analysis'/'lyrics_timeline_analysis.py'
spec=importlib.util.spec_from_file_location('lyrics_timeline_analysis',p); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
provided=[{'text':'Je','norm':'je','section_label':'Couplet 1'},{'text':'vous','norm':'vous','section_label':'Couplet 1'},{'text':'parle','norm':'parle','section_label':'Couplet 1'}]
recognized=[{'text':'foo','norm':'foo','start_ms':12000,'end_ms':12100,'confidence':.9,'language':'fr'},{'text':'vous','norm':'vous','start_ms':12400,'end_ms':12600,'confidence':.9,'language':'fr'},{'text':'parle','norm':'parle','start_ms':12800,'end_ms':13000,'confidence':.9,'language':'fr'},{'text':'Je','norm':'je','start_ms':125000,'end_ms':125200,'confidence':.99,'language':'fr'}]
rows=mod.align_provided_text(provided,recognized,12340)
assert rows[0]['start_ms']==12340,rows
assert rows[1]['start_ms']>=rows[0]['start_ms'] and rows[2]['start_ms']>=rows[1]['start_ms'],rows
assert rows[0]['start_ms']<20000,rows
print('R38_7A_MONOTONIC_OK')
