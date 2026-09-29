#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT=Path(sys.argv[1] if len(sys.argv)>1 else r"H:\EZScore_v1").resolve()
HERE=Path(__file__).resolve().parent.parent

def read(path):
    if not path.is_file():
        raise RuntimeError(f"Missing prerequisite: {path}")
    return path.read_text(encoding="utf-8")

def write(path,text):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(text,encoding="utf-8",newline="\n")

chord_js=ROOT/"public/assets/js/chordslab.js"
lyrics_js=ROOT/"public/assets/js/lyricslab-r37.js"
chord_twig=ROOT/"templates/song/chordslab.html.twig"
lyrics_twig=ROOT/"templates/song/lyricslab.html.twig"
lyrics_css=ROOT/"public/assets/css/lyricslab-r37.css"

cj=read(chord_js)
lj=read(lyrics_js)
ct=read(chord_twig)
lt=read(lyrics_twig)
lc=read(lyrics_css)

core=read(HERE/"patches/ezscore-timeline-core-r39.js")
renderer=read(HERE/"patches/lyricslab-timeline-r39.js")
cdc=read(HERE/"docs/CDC_TIMELINE_CANONIQUE_R39.md")

write(ROOT/"public/assets/js/ezscore-timeline-core-r39.js",core)
write(ROOT/"public/assets/js/lyricslab-timeline-r39.js",renderer)
write(ROOT/"docs/CDC_TIMELINE_CANONIQUE_R39.md",cdc)

if "timelineCore=()=>window.EZScoreTimelineCoreR39" not in cj:
    old="const beats=parse(root.dataset.beats).sort((a,b)=>a.start_ms-b.start_ms);\nlet capo=Number(root.dataset.capo||0), signature=root.dataset.timeSignature||'4/4';"
    new="const beats=parse(root.dataset.beats).sort((a,b)=>a.start_ms-b.start_ms);\nlet capo=Number(root.dataset.capo||0), signature=root.dataset.timeSignature||'4/4';\nconst canonicalSignature=signature;\nconst timelineCore=()=>window.EZScoreTimelineCoreR39?.create({beats,timeSignature:signature,spacing:44,preserveSourcePosition:signature===canonicalSignature})||null;"
    if old not in cj:
        raise RuntimeError("ChordsLab bootstrap anchor not found")
    cj=cj.replace(old,new,1)
    cj=cj.replace("\nconst canonicalSignature=signature;\nfunction buildProjection(){","\nfunction buildProjection(){",1)
    start=cj.find("function buildProjection(){")
    end=cj.find("\nfunction profileLabel(",start)
    if start<0 or end<0:
        raise RuntimeError("ChordsLab buildProjection block not found")
    replacement=(
        "function buildProjection(){\n"
        " const core=timelineCore();\n"
        " if(core){\n"
        "  const slots=core.chordProjection(events,displayChord),measures=[];\n"
        "  for(const slot of slots){\n"
        "   const measureIndex=Number(slot.beat.display_measure_index);\n"
        "   let measure=measures.at(-1);\n"
        "   if(!measure||measure.index!==measureIndex){measure={index:measureIndex,slots:[]};measures.push(measure)}\n"
        "   measure.slots.push({seq:slot.seq,beatIndex:Number(slot.beat.display_beat_index),startMs:slot.startMs,text:slot.text,beatId:slot.beatId,eventId:slot.eventId,activeEventId:slot.activeEventId,editable:slot.editable});\n"
        "  }\n"
        "  return measures;\n"
        " }\n"
        " throw new Error('EZScore canonical timeline engine missing');\n"
        "}\n"
    )
    cj=cj[:start]+replacement+cj[end:]
    oldh="const ms=seconds*1000;let seq=-1;\n for(let i=0;i<beats.length;i++){if(beats[i].start_ms<=ms)seq=i;else break}"
    newh="const ms=seconds*1000;const core=timelineCore();let seq=core?core.beatIndexAtMs(ms):-1;"
    if oldh not in cj:
        raise RuntimeError("ChordsLab highlight anchor not found")
    cj=cj.replace(oldh,newh,1)

