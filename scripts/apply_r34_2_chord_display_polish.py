#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
BACKUP = ROOT / 'var' / 'backup' / ('r34-2-chord-display-' + datetime.now().strftime('%Y%m%d-%H%M%S'))


def backup_file(path: Path) -> None:
    dst = BACKUP / path.relative_to(ROOT)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dst)


def find_js_file() -> Path:
    candidates = []
    base = ROOT / 'public' / 'assets' / 'js'
    if base.exists():
        candidates.extend(sorted(base.glob('**/*.js')))
    for path in candidates:
        try:
            text = path.read_text(encoding='utf-8')
        except Exception:
            continue
        if 'data-chordslab' in text and 'const SHAPES=' in text:
            return path
    raise RuntimeError('Impossible de localiser le fichier JavaScript de ChordsLab dans public/assets/js.')


def find_translation_file() -> Path | None:
    trans = ROOT / 'translations'
    if not trans.exists():
        return None
    for path in sorted(trans.glob('**/*fr*.yaml')) + sorted(trans.glob('**/*fr*.yml')):
        try:
            text = path.read_text(encoding='utf-8')
        except Exception:
            continue
        if 'guitar_chords:' in text:
            return path
    return None


def ensure_once(text: str, marker: str) -> bool:
    return marker in text


