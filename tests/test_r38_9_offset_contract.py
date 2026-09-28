from pathlib import Path
import importlib.util,sys
root=Path(sys.argv[1] if len(sys.argv)>1 else '.').resolve()
p=root/'analysis'/'lyrics_timeline_analysis.py'
spec=importlib.util.spec_from_file_location('lyrics_timeline_analysis',p)
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
provided=[{'text':'Je','norm':'je','section_label':'Couplet 1'},{'text':'vous','norm':'vous','section_label':'Couplet 1'},{'text':'parle','norm':'parle','section_label':'Couplet 1'},{'text':'temps','norm':'temps','section_label':'Couplet 1'}]
recognized=[{'text':'Je','norm':'je','start_ms':0,'end_ms':150,'confidence':.95,'language':'fr'},{'text':'vous','norm':'vous','start_ms':350,'end_ms':500,'confidence':.95,'language':'fr'},{'text':'parle','norm':'parle','start_ms':700,'end_ms':900,'confidence':.95,'language':'fr'},{'text':'temps','norm':'temps','start_ms':1300,'end_ms':1500,'confidence':.95,'language':'fr'}]
rows=mod.align_provided_text(provided,recognized,12340)
assert [r['start_ms'] for r in rows]==[12340,12690,13040,13640],rows
assert rows[0]['timeline_offset_ms']==12340,rows
print('R38_9_OFFSET_CONTRACT_OK')
