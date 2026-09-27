#!/usr/bin/env python3
from pathlib import Path
import sys,re

def die(msg):
    raise SystemExit('R35.7 ABORT: '+msg)

def rd(p):
    return p.read_text(encoding='utf-8-sig')

def wr(p,s):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(s,encoding='utf-8',newline='\n')

def rep(s,a,b,label):
    if a not in s:
        die('ancre absente: '+label)
    return s.replace(a,b,1)

root=Path(sys.argv[1] if len(sys.argv)>1 else '.').resolve()
for rel in [
 'templates/base.html.twig',
 'templates/song/edit.html.twig',
 'templates/catalog/index.html.twig',
 'templates/song/chordslab.html.twig',
 'src/Controller/SongLabController.php',
 'src/Service/SongChordJobService.php',
 'worker_app/ezscore_analysis_worker.pyw',
 'analysis/chord_timeline_analysis.py',
 'public/assets/js/audio/ezscore-audio-engine.js'
]:
    if not (root/rel).is_file():
        die('fichier absent: '+rel)

# Popup audio
p=root/'templates/song/edit.html.twig'; s=rd(p)
s=s.replace('onclick="return confirm(\'{{ \'song.edit.audio.confirm\'|trans|e(\'js\') }}\')"',
            'data-ez-confirm="{{ \'song.edit.audio.confirm\'|trans|e(\'html_attr\') }}"')
wr(p,s)

# Popup suppression catalogue
p=root/'templates/catalog/index.html.twig'; s=rd(p)
s=re.sub(r'onsubmit="return confirm\(\'([^\']*(?:\'[^)]*)?)\'\);"',
         r'data-ez-confirm="\1"',s)
wr(p,s)

# Base assets/modal
p=root/'templates/base.html.twig'; s=rd(p)
if '/assets/css/ez-modal.css' not in s:
    a='    <link rel="stylesheet" href="/assets/css/interactions.css?v=20260924f">'
    s=rep(s,a,a+'\n    <link rel="stylesheet" href="/assets/css/ez-modal.css?v=20260928r35_7">','modal css')
if '/assets/js/ez-modal.js' not in s:
    a='<script src="/assets/js/dirty-tracker.js?v=20260924"></script>'
    s=rep(s,a,a+'\n<script src="/assets/js/ez-modal.js?v=20260928r35_7"></script>','modal js')
if 'data-ez-confirm-modal' not in s:
    a='{% if app.user %}</div>{% endif %}'
    b='''{% if app.user %}</div>{% endif %}
<div class="ez-modal-backdrop" data-ez-confirm-modal hidden>
<section class="ez-modal" role="dialog" aria-modal="true" aria-labelledby="ez-confirm-title">
<div class="ez-modal-icon" aria-hidden="true">!</div>
<div class="ez-modal-copy"><div class="eyebrow">Confirmation</div><h2 id="ez-confirm-title">Confirmer l’action</h2><p data-ez-confirm-message></p></div>
<div class="ez-modal-actions"><button type="button" data-ez-confirm-cancel>Annuler</button><button type="button" class="danger-soft" data-ez-confirm-ok>Confirmer</button></div>
</section></div>'''
    s=rep(s,a,b,'modal markup')
wr(p,s)

