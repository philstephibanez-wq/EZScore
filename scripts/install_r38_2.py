#!/usr/bin/env python3
from pathlib import Path
import re, sys
repo=Path(sys.argv[1] if len(sys.argv)>1 else '.').resolve()
twig=repo/'templates'/'song'/'lyricslab.html.twig'
analysis=repo/'analysis'/'lyrics_timeline_analysis.py'
if not twig.is_file(): raise SystemExit(f'ABSENT: {twig}')
if not analysis.is_file(): raise SystemExit(f'ABSENT: {analysis}')
view=twig.read_text(encoding='utf-8')
if 'data-profile-data-url-template=' not in view:
    needle='         data-time-signature="{{ song.timeSignature }}"\n'
    add=needle+'         data-profile-data-url-template="{{ path(\'app_song_chordslab_profile_data\', {\'_locale\': app.request.locale, id: song.id, profile:\'__PROFILE__\'}) }}"\n         data-profile-save-url="{{ path(\'app_song_chordslab_profile\', {\'_locale\': app.request.locale, id: song.id}) }}"\n         data-profile-token="{{ csrf_token(\'song_chordslab_profile_\' ~ song.id) }}"\n'
    if needle not in view: raise SystemExit('LyricsLab data hook not found')
    view=view.replace(needle,add,1)
if 'data-lyrics-profile' not in view:
    needle='            <strong>{{ (\'chordslab.level.\' ~ song.chordAnalysisLevel)|trans({}, \'chordslab\') }}</strong>\n'
    add=needle+'            <select class="lyrics-profile-select" data-lyrics-profile aria-label="Profil d’accords">\n                <option value="beginner" {% if song.chordAnalysisLevel == \'beginner\' %}selected{% endif %}>Débutant</option>\n                <option value="intermediate" {% if song.chordAnalysisLevel == \'intermediate\' %}selected{% endif %}>Intermédiaire</option>\n                <option value="expert" {% if song.chordAnalysisLevel == \'expert\' %}selected{% endif %}>Expert</option>\n            </select>\n'
    if needle not in view: raise SystemExit('LyricsLab profile status hook not found')
    view=view.replace(needle,add,1)
view=re.sub(r'/assets/css/lyricslab-r37\.css\?v=[^\"\']+', '/assets/css/lyricslab-r37.css?v=20260928r38_2', view)
view=re.sub(r'/assets/js/lyricslab-r37\.js\?v=[^\"\']+', '/assets/js/lyricslab-r37.js?v=20260928r38_2', view)
twig.write_text(view,encoding='utf-8',newline='\n')
txt=analysis.read_text(encoding='utf-8')
replacement="def interpolate_unmatched(rows: list[dict]) -> list[dict]:\n    known = [i for i, row in enumerate(rows) if row.get('start_ms') is not None]\n    if not known:\n        return rows\n\n    first_known = known[0]\n    if first_known > 0:\n        anchor = int(rows[first_known]['start_ms'])\n        # Prefix words are packed immediately before the first acoustic anchor.\n        # Never spread them all the way back to MP3 t=0 through long intros.\n        window = min(1800, max(320, first_known * 190))\n        base = max(0, anchor - window)\n        step = max(80, (anchor - base) // max(1, first_known))\n        for i in range(first_known):\n            start = base + i * step\n            end = min(anchor, start + max(100, step - 10))\n            rows[i].update(start_ms=start, end_ms=end, confidence=0.18)\n\n    for i, row in enumerate(rows):\n        if row.get('start_ms') is not None:\n            continue\n        left = max((k for k in known if k < i), default=None)\n        right = min((k for k in known if k > i), default=None)\n\n        if left is not None and right is not None:\n            span = max(1, right - left)\n            ratio = (i - left) / span\n            a = rows[left]['end_ms']\n            b = rows[right]['start_ms']\n            t = int(round(a + (b - a) * ratio))\n            row.update(start_ms=t, end_ms=t + 120, confidence=0.35)\n        elif left is not None:\n            t = rows[left]['end_ms'] + max(80, (i - left - 1) * 180)\n            row.update(start_ms=t, end_ms=t + 160, confidence=0.25)\n\n    return rows\n"
pat=re.compile(r'def interpolate_unmatched\(rows: list\[dict\]\) -> list\[dict\]:.*?(?=\ndef align_provided_text\()',re.S)
if not pat.search(txt): raise SystemExit('interpolate_unmatched block not found')
txt=pat.sub(lambda _m: replacement.rstrip()+'\n',txt,count=1)
analysis.write_text(txt,encoding='utf-8',newline='\n')
print('R38_2_INSTALL_OK')
