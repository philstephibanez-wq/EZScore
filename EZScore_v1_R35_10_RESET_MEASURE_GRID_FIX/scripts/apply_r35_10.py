#!/usr/bin/env python3
from pathlib import Path
import sys,re

def die(msg):
    raise SystemExit('R35.10 ABORT: '+msg)

def rd(p):
    return p.read_text(encoding='utf-8-sig')

def wr(p,s):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(s,encoding='utf-8',newline='\n')

root=Path(sys.argv[1] if len(sys.argv)>1 else '.').resolve()
required=[
    'analysis/chord_timeline_analysis.py',
    'templates/song/chordslab.html.twig',
    'public/assets/js/chordslab-r33-2.js',
]
for rel in required:
    if not (root/rel).is_file(): die('fichier absent: '+rel)

# 1) Full measures from MP3 t=0: phase remains metadata, not a partial first bar.
p=root/'analysis/chord_timeline_analysis.py'
s=rd(p)
old='''def position(i,phase,bpm):\n    if phase<=0:return i//bpm,i%bpm\n    if i<phase:return 0,bpm-phase+i\n    shifted=i-phase\n    return 1+shifted//bpm,shifted%bpm\n'''
new='''def position(i,phase,bpm):\n    # R35.10: absolute prompter grid. Measure 1 always contains exactly bpm beats\n    # from MP3 t=0. Downbeat phase is preserved as analysis metadata only.\n    return i//bpm,i%bpm\n'''
if old in s:
    s=s.replace(old,new,1)
elif 'return i//bpm,i%bpm' not in s:
    die('fonction position inattendue')
s=s.replace('"version":"r35.8a-absolute-timeline"','"version":"r35.10-absolute-full-measures"',1)
wr(p,s)

# 2) Reset confirmation: no dedicated dialog in DOM. The global EZScore modal
# opens only when the reset form itself is submitted.
p=root/'templates/song/chordslab.html.twig'
s=rd(p)
# Add global confirmation attribute to reset form.
needle='''action="{{ path('app_song_chordslab_reset', {'_locale': app.request.locale, id: song.id}) }}" data-chord-reset-form>'''
replacement='''action="{{ path('app_song_chordslab_reset', {'_locale': app.request.locale, id: song.id}) }}"\n                  data-ez-confirm="Réinitialiser les accords ? Les corrections manuelles seront supprimées et les accords issus de la dernière analyse seront restaurés.">'''
if needle in s:
    s=s.replace(needle,replacement,1)
elif 'app_song_chordslab_reset' in s and 'data-ez-confirm="Réinitialiser les accords ?' not in s:
    die('formulaire reset trouvé mais ancre inattendue')

# Remove the dedicated reset <dialog> completely.
start=s.find('<dialog class="ez-modal chord-reset-dialog" data-chord-reset-dialog>')
if start!=-1:
    end=s.find('</dialog>',start)
    if end==-1: die('fin dialog reset introuvable')
    s=s[:start]+s[end+len('</dialog>'):]

# Cache bust relevant scripts.
s=re.sub(r'/assets/js/chordslab-r33-2\.js\?v=[^"]+','/assets/js/chordslab-r33-2.js?v=20260928r35_10',s)
s=re.sub(r'/assets/js/chordslab\.js\?v=[^"]+','/assets/js/chordslab.js?v=20260928r35_10',s)
wr(p,s)

# 3) Remove legacy dedicated-reset JS. Global ez-modal handles data-ez-confirm.
p=root/'public/assets/js/chordslab-r33-2.js'
s=rd(p)
for decl in [
    "const resetDialog=document.querySelector('[data-chord-reset-dialog]');\n",
    "const resetCancel=resetDialog?.querySelector('[data-chord-reset-cancel]');\n",
    "const resetConfirm=resetDialog?.querySelector('[data-chord-reset-confirm]');\n",
]:
    s=s.replace(decl,'')
block_start=s.find('if(resetForm&&resetDialog){')
if block_start!=-1:
    block_end=s.find('\n}\n\nfunction updateQuickOutput',block_start)
    if block_end==-1: die('bloc JS reset introuvable')
    s=s[:block_start]+s[block_end+3:]
wr(p,s)

# Contract checks inside installer.
analysis=rd(root/'analysis/chord_timeline_analysis.py')
if 'return i//bpm,i%bpm' not in analysis: die('grille mesures complètes absente')
twig=rd(root/'templates/song/chordslab.html.twig')
if 'data-chord-reset-dialog' in twig: die('dialog reset encore présent')
if 'data-ez-confirm="Réinitialiser les accords ?' not in twig: die('confirmation reset ciblée absente')
js=rd(root/'public/assets/js/chordslab-r33-2.js')
if 'resetDialog' in js or 'resetConfirm' in js: die('ancien JS reset encore présent')

print('R35_10_APPLIED_OK')