wr(root/'public/assets/css/ez-modal.css', '.ez-modal-backdrop{position:fixed;inset:0;z-index:9999;display:grid;place-items:center;padding:24px;background:rgba(0,0,0,.72);backdrop-filter:blur(5px)}.ez-modal-backdrop[hidden]{display:none}.ez-modal{width:min(560px,100%);display:grid;grid-template-columns:auto 1fr;gap:18px;padding:24px;border:1px solid rgba(255,255,255,.18);border-radius:18px;background:#11161b;box-shadow:0 28px 80px rgba(0,0,0,.55)}.ez-modal-icon{width:46px;height:46px;display:grid;place-items:center;border-radius:50%;background:rgba(255,181,71,.14);border:1px solid rgba(255,181,71,.4);font-size:24px;font-weight:900}.ez-modal-copy h2{margin:.15rem 0 .55rem}.ez-modal-copy p{margin:0;line-height:1.5;color:rgba(255,255,255,.78)}.ez-modal-actions{grid-column:1/-1;display:flex;justify-content:flex-end;gap:10px;margin-top:6px}@media(max-width:600px){.ez-modal{grid-template-columns:1fr}.ez-modal-actions{grid-column:auto}}')
wr(root/'public/assets/js/ez-modal.js', '''(() => {
'use strict';
const modal=document.querySelector('[data-ez-confirm-modal]'); if(!modal)return;
const message=modal.querySelector('[data-ez-confirm-message]'),ok=modal.querySelector('[data-ez-confirm-ok]'),cancel=modal.querySelector('[data-ez-confirm-cancel]');
let pending=null,lastFocus=null;
const close=()=>{modal.hidden=true;pending=null;if(lastFocus?.focus)lastFocus.focus();};
const open=(text,action,focusEl)=>{pending=action;lastFocus=focusEl||document.activeElement;message.textContent=text||'Confirmer cette action ?';modal.hidden=false;setTimeout(()=>cancel.focus(),0);};
document.addEventListener('click',e=>{const trigger=e.target.closest('[data-ez-confirm]');if(!trigger)return;const text=trigger.getAttribute('data-ez-confirm')||'Confirmer cette action ?';const form=trigger.form;if(form&&trigger.type==='submit'){if(trigger.dataset.ezConfirmed==='1'){delete trigger.dataset.ezConfirmed;return}e.preventDefault();open(text,()=>{trigger.dataset.ezConfirmed='1';form.requestSubmit(trigger)},trigger)}else if(trigger.tagName==='A'){e.preventDefault();open(text,()=>location.href=trigger.href,trigger)}});
document.addEventListener('submit',e=>{const form=e.target.closest('form[data-ez-confirm]');if(!form||form.dataset.ezConfirmed==='1')return;e.preventDefault();open(form.getAttribute('data-ez-confirm'),()=>{form.dataset.ezConfirmed='1';form.requestSubmit()},form)});
ok.addEventListener('click',()=>{const fn=pending;modal.hidden=true;pending=null;if(fn)fn()});cancel.addEventListener('click',close);modal.addEventListener('click',e=>{if(e.target===modal)close()});document.addEventListener('keydown',e=>{if(!modal.hidden&&e.key==='Escape')close()});
})();''')

# noise option UI
p=root/'templates/song/chordslab.html.twig'; s=rd(p)
if 'name="filter_noise"' not in s:
    a='''                <input type="hidden" name="_token" value="{{ csrf_token('song_chordslab_analyze_' ~ song.id) }}">'''
    b=a+'''
                <label class="chord-analysis-noise-filter"><input type="checkbox" name="filter_noise" value="1"><span>Filtrer applaudissements / foule pour l’analyse</span></label>'''
    s=rep(s,a,b,'filter noise checkbox')
wr(p,s)

# controller/job request
p=root/'src/Controller/SongLabController.php'; s=rd(p)
s=s.replace('$chordJobs->queue($song, $user);','$chordJobs->queue($song, $user, $request->request->getBoolean(\'filter_noise\'));',1)
wr(p,s)

p=root/'src/Service/SongChordJobService.php'; s=rd(p)
s=s.replace('public function queue(Song $song, User $user): AnalysisJob','public function queue(Song $song, User $user, bool $filterNoise = false): AnalysisJob',1)
if "'filter_noise' => $filterNoise" not in s:
    a="            'time_signature' => $song->getTimeSignature(),"
    s=rep(s,a,a+"\n            'filter_noise' => $filterNoise,",'job filter noise')
wr(p,s)

# worker cli
p=root/'worker_app/ezscore_analysis_worker.pyw'; s=rd(p)
if '--filter-noise' not in s:
    a='''        if paths.get("drums"):
            command.extend(["--drums", str(paths["drums"])])
'''
    b=a+'''        if bool(request.get("filter_noise")):
            command.append("--filter-noise")
'''
    s=rep(s,a,b,'worker filter noise')