guard="const root=document.querySelector('[data-lyricslab]'); if(!root)return;"
if "EZScoreLyricsTimelineR39.mount(root)" not in lj:
    if guard not in lj:
        raise RuntimeError("LyricsLab root anchor not found")
    lj=lj.replace(guard,guard+"\nif(window.EZScoreLyricsTimelineR39){window.EZScoreLyricsTimelineR39.mount(root);return;}",1)

if "data-chord-beat-edit-url-template" not in lt:
    anchor='         data-edit-token="{{ csrf_token(\'song_lyricslab_word_\' ~ song.id) }}">'
    repl='''         data-edit-token="{{ csrf_token('song_lyricslab_word_' ~ song.id) }}"
         data-chord-beat-edit-url-template="{{ path('app_song_chordslab_beat_override', {'_locale': app.request.locale, id: song.id, beatId: 999999})|replace({'999999':'__BEAT__'}) }}"
         data-chord-edit-token="{{ csrf_token('song_chordslab_edit_' ~ song.id) }}">'''
    if anchor not in lt:
        raise RuntimeError("LyricsLab data token anchor not found")
    lt=lt.replace(anchor,repl,1)

lt=lt.replace("{{ lyric_events|length }} mots ancrés","{{ lyric_events|length }} mots · rendu syllabique",1)
lt=lt.replace("Prompteur en lecture seule : accords et paroles défilent sous une zone de lecture fixe.","Timeline musicale commune : cliquez un accord pour le modifier ; syllabes et accords partagent exactement le même axe temporel.",1)

core_tag='<script src="/assets/js/ezscore-timeline-core-r39.js?v=20260929r39_0"></script>'
if core_tag not in ct:
    anchor='<script src="/assets/js/chordslab.js?v=20260928r35_10"></script>'
    if anchor not in ct:
        raise RuntimeError("ChordsLab script anchor not found")
    ct=ct.replace(anchor,core_tag+"\n"+'<script src="/assets/js/chordslab.js?v=20260929r39_0"></script>',1)

renderer_tag='<script src="/assets/js/lyricslab-timeline-r39.js?v=20260929r39_0"></script>'
if core_tag not in lt:
    anchor='<script src="/assets/js/lyricslab-r37.js?v=20260929r38_17c"></script>'
    if anchor not in lt:
        raise RuntimeError("LyricsLab script anchor not found")
    lt=lt.replace(anchor,core_tag+"\n"+renderer_tag+"\n"+'<script src="/assets/js/lyricslab-r37.js?v=20260929r39_0"></script>',1)

css_patch=read(HERE/"patches/lyricslab-r39.css.txt")
if "R39 canonical shared timeline" not in lc:
    lc=lc.rstrip()+"\n\n"+css_patch.rstrip()+"\n"
lt=lt.replace('/assets/css/lyricslab-r37.css?v=20260928r38_2','/assets/css/lyricslab-r37.css?v=20260929r39_0')

for needle in ["timelineCore=()=>window.EZScoreTimelineCoreR39","core.chordProjection(events,displayChord)"]:
    if needle not in cj:
        raise RuntimeError(f"ChordsLab validation failed: {needle}")
if "EZScoreLyricsTimelineR39.mount(root)" not in lj:
    raise RuntimeError("LyricsLab delegation validation failed")
for needle in ["data-chord-beat-edit-url-template","data-chord-edit-token","lyricslab-timeline-r39.js"]:
    if needle not in lt:
        raise RuntimeError(f"LyricsLab template validation failed: {needle}")

write(chord_js,cj)
write(lyrics_js,lj)
write(chord_twig,ct)
write(lyrics_twig,lt)
write(lyrics_css,lc)
print("R39_CANONICAL_TIMELINE_SYLLABLES_INSTALL_OK")
