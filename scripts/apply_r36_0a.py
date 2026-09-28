#!/usr/bin/env python3
from pathlib import Path
import shutil,sys

def die(msg):raise SystemExit("R36.0a ABORT: "+msg)
def rd(p):return p.read_text(encoding="utf-8-sig")
def wr(p,s):p.write_text(s,encoding="utf-8",newline="\n")

root=Path(sys.argv[1] if len(sys.argv)>1 else ".").resolve()
bundle=Path(__file__).resolve().parents[1]/"payload"

worker=root/"worker_app/ezscore_analysis_worker.pyw"
twig=root/"templates/song/lyricslab.html.twig"
if not worker.is_file():die("worker absent")
if not twig.is_file():die("R36.0 LyricsLab absent: appliquer R36.0 avant ce hotfix")

s=rd(worker)

# The R36.0 dispatch exists, but the method was not actually inside WorkerEngine.
if 'if job.get("kind") == "lyrics":' not in s:
    anchor='        if job.get("kind") == "chords":\n            self._run_chord_job(job)\n            return\n\n'
    if anchor not in s:die("dispatch chords introuvable")
    s=s.replace(anchor,anchor+'        if job.get("kind") == "lyrics":\n            self._run_lyrics_job(job)\n            return\n\n',1)

# Remove any malformed/nested duplicate method if one exists outside the real method table.
# Then insert exactly before WorkerEngine._read_progress, which is after _run_chord_job.
method=rd(bundle/"patches/worker_method.txt")
if "    def _run_lyrics_job(self, job: dict) -> None:" not in s:
    anchor="    @staticmethod\n    def _read_progress(path: Path) -> dict | None:\n"
    if anchor not in s:die("ancre WorkerEngine _read_progress introuvable")
    s=s.replace(anchor,method+anchor,1)

wr(worker,s)

# Presentation: LyricsLab deliberately reuses ChordsLab template classes and stylesheet.
shutil.copy2(bundle/"templates/song/lyricslab.html.twig",twig)
for rel in ["public/assets/js/lyricslab-r36-0a.js","public/assets/css/lyricslab-r36-0a.css"]:
    src=bundle/rel;dst=root/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)

# Hard checks.
s=rd(worker)
if s.count("    def _run_lyrics_job(self, job: dict) -> None:")!=1:die("méthode lyrics absente ou dupliquée")
dispatch=s.find('if job.get("kind") == "lyrics":')
method_pos=s.find("    def _run_lyrics_job(self, job: dict) -> None:")
static_pos=s.find("    @staticmethod\n    def _read_progress")
if min(dispatch,method_pos,static_pos)<0 or not (dispatch<method_pos<static_pos):die("méthode lyrics mal placée dans WorkerEngine")

print("R36_0A_APPLIED_OK")