wr(p,s)

# analysis python
p=root/'analysis/chord_timeline_analysis.py'; s=rd(p)
if 'def suppress_crowd_noise' not in s:
    a='def load_mix(paths,sr=11025):'
    helper='''def suppress_crowd_noise(y,sr,hop=512):
    if y is None or len(y)<hop*4:return y,None
    harmonic,_=librosa.effects.hpss(y)
    flat=librosa.feature.spectral_flatness(y=y,hop_length=hop)[0]
    onset=librosa.onset.onset_strength(y=y,sr=sr,hop_length=hop)
    n=min(len(flat),len(onset))
    if n==0:return harmonic,None
    f=flat[:n];o=onset[:n]
    fz=(f-np.median(f))/(np.std(f)+1e-9);oz=(o-np.median(o))/(np.std(o)+1e-9)
    contaminated=(fz>0.85)&(oz>0.55)
    mask=np.ones(n,float);mask[contaminated]=0.18
    if len(mask)>=5:
        mask=np.clip(np.convolve(mask,np.ones(5)/5.0,mode="same"),.18,1.0)
    cleaned=.82*harmonic+.18*y
    return librosa.util.normalize(cleaned),mask

def extend_beats_to_zero(beat_times,duration,tempo):
    bt=np.asarray(beat_times,dtype=float)
    if bt.size==0:
        step=60.0/tempo if tempo>20 else .5
        return np.arange(0.0,duration,step,float),0
    diffs=np.diff(bt);positive=diffs[diffs>1e-4]
    step=float(np.median(positive)) if positive.size else (60.0/tempo if tempo>20 else .5)
    prepend=[];t=float(bt[0])-step
    while t>0.04:prepend.append(t);t-=step
    if bt[0]>step*.40:prepend.append(max(0.0,t))
    prepend=sorted(set(round(max(0.0,x),6) for x in prepend))
    return (np.concatenate([np.asarray(prepend,float),bt]),len(prepend)) if prepend else (bt,0)

'''
    s=rep(s,a,helper+a,'analysis helpers')

s=s.replace('def analyse(source,stems,drums,requested_signature,progress_file=None):','def analyse(source,stems,drums,requested_signature,progress_file=None,filter_noise=False):',1)

old='''    if drums and Path(drums).is_file():
        yr,_=librosa.load(str(drums),sr=sr,mono=True);yr=librosa.util.normalize(yr);rhythm_source="drums"
    else:
        yr=yh;rhythm_source=harmonic_source
'''
new='''    noise_mask=None
    if filter_noise:
        yh,noise_mask=suppress_crowd_noise(yh,sr)
    if drums and Path(drums).is_file():
        yr,_=librosa.load(str(drums),sr=sr,mono=True);yr=librosa.util.normalize(yr);rhythm_source="drums"
        if filter_noise:yr,_=suppress_crowd_noise(yr,sr)
    else:
        yr=yh;rhythm_source=harmonic_source
'''
if old in s:s=s.replace(old,new,1)

a='''    bpm=numerator(signature)

    prog(progress_file,32,"chroma","Extraction de l’harmonie")
'''
if 'extend_beats_to_zero(beat_times' not in s and a in s:
    b='''    bpm=numerator(signature)
    beat_times,prepended_count=extend_beats_to_zero(beat_times,duration,tempo)
    if prepended_count:phase=(phase+prepended_count)%max(1,bpm)

    prog(progress_file,32,"chroma","Extraction de l’harmonie")
'''
    s=s.replace(a,b,1)

s=s.replace('''        if silent[i]:
            labels.append(last);confs.append(0.0);continue''','''        if silent[i]:
            labels.append(".");confs.append(0.0);last=".";continue''',1)

if 'p.add_argument("--filter-noise"' not in s:
    s=s.replace('    p.add_argument("--time-signature",default="auto")','    p.add_argument("--time-signature",default="auto")\n    p.add_argument("--filter-noise",action="store_true")',1)
