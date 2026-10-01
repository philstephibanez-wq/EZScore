#!/usr/bin/env python3
from pathlib import Path
import re, sys
repo=Path(sys.argv[1] if len(sys.argv)>1 else '.').resolve()
analysis=repo/'analysis'/'lyrics_timeline_analysis.py'
service=repo/'src'/'Service'/'LyricsTimelineResultService.php'
if not analysis.is_file(): raise SystemExit(f'ABSENT: {analysis}')
if not service.is_file(): raise SystemExit(f'ABSENT: {service}')
txt=analysis.read_text(encoding='utf-8')
replacement="def normalise_section_type(label: str) -> str:\n    value=unicodedata.normalize('NFKD',label.lower())\n    value=''.join(c for c in value if not unicodedata.combining(c))\n    value=re.sub(r'\\s+\\d+\\s*$','',value).strip()\n    aliases={'intro':'intro','introduction':'intro','couplet':'verse','verse':'verse','refrain':'chorus','chorus':'chorus','pont':'bridge','bridge':'bridge','pre-refrain':'prechorus','pre chorus':'prechorus','prechorus':'prechorus','instrumental':'instrumental','solo':'solo','final':'final','outro':'outro','coda':'coda'}\n    return aliases.get(value,'section')\n\ndef section_label(line: str) -> str | None:\n    s=line.strip()\n    if not s:\n        return None\n    m=re.fullmatch(r'\\[([^\\[\\]\\r\\n]{1,80})\\]',s)\n    if m:\n        return m.group(1).strip()\n    m=re.fullmatch(r'([^\\r\\n:]{1,48}):',s)\n    if m:\n        candidate=m.group(1).strip()\n        if normalise_section_type(candidate)!='section':\n            return candidate\n    return None\n\n_CHORD_TOKEN_RE=re.compile(r'^(?:[A-G](?:#|b|♭)?(?:maj|min|m|dim|aug|sus|add|M)?(?:\\d{0,2})?(?:\\([^)]*\\))?(?:/[A-G](?:#|b|♭)?)?|[._|-]|\\([xX0-9]{4,8}\\))$')\n\ndef is_chord_line(line: str) -> bool:\n    tokens=re.findall(r'\\S+',line.strip())\n    if not tokens:\n        return False\n    ok=0\n    musical=0\n    for token in tokens:\n        c=token.strip().strip('|')\n        if not c:\n            ok+=1\n            continue\n        if _CHORD_TOKEN_RE.fullmatch(c):\n            ok+=1\n            if re.match(r'^[A-G]',c):\n                musical+=1\n    return musical>0 and ok/max(1,len(tokens))>=0.72\n\ndef source_tokens(text: str) -> list[dict]:\n    rows=[]\n    current_section=None\n    current_section_type=None\n    for line in text.replace('\\r\\n','\\n').replace('\\r','\\n').split('\\n'):\n        label=section_label(line)\n        if label is not None:\n            current_section=label\n            current_section_type=normalise_section_type(label)\n            continue\n        if is_chord_line(line):\n            continue\n        words=re.findall(r'\\S+',line)\n        for i,word in enumerate(words):\n            rows.append({\n                'text':word,\n                'norm':normalise_token(word),\n                'line_break_after':i==len(words)-1,\n                'section_label':current_section,\n                'section_type':current_section_type,\n            })\n    if rows:\n        rows[-1]['line_break_after']=False\n    return rows\n"
pat=re.compile(r"def source_tokens\(text: str\) -> list\[dict\]:.*?(?=\ndef choose_model_path\(\))",re.S)
if 'def section_label(line: str)' not in txt:
    if not pat.search(txt): raise SystemExit('source_tokens block not found')
    txt=pat.sub(lambda _m: replacement.rstrip()+'\n',txt,count=1)
old="        'line_break_after': bool(row.get('line_break_after')),\n        'confidence': round(float(row.get('confidence', 0.0)), 4),\n        'language': row.get('language'),"
new="        'line_break_after': bool(row.get('line_break_after')),\n        'section_label': row.get('section_label'),\n        'section_type': row.get('section_type'),\n        'confidence': round(float(row.get('confidence', 0.0)), 4),\n        'language': row.get('language'),"
if "'section_label': row.get('section_label')" not in txt:
    if old not in txt: raise SystemExit('lyrics payload block not found')
    txt=txt.replace(old,new,1)
analysis.write_text(txt,encoding='utf-8',newline='\n')
php=service.read_text(encoding='utf-8')
oldp="                'line_break_after'=>(bool)($word['line_break_after']??false),\n                'confidence'=>isset($word['confidence'])?(float)$word['confidence']:null,\n                'analysis_version'=>(string)($result['version']??'r36.0'),"
newp="                'line_break_after'=>(bool)($word['line_break_after']??false),\n                'section_label'=>isset($word['section_label'])&&is_string($word['section_label'])?trim($word['section_label']):null,\n                'section_type'=>isset($word['section_type'])&&is_string($word['section_type'])?trim($word['section_type']):null,\n                'confidence'=>isset($word['confidence'])?(float)$word['confidence']:null,\n                'analysis_version'=>(string)($result['version']??'r36.0'),"
if "'section_label'=>" not in php:
    if oldp not in php: raise SystemExit('service payload block not found')
    php=php.replace(oldp,newp,1)
service.write_text(php,encoding='utf-8',newline='\n')
print('R38_0A_INSTALL_OK')
