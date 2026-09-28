from pathlib import Path
import importlib.util, sys

root=Path(sys.argv[1] if len(sys.argv)>1 else ".").resolve()
p=root/"analysis"/"lyrics_timeline_analysis.py"
spec=importlib.util.spec_from_file_location("lyrics_timeline_analysis",p)
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

def row(text,norm):
    return {"text":text,"norm":norm,"section_label":"Couplet 1","section_type":"verse","line_break_after":False}

provided=[
 row("Je","je"), row("vous","vous"), row("parle","parle"), row("d","d"), row("'un","'un"),
 row("temps","temps"), row("Que","que"), row("les","les"), row("moins","moins"), row("lilas","lilas"),
]
recognized=[
 {"text":"j","norm":"j","start_ms":15880,"end_ms":16100,"confidence":.35,"language":"fr"},
 {"text":"veux","norm":"veux","start_ms":16450,"end_ms":16720,"confidence":.40,"language":"fr"},
 {"text":"parler","norm":"parler","start_ms":17020,"end_ms":17380,"confidence":.55,"language":"fr"},
 {"text":"d'un","norm":"d'un","start_ms":17880,"end_ms":18200,"confidence":.88,"language":"fr"},
 {"text":"temps","norm":"temps","start_ms":18650,"end_ms":19100,"confidence":.96,"language":"fr"},
 {"text":"que","norm":"que","start_ms":19720,"end_ms":19980,"confidence":.97,"language":"fr"},
 {"text":"les","norm":"les","start_ms":20250,"end_ms":20400,"confidence":.99,"language":"fr"},
 {"text":"moins","norm":"moins","start_ms":20750,"end_ms":21100,"confidence":.98,"language":"fr"},
 {"text":"lilas","norm":"lilas","start_ms":22600,"end_ms":23000,"confidence":.99,"language":"fr"},
]

rows=mod.align_provided_text(provided,recognized,15890)
starts=[r["start_ms"] for r in rows]
assert starts[0]==15890, starts
assert all(starts[i] < starts[i+1] for i in range(len(starts)-1)), starts
deltas=[starts[i+1]-starts[i] for i in range(min(6,len(starts)-1))]
assert len(set(deltas)) > 2, deltas
assert starts[-1] >= 22000, starts
assert rows[0].get("alignment")=="acoustic_trigger", rows[0]
print("R38_10_SEQUENTIAL_TIMELINE_OK")