s=s.replace('result=analyse(Path(a.audio),a.stem,a.drums,a.time_signature,a.progress_file)','result=analyse(Path(a.audio),a.stem,a.drums,a.time_signature,a.progress_file,a.filter_noise)',1)
if 'guitar_accompaniment_from_full_harmony' not in s:
    s=s.replace('        "rhythm_source":rhythm_source,','        "rhythm_source":rhythm_source,\n        "noise_filter_enabled":bool(filter_noise),\n        "harmonic_goal":"guitar_accompaniment_from_full_harmony",',1)
wr(p,s)

# Warm-up Opus media as soon as the song/player page is opened.
p=root/'public/assets/js/audio/ezscore-audio-engine.js'; s=rd(p)
s=s.replace("media.preload = 'none';","media.preload = 'auto';",1)
if 'warmUp(options = {})' not in s:
    add_anchor='''        setTrackEnabled(key, enabled) {'''
    warm='''        warmUp(options = {}) {
            if (this.disposed) return Promise.resolve([]);
            const enabledFirst = options.enabledFirst !== false;
            const tracks = Array.from(this.tracks.values());
            const ordered = enabledFirst
                ? [...tracks.filter((t) => t.enabled), ...tracks.filter((t) => !t.enabled)]
                : tracks;
            this.dispatchEvent(new CustomEvent('statechange', {detail: {state: 'preloading'}}));
            return Promise.allSettled(
                ordered.map((track, index) => new Promise((resolve) => {
                    const delay = track.enabled ? 0 : Math.min(1200, 120 * index);
                    setTimeout(() => {
                        this._ensureTrackReady(track)
                            .then(resolve)
                            .catch((error) => {
                                this._trackFailure(track, error);
                                resolve(track);
                            });
                    }, delay);
                }))
            ).then((result) => {
                if (!this.disposed && !this.playing) {
                    this.dispatchEvent(new CustomEvent('statechange', {detail: {state: 'ready'}}));
                }
                return result;
            });
        }

'''
    s=rep(s,add_anchor,warm+add_anchor,'audio warmUp method')
if 'this.warmUp({enabledFirst: true})' not in s:
    add_anchor='''            this._setTrackState(track, 'idle');

            return track;'''
    repl='''            this._setTrackState(track, 'idle');

            // Start network/media warm-up without playback. Browser cache then
            // serves the first Play immediately or nearly immediately.
            queueMicrotask(() => {
                if (!this.disposed) this._ensureTrackReady(track).catch((error) => this._trackFailure(track, error));
            });

            return track;'''
    s=rep(s,add_anchor,repl,'audio addTrack warm-up')
wr(p,s)

# css
p=root/'public/assets/css/chordslab.css'
if p.is_file():
    s=rd(p)
    if '.chord-analysis-noise-filter' not in s:
        s+='\n.chord-analysis-noise-filter{display:inline-flex;align-items:center;gap:.55rem;margin-right:.75rem;font-size:.9rem}.chord-analysis-noise-filter input{width:18px;height:18px}\n'
    wr(p,s)

# Audit native popups
off=[]
for base in [root/'templates',root/'public/assets/js']:
    if base.exists():
        for f in base.rglob('*'):
            if f.is_file() and f.suffix.lower() in {'.twig','.js'}:
                txt=rd(f)
                if re.search(r'(?<![A-Za-z0-9_])(confirm|alert)\s*\(',txt):
                    off.append(str(f.relative_to(root)))
if off:
    die('popup navigateur restante: '+', '.join(off))

p=root/'readme.md'
if p.is_file():
    s=rd(p)
    if 'R35.7 ANALYSIS SYNC + NOISE + MODAL' not in s:
        s+='\n\n## R35.7 ANALYSIS SYNC + NOISE + MODAL\nModales EZScore, audit anti-popup navigateur, filtre foule/applaudissements optionnel, mesures vides conservées depuis le début, accords destinés à l’accompagnement guitare à partir de toute l’harmonie disponible.\n'
    wr(p,s)

print('R35_7_APPLIED_OK')
