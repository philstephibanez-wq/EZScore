#!/usr/bin/env python3
from pathlib import Path
import sys,re

def die(msg):
    raise SystemExit("R35.8a ABORT: "+msg)

def rd(p):
    return p.read_text(encoding="utf-8-sig")

def wr(p,s):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(s,encoding="utf-8",newline="\n")

def replace_once(s,a,b,label):
    if a not in s:
        die("ancre absente: "+label)
    return s.replace(a,b,1)

root=Path(sys.argv[1] if len(sys.argv)>1 else ".").resolve()
for rel in [
    "analysis/chord_timeline_analysis.py",
    "public/assets/css/chordslab.css",
    "src/Service/ChordTimelineResultService.php",
    "templates/song/chordslab.html.twig",
]:
    if not (root/rel).is_file():
        die("fichier absent: "+rel)

# 1) Timeline absolue: R35.8 avait defini extend_beats_to_zero(), mais ne l'appelait pas.
p=root/"analysis/chord_timeline_analysis.py"
s=rd(p)
if "beat_times,prepended_count=extend_beats_to_zero" not in s:
    anchor='    bpm=numerator(signature)\n\n    prog(progress_file,32,"chroma","Extraction de l’harmonie")\n'
    replacement='    bpm=numerator(signature)\n\n    # R35.8a: timeline prompteur depuis t=0 du MP3.\n    beat_times,prepended_count=extend_beats_to_zero(beat_times,duration,tempo)\n    if prepended_count:\n        phase=(phase+prepended_count)%max(1,bpm)\n\n    prog(progress_file,32,"chroma","Extraction de l’harmonie")\n'
    s=replace_once(s,anchor,replacement,"appel extend_beats_to_zero")
if s.count("extend_beats_to_zero(") < 2:
    die("extend_beats_to_zero doit etre definie ET appelee")
s=s.replace('"version":"r35.8-absolute-timeline"','"version":"r35.8a-absolute-timeline"',1)
s=s.replace('"version":"r34-three-profiles"','"version":"r35.8a-absolute-timeline"',1)
wr(p,s)

# 2) Les crochets provenaient du CSS ::before/::after, pas du label de l'accord.
p=root/"public/assets/css/chordslab.css"
s=rd(p)
s=s.replace('.chord-measure-notation::before{content:"[";margin-right:6px}.chord-measure-notation::after{content:"]";margin-left:6px}\n','')
marker='/* R35.8a framed cells: no square brackets */'
if marker not in s:
    s += '\n'+marker+'\n.chord-measure-notation::before,.chord-measure-notation::after{content:none!important;display:none!important}\n'
wr(p,s)

# 3) Reanalyse autoritative: ne pas reancrer silencieusement les anciennes corrections.
p=root/"src/Service/ChordTimelineResultService.php"
s=rd(p)
start=s.find("        // Preserve manual corrections independently for each profile.")
end=s.find("        $this->timeline->deleteMusicalAnalysisForSong($song);")
if start!=-1 and end!=-1 and start<end:
    s=s[:start] + "        // R35.8a: fresh harmonic analysis is authoritative; old manual overrides are discarded.\n" + s[end:]
# remove reapply block if still present
s=re.sub(r"\n\s*\$overrideKey = \$profile\.':'\.\(\$measure \?\? -1\)\.':'\.\(\$beat \?\? -1\);\n\s*if \(isset\(\$overrides\[\$overrideKey\]\)\) \{\n\s*\$event->setOverrideValue\([^\n]+\);\n\s*\}\n", "\n", s, count=1)
if "$overrides" in s:
    die("ancienne logique de conservation des overrides encore presente")
wr(p,s)

# 4) Texte et cache-busting.
p=root/"templates/song/chordslab.html.twig"
s=rd(p)
s=s.replace(
    "Les corrections manuelles déjà enregistrées seront conservées profil par profil lorsqu’elles peuvent être réancrées sur les mêmes beats.",
    "La nouvelle analyse remplacera la grille automatique actuelle. Les corrections manuelles de l’ancienne analyse seront supprimées."
)
s=re.sub(r'/assets/css/chordslab\.css\?v=[^"]+', '/assets/css/chordslab.css?v=20260928r35_8a', s)
s=re.sub(r'/assets/js/chordslab\.js\?v=[^"]+', '/assets/js/chordslab.js?v=20260928r35_8a', s)
wr(p,s)

# Assertions
css=rd(root/"public/assets/css/chordslab.css")
if 'content:"["' in css or 'content:"]"' in css or "content:'['" in css or "content:']'" in css:
    die("crochets CSS encore presents")
py=rd(root/"analysis/chord_timeline_analysis.py")
if py.count("extend_beats_to_zero(") < 2:
    die("timeline t=0 non branchee")
svc=rd(root/"src/Service/ChordTimelineResultService.php")
if "$overrides" in svc:
    die("reanalyse conserve encore des overrides")
print("R35_8A_APPLIED_OK")
