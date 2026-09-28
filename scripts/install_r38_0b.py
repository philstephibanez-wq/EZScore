#!/usr/bin/env python3
from pathlib import Path
import sys
repo=Path(sys.argv[1] if len(sys.argv)>1 else '.').resolve()
analysis=repo/'analysis'/'lyrics_timeline_analysis.py'
twig=repo/'templates'/'song'/'lyricslab.html.twig'
if not analysis.is_file(): raise SystemExit(f'ABSENT: {analysis}')
if not twig.is_file(): raise SystemExit(f'ABSENT: {twig}')
txt=analysis.read_text(encoding='utf-8')
old="def write_json(path: str | Path, payload: dict) -> None:\n    p = Path(path)\n    p.parent.mkdir(parents=True, exist_ok=True)\n    tmp = p.with_suffix(p.suffix + '.tmp')\n    tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')\n    tmp.replace(p)\n"
new="def write_json(path: str | Path, payload: dict) -> None:\n    p = Path(path)\n    p.parent.mkdir(parents=True, exist_ok=True)\n    data = json.dumps(payload, ensure_ascii=False)\n\n    import tempfile\n    fd, tmp_name = tempfile.mkstemp(\n        prefix=p.name + '.',\n        suffix='.tmp',\n        dir=str(p.parent),\n        text=True,\n    )\n    tmp = Path(tmp_name)\n    try:\n        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as handle:\n            handle.write(data)\n            handle.flush()\n            try:\n                os.fsync(handle.fileno())\n            except OSError:\n                pass\n\n        last_error = None\n        for attempt in range(20):\n            try:\n                os.replace(tmp, p)\n                return\n            except PermissionError as exc:\n                last_error = exc\n                time.sleep(0.025 * (attempt + 1))\n\n        try:\n            p.write_text(data, encoding='utf-8')\n            return\n        except Exception:\n            if last_error is not None:\n                raise last_error\n            raise\n    finally:\n        tmp.unlink(missing_ok=True)\n"
if 'tempfile.mkstemp(' not in txt:
    if old not in txt: raise SystemExit('write_json block not found')
    txt=txt.replace(old,new,1)
analysis.write_text(txt,encoding='utf-8',newline='\n')
view=twig.read_text(encoding='utf-8')
view=view.replace('/assets/css/lyricslab-r37.css?v=20260928r37_0','/assets/css/lyricslab-r37.css?v=20260928r38_0b')
view=view.replace('/assets/js/lyricslab-r37.js?v=20260928r37_0','/assets/js/lyricslab-r37.js?v=20260928r38_0b')
view=view.replace('Le mot courant s’allume dans la cellule du beat joué. Cliquez sur un mot pour le corriger.','Prompteur en lecture seule : section, accord courant fixe et paroles synchronisées mot à mot.')
twig.write_text(view,encoding='utf-8',newline='\n')
print('R38_0B_INSTALL_OK')
