#!/usr/bin/env python3
from __future__ import annotations

import re, shutil, subprocess, sys
from pathlib import Path

BASE_COMMIT = 'e1f473758bb813d620c08e00cc740cc1e20d844e'
ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else r'H:\EZScore_v1').resolve()
RELS = {
    'chords_js':'public/assets/js/chordslab.js',
    'chords_css':'public/assets/css/chordslab.css',
    'chords_twig':'templates/song/chordslab.html.twig',
    'lyrics_js':'public/assets/js/lyricslab-timeline-r39.js',
    'lyrics_css':'public/assets/css/lyricslab-r37.css',
    'lyrics_twig':'templates/song/lyricslab.html.twig',
}
FILES={k:ROOT/v for k,v in RELS.items()}

def git(*args):
    return subprocess.run(['git',*args],cwd=str(ROOT),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace',check=False)

def git_show(rel):
    p=git('show',f'HEAD:{rel}')
    if p.returncode!=0: raise RuntimeError(f'git show HEAD:{rel} failed: {p.stderr.strip()}')
    return p.stdout.replace('\r\n','\n').replace('\r','\n').lstrip('\ufeff')

def rep(text,old,new,label):
    n=text.count(old)
    if n!=1: raise RuntimeError(f'{label}: expected 1 anchor, found {n}')
    return text.replace(old,new,1)

def regex_rep(text,pattern,repl,label):
    new,n=re.subn(pattern,repl,text,count=1)
    if n!=1: raise RuntimeError(f'{label}: expected 1 regex anchor, found {n}')
    return new

def write_atomic(path,text):
    tmp=path.with_suffix(path.suffix+'.r41i.tmp')
    tmp.write_text(text,encoding='utf-8',newline='\n')
    tmp.replace(path)

def cache_clear(env_name):
    php=shutil.which('php')
    if not php: raise RuntimeError('PHP introuvable dans PATH. STOP.')
    p=subprocess.run([php,'bin/console','cache:clear',f'--env={env_name}'],cwd=str(ROOT),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',check=False)
    print(p.stdout,end='')
    if p.returncode!=0: raise RuntimeError(f'cache:clear --env={env_name} failed with code {p.returncode}')

def guard():
    h=git('rev-parse','HEAD')
    if h.returncode!=0: raise RuntimeError('git rev-parse HEAD failed')
    actual=h.stdout.strip()
    if actual!=BASE_COMMIT: raise RuntimeError(f'HEAD={actual}; expected {BASE_COMMIT}. STOP.')
    if git('diff','--quiet').returncode!=0: raise RuntimeError('Tracked working-tree changes detected. STOP.')
    if git('diff','--cached','--quiet').returncode!=0: raise RuntimeError('Staged changes detected. STOP.')

def main():
    guard()
    original={k:p.read_bytes() for k,p in FILES.items()}
    src={k:git_show(v) for k,v in RELS.items()}
    cj,cc,ct=src['chords_js'],src['chords_css'],src['chords_twig']
    lj,lc,lt=src['lyrics_js'],src['lyrics_css'],src['lyrics_twig']
    baseline=[
      ("const measuresEl=root.querySelector('[data-chordslab-measures]');" in cj,'Chords measures anchor'),
      ("diagramToggle?.addEventListener('change',()=>{if(!diagramToggle.checked&&diagramEl)diagramEl.hidden=true});" in cj,'Chords broken toggle handler'),
      ('padding-top:164px!important;' in cc,'Chords R39.3 padding'),
      ('min-height:220px;' in cc,'Chords R39.3 min-height'),
      ("const stage=host.querySelector('[data-stage]')" in lj,'Lyrics stage anchor'),
      ("diagramToggle?.addEventListener('change',()=>renderAt(lastTime,true));" in lj,'Lyrics rerender'),
      ('height:392px!important;' in lc,'Lyrics expanded height'),
      ('top:174px!important;' in lc,'Lyrics expanded chord top'),
      ('top:284px!important;' in lc,'Lyrics expanded lyrics top'),
      ('chordslab.js?v=' in ct,'Chords JS cache'),
      ('chordslab.css?v=' in ct,'Chords CSS cache'),
      ('lyricslab-timeline-r39.js?v=' in lt,'Lyrics JS cache'),
      ('lyricslab-r37.css?v=' in lt,'Lyrics CSS cache'),
    ]
    bad=[name for ok,name in baseline if not ok]
    if bad: raise RuntimeError('R41.0I baseline mismatch: '+', '.join(bad)+'. STOP.')
    try:
        cj=rep(cj,"const measuresEl=root.querySelector('[data-chordslab-measures]');\n","const measuresEl=root.querySelector('[data-chordslab-measures]');\nconst stageEl=measuresEl?.closest('.chordslab-stage');\n",'Chords stage')
        cj=rep(cj,'function highlightAt(seconds){\n const ms=seconds*1000;','let lastPlaybackSeconds=0;\nfunction highlightAt(seconds){\n lastPlaybackSeconds=Math.max(0,Number(seconds)||0);\n const ms=lastPlaybackSeconds*1000;','Chords last time')
        old_handler="diagramToggle?.addEventListener('change',()=>{if(!diagramToggle.checked&&diagramEl)diagramEl.hidden=true});"
        new_handler="function syncDiagramLayout(){\n const expanded=Boolean(diagramToggle?.checked);\n stageEl?.classList.toggle('is-diagram-collapsed',!expanded);\n if(!expanded){\n  updateDiagram(null);\n  return;\n }\n highlightAt(lastPlaybackSeconds);\n}\ndiagramToggle?.addEventListener('change',syncDiagramLayout);\nsyncDiagramLayout();"
        cj=rep(cj,old_handler,new_handler,'Chords toggle')
        cc=cc.rstrip()+'\n\n'+'/* R41.0I — reclaim the complete diagram reservation when guitar chords are hidden.\n   R39.3 remains unchanged when the toggle is enabled. */\n.chordslab-stage.is-diagram-collapsed{\n    padding-top:0!important;\n    min-height:0!important;\n}\n@media(max-width:640px){\n    .chordslab-stage.is-diagram-collapsed{\n        padding-top:0!important;\n        min-height:0!important;\n    }\n}\n'
        ct=regex_rep(ct,r'/assets/css/chordslab\.css\?v=[^\"\']+', '/assets/css/chordslab.css?v=20261001r41_0i','Chords CSS cache')
        ct=regex_rep(ct,r'/assets/js/chordslab\.js\?v=[^\"\']+', '/assets/js/chordslab.js?v=20261001r41_0i','Chords JS cache')
        lj=rep(lj," const stage=host.querySelector('[data-stage]'),diagram=host.querySelector('[data-lyrics-stage-diagram]'),zone=host.querySelector('[data-reading-zone]'),track=host.querySelector('[data-track]'),chordLane=host.querySelector('[data-chords-lane]'),syllableLane=host.querySelector('[data-syllables-lane]');\n"," const stage=host.querySelector('[data-stage]'),stageShell=host.closest('.chordslab-stage'),diagram=host.querySelector('[data-lyrics-stage-diagram]'),zone=host.querySelector('[data-reading-zone]'),track=host.querySelector('[data-track]'),chordLane=host.querySelector('[data-chords-lane]'),syllableLane=host.querySelector('[data-syllables-lane]');\n",'Lyrics stage')
        lj=rep(lj,'  const bi=timeline.beatIndexAtMs(ms);if(force||bi!==lastBeat){lastBeat=bi;chordLane.querySelectorAll(\'.current\').forEach(e=>e.classList.remove(\'current\'));chordLane.querySelector(`.lyrics-ribbon-beat[data-beat-seq="${bi}"]`)?.classList.add(\'current\')}\n  if(diagram){\n','  const bi=timeline.beatIndexAtMs(ms);if(force||bi!==lastBeat){lastBeat=bi;chordLane.querySelectorAll(\'.current\').forEach(e=>e.classList.remove(\'current\'));chordLane.querySelector(`.lyrics-ribbon-beat[data-beat-seq="${bi}"]`)?.classList.add(\'current\')}\n  const diagramExpanded=Boolean(diagramToggle?.checked);\n  stage.classList.toggle(\'is-diagram-collapsed\',!diagramExpanded);\n  stageShell?.classList.toggle(\'is-diagram-collapsed\',!diagramExpanded);\n  if(diagram){\n','Lyrics compact state')
        lj=rep(lj,"   if(diagramToggle?.checked&&label&&label!=='.'){diagram.hidden=false;window.EZScoreChordDiagram?.render(diagram,label)}\n","   if(diagramExpanded&&label&&label!=='.'){diagram.hidden=false;window.EZScoreChordDiagram?.render(diagram,label)}\n",'Lyrics diagram state')
        lc=lc.rstrip()+'\n\n'+'/* R41.0I — true compact LyricsLab geometry when the guitar diagram is hidden.\n   Timeline x/time geometry is unchanged; only vertical layout is reclaimed. */\n[data-lyricslab] .chordslab-stage.is-diagram-collapsed{\n    min-height:236px!important;\n}\n[data-lyricslab] .r39-shared-timeline.is-diagram-collapsed{\n    height:236px!important;\n}\n[data-lyricslab] .r39-shared-timeline.is-diagram-collapsed .lyrics-reading-zone{\n    top:18px!important;\n}\n[data-lyricslab] .r39-shared-timeline.is-diagram-collapsed .lyrics-ribbon-chords{\n    top:18px!important;\n}\n[data-lyricslab] .r39-shared-timeline.is-diagram-collapsed .lyrics-ribbon-syllables{\n    top:128px!important;\n}\n'
        lt=regex_rep(lt,r'/assets/css/lyricslab-r37\.css\?v=[^\"\']+', '/assets/css/lyricslab-r37.css?v=20261001r41_0i','Lyrics CSS cache')
        lt=regex_rep(lt,r'/assets/js/lyricslab-timeline-r39\.js\?v=[^\"\']+', '/assets/js/lyricslab-timeline-r39.js?v=20261001r41_0i','Lyrics JS cache')
        contracts=[
          ("stageEl=measuresEl?.closest('.chordslab-stage')" in cj,'Chords stage target'),
          ('let lastPlaybackSeconds=0;' in cj,'Chords last time'),
          ('function syncDiagramLayout()' in cj,'Chords sync function'),
          ("diagramToggle?.addEventListener('change',syncDiagramLayout);" in cj,'Chords toggle listener'),
          ('.chordslab-stage.is-diagram-collapsed' in cc,'Chords compact CSS'),
          ('padding-top:0!important;' in cc,'Chords zero padding'),
          ('min-height:0!important;' in cc,'Chords zero min-height'),
          ("stageShell=host.closest('.chordslab-stage')" in lj,'Lyrics stage shell'),
          ('const diagramExpanded=Boolean(diagramToggle?.checked);' in lj,'Lyrics toggle state'),
          ('.r39-shared-timeline.is-diagram-collapsed' in lc,'Lyrics compact CSS'),
          ('height:236px!important;' in lc,'Lyrics compact height'),
          ('top:18px!important;' in lc,'Lyrics compact chord top'),
          ('top:128px!important;' in lc,'Lyrics compact lyric top'),
          ('/assets/css/chordslab.css?v=20261001r41_0i' in ct,'Chords CSS cache applied'),
          ('/assets/js/chordslab.js?v=20261001r41_0i' in ct,'Chords JS cache applied'),
          ('/assets/css/lyricslab-r37.css?v=20261001r41_0i' in lt,'Lyrics CSS cache applied'),
          ('/assets/js/lyricslab-timeline-r39.js?v=20261001r41_0i' in lt,'Lyrics JS cache applied'),
          ('new Audio(' not in cj and 'new AudioContext' not in cj,'Chords no parallel audio'),
          ('new Audio(' not in lj and 'new AudioContext' not in lj,'Lyrics no parallel audio'),
          ('EZScoreTimelineCoreR39' in lj,'Lyrics canonical timeline'),
        ]
        failed=[name for ok,name in contracts if not ok]
        if failed: raise RuntimeError('R41.0I invariant failed: '+', '.join(failed))
        write_atomic(FILES['chords_js'],cj); write_atomic(FILES['chords_css'],cc); write_atomic(FILES['chords_twig'],ct)
        write_atomic(FILES['lyrics_js'],lj); write_atomic(FILES['lyrics_css'],lc); write_atomic(FILES['lyrics_twig'],lt)
        print('[CACHE] Clearing Symfony dev cache...')
        cache_clear('dev')
        print('[CACHE] Clearing Symfony prod cache...')
        cache_clear('prod')
        print('R41_0I_CHORDS_LYRICS_COMPACT_TOGGLE_INSTALL_OK')
        return 0
    except Exception:
        for k,data in original.items(): FILES[k].write_bytes(data)
        try:
            print('[ROLLBACK] Re-clearing Symfony dev cache on restored files...')
            cache_clear('dev')
        except Exception as e:
            print(f'[ROLLBACK WARNING] dev cache clear failed: {e}',file=sys.stderr)
        try:
            print('[ROLLBACK] Re-clearing Symfony prod cache on restored files...')
            cache_clear('prod')
        except Exception as e:
            print(f'[ROLLBACK WARNING] prod cache clear failed: {e}',file=sys.stderr)
        raise

if __name__=='__main__':
    try: raise SystemExit(main())
    except Exception as exc:
        print(f'ERROR: {exc}',file=sys.stderr)
        raise SystemExit(1)
