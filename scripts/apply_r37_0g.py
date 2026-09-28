#!/usr/bin/env python3
from pathlib import Path
import re
import sys

def die(msg):
    raise SystemExit("R37.0g ABORT: " + msg)

root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()

# 1) Twig: make Analyze a native POST and attach the textarea directly to that form.
twig = root / "templates/song/lyricslab.html.twig"
if not twig.is_file():
    die("templates/song/lyricslab.html.twig absent")
s = twig.read_text(encoding="utf-8-sig")

s = s.replace(
    '                  data-lyrics-analyze-form>\n',
    '                  id="lyrics-analyze-form">\n',
    1,
)

if 'id="lyrics-analyze-form"' not in s:
    die("formulaire Analyze introuvable")

if 'name="lyrics_source"' not in s:
    s = s.replace(
        '<textarea data-lyrics-source\n',
        '<textarea data-lyrics-source\n              name="lyrics_source"\n              form="lyrics-analyze-form"\n',
        1,
    )

twig.write_text(s, encoding="utf-8", newline="\n")

# 2) Controller: persist posted textarea and ALWAYS queue mode=align.
controller = root / "src/Controller/SongLabController.php"
if not controller.is_file():
    die("src/Controller/SongLabController.php absent")
s = controller.read_text(encoding="utf-8-sig")

start = s.find("public function analyzeLyrics(")
end = s.find("#[Route('/lyrics/status'", start)
if start < 0 or end < 0:
    die("méthode analyzeLyrics introuvable")

block = s[start:end]

if "EntityManagerInterface $em" not in block:
    block = re.sub(
        r'public function analyzeLyrics\(\s*Song \$song,\s*Request \$request,\s*\\App\\Service\\SongLyricsJobService \$jobs\s*\): Response',
        "public function analyzeLyrics(\n"
        "    Song $song,\n"
        "    Request $request,\n"
        "    \\App\\Service\\SongLyricsJobService $jobs,\n"
        "    EntityManagerInterface $em,\n"
        "): Response",
        block,
        count=1,
    )

if "$request->request->get('lyrics_source'" not in block:
    needle = "    $user=$this->requireEditor($song);\n"
    if needle not in block:
        die("ancre requireEditor introuvable dans analyzeLyrics")
    insert = (
        needle +
        "    $postedText = (string) $request->request->get('lyrics_source', '');\n"
        "    if ($postedText !== '') {\n"
        "        $song->setLyricsSourceText($postedText);\n"
        "        $em->flush();\n"
        "    }\n"
    )
    block = block.replace(needle, insert, 1)

block = block.replace("$jobs->queue($song,$user);", "$jobs->queue($song,$user,'align');")
block = block.replace("$jobs->queue($song, $user);", "$jobs->queue($song, $user, 'align');")

if "mode" not in block and "$jobs->queue($song,$user,'align');" not in block and "$jobs->queue($song, $user, 'align');" not in block:
    die("queue align non appliquée")

s = s[:start] + block + s[end:]
controller.write_text(s, encoding="utf-8", newline="\n")

# 3) JS: remove any submit interception for Analyze. Native form submit is authoritative.
js = root / "public/assets/js/lyricslab-r37.js"
if not js.is_file():
    die("public/assets/js/lyricslab-r37.js absent")
j = js.read_text(encoding="utf-8-sig")

j = re.sub(
    r"\ndocument\.querySelector\('\[data-lyrics-analyze-form\]'\)\?\.addEventListener\('submit',async e=>\{.*?\n\}\);\n",
    "\n",
    j,
    count=1,
    flags=re.S,
)
js.write_text(j, encoding="utf-8", newline="\n")

# Final verification.
t = twig.read_text(encoding="utf-8")
c = controller.read_text(encoding="utf-8")
j = js.read_text(encoding="utf-8")

for token in ['id="lyrics-analyze-form"', 'name="lyrics_source"', 'form="lyrics-analyze-form"']:
    if token not in t:
        die("Twig token absent: " + token)

for token in ["$request->request->get('lyrics_source'", "EntityManagerInterface $em"]:
    if token not in c:
        die("Controller token absent: " + token)

if "$jobs->queue($song,$user,'align');" not in c and "$jobs->queue($song, $user, 'align');" not in c:
    die("queue align absente")

if "data-lyrics-analyze-form" in j:
    die("intercepteur submit JS encore présent")

print("R37_0G_APPLIED_OK")