def patch_js(path: Path) -> None:
    text = path.read_text(encoding='utf-8')
    marker = '/* R34.2 rich chord labels / diagram polish */'
    if marker in text:
        print(f'[OK] {path.relative_to(ROOT)} : already applied')
        return

    old_block = """const SHAPES={C:'x32010',Cm:'x35543',C7:'x32310',D:'xx0232',Dm:'xx0231',D7:'xx0212',E:'022100',Em:'022000',E7:'020100',F:'133211',Fm:'133111',F7:'131211',G:'320003',Gm:'355333',G7:'320001',A:'x02220',Am:'x02210',A7:'x02020',B:'x24442',Bm:'x24432',B7:'x21202'};

function normaliseLabel(chord){"""

    new_block = """const SHAPES={
 C:'x32010',Cm:'x35543',C7:'x32310',Cmaj7:'x32000',Cadd9:'x32030',Cm7:'x35343',Csus2:'x30033',Csus4:'x33011',
 D:'xx0232',Dm:'xx0231',D7:'xx0212',Dmaj7:'xx0222',Dm7:'xx0211',Dadd9:'xx0230',Dsus2:'xx0230',Dsus4:'xx0233',
 E:'022100',Em:'022000',E7:'020100',Emaj7:'021100',Em7:'022030',Esus4:'022200',
 F:'133211',Fm:'133111',F7:'131211',Fmaj7:'xx3210',Fadd9:'103211',Fm7:'131111',Fsus4:'133311',
 G:'320003',Gm:'355333',G7:'320001',Gmaj7:'320002',Gadd9:'320203',Gsus4:'330013',G6:'320000',
 A:'x02220',Am:'x02210',A7:'x02020',Amaj7:'x02120',Am7:'x02010',Aadd9:'x02420',Asus2:'x02200',Asus4:'x02230',
 B:'x24442',Bm:'x24432',B7:'x21202',Bmaj7:'x24342',Bm7:'x20202',Bsus4:'x24452'
};

const diagramLabel=diagramToggle?.closest('label');
if(diagramLabel)diagramLabel.classList.add('chordslab-diagram-inline');
installR342Styles();

function normaliseLabel(chord){"""
    if old_block not in text:
        raise RuntimeError('Bloc SHAPES / normaliseLabel introuvable dans le fichier JS ChordsLab.')
    text = text.replace(old_block, new_block, 1)

    helper_anchor = """function displayChord(chord){
 chord=normaliseLabel(chord);
 if(!chord||chord==='.')return chord||'.';
 const m=/^([A-G](?:#|b)?)(.*)$/.exec(chord); if(!m)return chord;
 const pc=NOTE_TO_PC[m[1]]; if(pc===undefined)return chord;
 const shown=(pc-capo+120)%12;
 return (m[1].includes('b')?FLAT:SHARP)[shown]+m[2];
}
function activeEventAt(ms){let current=null;for(const e of events){if(e.start_ms<=ms)current=e;else break}return current}
"""
    helper_replace = """function displayChord(chord){
 chord=normaliseLabel(chord);
 if(!chord||chord==='.')return chord||'.';
 const m=/^([A-G](?:#|b)?)(.*)$/.exec(chord); if(!m)return chord;
 const pc=NOTE_TO_PC[m[1]]; if(pc===undefined)return chord;
 const shown=(pc-capo+120)%12;
 return (m[1].includes('b')?FLAT:SHARP)[shown]+m[2];
}
function splitChordLabel(chord){
 const text=String(chord||'').trim();
 if(!text||text==='-'||text==='.')return {raw:text,root:text,suffix:'',bass:''};
 const slash=text.split('/');
 const head=slash.shift()||'';
 const bass=slash.length?'/'+slash.join('/') : '';
 const m=/^([A-G](?:#|b)?)(.*)$/.exec(head);
 if(!m)return {raw:text,root:text,suffix:'',bass};
 return {raw:text,root:m[1],suffix:m[2]||'',bass};
}
function formatChordHtml(chord){
 const parts=splitChordLabel(chord);
 if(!parts.raw||parts.raw==='-'||parts.raw==='.')return escapeHtml(parts.raw||'.');
 const suffix=escapeHtml(parts.suffix)
  .replace(/maj/g,'<span class="chord-quality-maj">maj</span>');
 return `<span class="chord-label-root">${escapeHtml(parts.root)}</span><span class="chord-label-suffix">${suffix}</span>${parts.bass?`<span class="chord-label-bass">${escapeHtml(parts.bass)}</span>`:''}`;
}
function installR342Styles(){
 if(document.getElementById('ezscore-r34-2-style'))return;
 const style=document.createElement('style');
 style.id='ezscore-r34-2-style';
 style.textContent=`/* R34.2 rich chord labels / diagram polish */
 .chord-slot{display:flex;align-items:center;justify-content:center;gap:0;overflow:hidden}
 .chord-label-root{font-size:1em;font-weight:800;line-height:1}
 .chord-label-suffix{font-size:1em;line-height:1}
 .chord-quality-maj{display:inline-block;font-size:.62em;line-height:1;vertical-align:super;letter-spacing:.04em;text-transform:none;opacity:.95;margin-inline:1px 0}
 .chord-label-bass{font-size:.8em;opacity:.9;margin-left:1px}
 [data-chord-diagram] strong{display:inline-flex;align-items:flex-start;gap:0;line-height:1.05}
 .chordslab-diagram-inline{display:inline-flex!important;align-items:center!important;gap:10px;white-space:nowrap;min-height:38px}
 .chordslab-diagram-inline>span{display:inline!important;margin:0!important;font-size:14px!important;line-height:1.1!important;text-transform:none!important;letter-spacing:0!important}
 .chordslab-diagram-inline input[type="checkbox"]{margin:0}
 .chordslab-diagram-inline .form-check-label,.chordslab-diagram-inline .checkbox-label{display:inline!important;white-space:nowrap}
 `;
 document.head.appendChild(style);
}
function activeEventAt(ms){let current=null;for(const e of events){if(e.start_ms<=ms)current=e;else break}return current}
"""
    if helper_anchor not in text:
        raise RuntimeError('Ancre displayChord / activeEventAt introuvable dans le fichier JS ChordsLab.')
    text = text.replace(helper_anchor, helper_replace, 1)

    line = "b.textContent=slot.text;"
    repl = "b.innerHTML=formatChordHtml(slot.text); b.setAttribute('aria-label', slot.text);"
    if line not in text:
        raise RuntimeError('Affectation texte des slots introuvable.')
    text = text.replace(line, repl, 1)

    old_unavailable = "if(!shape){diagramEl.innerHTML=`<strong>${escapeHtml(chord)}</strong><small>Diagramme non disponible</small>`;return}"
    new_unavailable = "if(!shape){diagramEl.innerHTML=`<strong class=\"chord-diagram-title\">${formatChordHtml(chord)}</strong><small>Diagramme non disponible</small>`;return}"
    if old_unavailable not in text:
        raise RuntimeError('Branche diagramme non disponible introuvable.')
    text = text.replace(old_unavailable, new_unavailable, 1)

    old_diagram = "diagramEl.innerHTML=`<strong>${escapeHtml(chord)}</strong><svg viewBox=\"0 0 120 105\" role=\"img\" aria-label=\"${escapeHtml(chord)}\"><g stroke=\"currentColor\" fill=\"none\"><path d=\"M18 18V90M36 18V90M54 18V90M72 18V90M90 18V90M108 18V90\"/><path d=\"M18 18H108M18 36H108M18 54H108M18 72H108M18 90H108\"/></g>${marks}</svg>`;"
    new_diagram = "diagramEl.innerHTML=`<strong class=\"chord-diagram-title\">${formatChordHtml(chord)}</strong><svg viewBox=\"0 0 120 105\" role=\"img\" aria-label=\"${escapeHtml(chord)}\"><g stroke=\"currentColor\" fill=\"none\"><path d=\"M18 18V90M36 18V90M54 18V90M72 18V90M90 18V90M108 18V90\"/><path d=\"M18 18H108M18 36H108M18 54H108M18 72H108M18 90H108\"/></g>${marks}</svg>`;"
    if old_diagram not in text:
        raise RuntimeError('Rendu diagramme introuvable.')
    text = text.replace(old_diagram, new_diagram, 1)

    backup_file(path)
    path.write_text(text, encoding='utf-8', newline='\n')
    print(f'[OK] {path.relative_to(ROOT)} : patched')


def patch_translation(path: Path | None) -> None:
    if path is None:
        print('[OK] translation fr: not found, skipped')
        return
    text = path.read_text(encoding='utf-8')
    old = '  guitar_chords: Afficher accords guitare'
    new = '  guitar_chords: Afficher les accords guitare'
    if new in text:
        print(f'[OK] {path.relative_to(ROOT)} : already applied')
        return
    if old in text:
        text = text.replace(old, new, 1)
        backup_file(path)
        path.write_text(text, encoding='utf-8', newline='\n')
        print(f'[OK] {path.relative_to(ROOT)} : patched')
    else:
        print(f'[OK] {path.relative_to(ROOT)} : key not patched (custom wording kept)')


def main() -> int:
    js_path = find_js_file()
    patch_js(js_path)
    patch_translation(find_translation_file())
    print(f'[OK] Backup: {BACKUP}')
    print('[OK] R34.2 applied.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
