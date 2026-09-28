#!/usr/bin/env python3
from pathlib import Path
import sys
repo = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()

def read(rel):
    p=repo/rel
    if not p.is_file(): raise SystemExit(f'ABSENT: {p}')
    return p,p.read_text(encoding='utf-8')
def write(p,text): p.write_text(text,encoding='utf-8',newline='\n')

p,js=read('public/assets/js/stems-mixer.js')
broken="    root.addEventListener('ezscore:request-seek', (event) => {\\n        const time=Math.max(0,Number(event.detail?.time||0));\\n        engine.seek(time);\\n        const duration=engine.duration();\\n        if(els.seek&&duration>0) els.seek.value=String(Math.round((time/duration)*1000));\\n    });\\n\\n    engine.addEventListener('statechange', (event) => {"
fixed="""    root.addEventListener('ezscore:request-seek', (event) => {
        const time = Math.max(0, Number(event.detail?.time || 0));
        engine.seek(time);
        const duration = engine.duration();
        if (els.seek && duration > 0) {
            els.seek.value = String(Math.round((time / duration) * 1000));
        }
    });

    engine.addEventListener('statechange', (event) => {"""
if broken in js: js=js.replace(broken,fixed,1)
if "quickVolume: q('[data-chordslab-quick-volume]')" not in js:
    a="        reset: q('[data-master-fx-reset]'),\n    };"
    b="        reset: q('[data-master-fx-reset]'),\n        quickVolume: q('[data-chordslab-quick-volume]'),\n        quickVolumeOut: q('[data-chordslab-quick-volume-output]'),\n    };"
    if a not in js: raise SystemExit('stems-mixer els anchor not found')
    js=js.replace(a,b,1)
if 'const syncQuickVolume = () =>' not in js:
    a="    const syncMasterOutputs = () => {\n        if (els.volume && els.volumeOut) {\n            els.volumeOut.textContent = `${Math.round(Number(els.volume.value) * 100)}%`;\n        }"
    b="    const syncQuickVolume = () => {\n        if (!els.volume || !els.quickVolume) return;\n        els.quickVolume.value = els.volume.value;\n        if (els.quickVolumeOut) {\n            els.quickVolumeOut.textContent = `${Math.round(Number(els.volume.value) * 100)}%`;\n        }\n    };\n\n    const syncMasterOutputs = () => {\n        if (els.volume && els.volumeOut) {\n            els.volumeOut.textContent = `${Math.round(Number(els.volume.value) * 100)}%`;\n        }\n        syncQuickVolume();"
    if a not in js: raise SystemExit('syncMasterOutputs anchor not found')
    js=js.replace(a,b,1)
if "els.quickVolume?.addEventListener('input'" not in js:
    a="    els.volume?.addEventListener('input', () => {\n        engine.setMasterVolume(Number(els.volume.value));\n        syncMasterOutputs();\n        scheduleSave();\n    });"
    b="    els.volume?.addEventListener('input', () => {\n        engine.setMasterVolume(Number(els.volume.value));\n        syncMasterOutputs();\n        scheduleSave();\n    });\n    els.quickVolume?.addEventListener('input', () => {\n        const value = Number(els.quickVolume.value);\n        if (els.volume) els.volume.value = String(value);\n        engine.setMasterVolume(value);\n        syncMasterOutputs();\n        scheduleSave();\n    });"
    if a not in js: raise SystemExit('master volume listener anchor not found')
    js=js.replace(a,b,1)
write(p,js)

p,lyrics=read('public/assets/js/lyricslab-r37.js')
a="let showDiagram=Boolean(toggle?.checked);toggle?.addEventListener('change',()=>{showDiagram=toggle.checked;renderAt(lastTime,true)});"
b="const diagramStorageKey=`ezscore:lyricslab:diagram:${location.pathname}`;\nlet showDiagram=false;\ntry{showDiagram=localStorage.getItem(diagramStorageKey)==='1'}catch(_){}\nif(toggle)toggle.checked=showDiagram;\ntoggle?.addEventListener('change',()=>{\n showDiagram=toggle.checked;\n try{localStorage.setItem(diagramStorageKey,showDiagram?'1':'0')}catch(_){}\n renderAt(lastTime,true)\n});"
if a in lyrics: lyrics=lyrics.replace(a,b,1)
elif 'diagramStorageKey=' not in lyrics: raise SystemExit('LyricsLab diagram toggle anchor not found')
a="b.onclick=()=>document.querySelector('[data-stem-mixer]')?.dispatchEvent(new CustomEvent('ezscore:request-seek',{detail:{time:s.start}}));"
b="b.onclick=()=>{renderAt(s.start,true);document.querySelector('[data-stem-mixer]')?.dispatchEvent(new CustomEvent('ezscore:request-seek',{detail:{time:s.start}}))};"
if a in lyrics: lyrics=lyrics.replace(a,b,1)
write(p,lyrics)

p,worker=read('worker_app/lyrics_worker_r37.py')
a='''    audio=paths.get("lead_vocals")
    if not audio or not Path(str(audio)).is_file():
        audio=paths.get("source")
    if not audio or not Path(str(audio)).is_file():
        raise RuntimeError("lyrics_audio_source_missing")
'''
b='''    # R38.3: extraction may use the isolated lead vocal, but alignment must use
    # the original source so timestamps share the exact playback clock.
    if mode=="align":
        audio=paths.get("source")
        audio_kind="source"
    else:
        audio=paths.get("lead_vocals")
        audio_kind="lead_vocals"
        if not audio or not Path(str(audio)).is_file():
            audio=paths.get("source")
            audio_kind="source"
    if not audio or not Path(str(audio)).is_file():
        raise RuntimeError("lyrics_audio_source_missing")
    engine.log(f"Audio Lyrics ({mode}): {audio_kind} -> {audio}")
'''
if a in worker: worker=worker.replace(a,b,1)
elif 'Audio Lyrics ({mode})' not in worker: raise SystemExit('Lyrics worker audio selection anchor not found')
write(p,worker)

p,twig=read('templates/song/lyricslab.html.twig')
twig=twig.replace('<script src="/assets/js/stems-mixer.js?v=20260928r35_10"></script>','<script src="/assets/js/stems-mixer.js?v=20260928r38_3"></script>')
twig=twig.replace('<script src="/assets/js/lyricslab-r37.js?v=20260928r38_2a"></script>','<script src="/assets/js/lyricslab-r37.js?v=20260928r38_3"></script>')
write(p,twig)
print('R38_3_INSTALL_OK')
