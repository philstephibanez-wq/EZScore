#!/usr/bin/env python3
from pathlib import Path
import sys

def die(msg):
    raise SystemExit("R37.0f ABORT: " + msg)

root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
path = root / "public" / "assets" / "js" / "lyricslab-r37.js"
if not path.is_file():
    die("public/assets/js/lyricslab-r37.js absent")

s = path.read_text(encoding="utf-8-sig")

old = """document.querySelector('[data-lyrics-analyze-form]')?.addEventListener('submit',async e=>{
 if(!source)return;
 e.preventDefault();
 clearTimeout(timer);
 if(await saveSource())e.currentTarget.submit();
});"""

new = """document.querySelector('[data-lyrics-analyze-form]')?.addEventListener('submit',async e=>{
 if(!source)return;
 e.preventDefault();
 const form=e.currentTarget;
 clearTimeout(timer);
 if(await saveSource()){
  form.submit();
 }
});"""

if old in s:
    s = s.replace(old, new, 1)
elif "const form=e.currentTarget;" not in s:
    die("bloc submit LyricsLab inattendu")

path.write_text(s, encoding="utf-8", newline="\n")

check = path.read_text(encoding="utf-8")
for token in [
    "const form=e.currentTarget;",
    "if(await saveSource()){",
    "form.submit();",
]:
    if token not in check:
        die("token absent après patch: " + token)

print("R37_0F_APPLIED_OK")
