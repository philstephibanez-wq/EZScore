#!/usr/bin/env python3
from pathlib import Path
import sys,re

def die(msg): raise SystemExit('R35.8 ABORT: '+msg)
def rd(p): return p.read_text(encoding='utf-8-sig')
def wr(p,s): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(s,encoding='utf-8',newline='\n')
def rep(s,a,b,label):
    if a not in s: die('ancre absente: '+label)
    return s.replace(a,b,1)

root=Path(sys.argv[1] if len(sys.argv)>1 else '.').resolve()
for rel in ['src/Domain/Song/Song.php','src/Controller/SongLabController.php','templates/song/chordslab.html.twig','templates/stems/index.html.twig','public/assets/js/chordslab.js','public/assets/js/stems-mixer.js','public/assets/js/audio/ezscore-audio-engine.js','analysis/chord_timeline_analysis.py']:
    if not (root/rel).is_file(): die('fichier absent: '+rel)

# 1) Persist optional crowd/applause filter on Song.
p=root/'src/Domain/Song/Song.php'; s=rd(p)
if 'private bool $chordNoiseFilterEnabled' not in s:
    a="""    #[ORM\\Column(name: 'chord_analysis_level', length: 16, options: ['default' => 'intermediate'])]\n    private string $chordAnalysisLevel = 'intermediate';\n"""
    b=a+"""\n    #[ORM\\Column(name: 'chord_noise_filter_enabled', options: ['default' => false])]\n    private bool $chordNoiseFilterEnabled = false;\n"""
    s=rep(s,a,b,'Song noise property')
if 'isChordNoiseFilterEnabled()' not in s:
    a="""    public function getChordAnalysisLevel(): string { return $this->chordAnalysisLevel; }\n"""
    b="""    public function isChordNoiseFilterEnabled(): bool { return $this->chordNoiseFilterEnabled; }\n    public function setChordNoiseFilterEnabled(bool $enabled): self { $this->chordNoiseFilterEnabled = $enabled; return $this->touch(); }\n\n"""+a
    s=rep(s,a,b,'Song noise getter/setter')
wr(p,s)

mig=root/'migrations/Version20260928013000.php'
if not mig.exists():
    wr(mig,"""<?php

declare(strict_types=1);
namespace DoctrineMigrations;
use Doctrine\\DBAL\\Schema\\Schema;
use Doctrine\\Migrations\\AbstractMigration;
final class Version20260928013000 extends AbstractMigration
{
    public function getDescription(): string { return 'Persist ChordsLab crowd/applause filter per song'; }
    public function up(Schema $schema): void { $this->addSql('ALTER TABLE songs ADD COLUMN chord_noise_filter_enabled BOOLEAN NOT NULL DEFAULT 0'); }
    public function down(Schema $schema): void { $this->addSql('ALTER TABLE songs DROP COLUMN chord_noise_filter_enabled'); }
}
""")

# 2) Controller persistence + reset visibility.
p=root/'src/Controller/SongLabController.php'; s=rd(p)
if "'has_chord_overrides'" not in s:
    a="""            'playback_ready' => $playback->isReady($song),\n        ]);\n"""
    b="""            'playback_ready' => $playback->isReady($song),\n            'has_chord_overrides' => (bool) array_filter(\n                $profiles[$activeProfile] ?? [],\n                static fn (array $event): bool => ($event['override'] ?? null) !== null && trim((string) $event['override']) !== ''\n            ),\n        ]);\n"""
    s=rep(s,a,b,'has chord overrides')
old="$chordJobs->queue($song, $user, $request->request->getBoolean('filter_noise'));"
if old in s:
    sig="""        SongChordJobService $chordJobs,\n        SongWorkflowState $workflow,\n    ): Response {\n"""
    if sig in s:
        s=s.replace(sig,"""        SongChordJobService $chordJobs,\n        SongWorkflowState $workflow,\n        EntityManagerInterface $em,\n    ): Response {\n""",1)
    s=s.replace(old,"""$filterNoise = $request->request->getBoolean('filter_noise');\n        $song->setChordNoiseFilterEnabled($filterNoise);\n        $em->flush();\n        $chordJobs->queue($song, $user, $song->isChordNoiseFilterEnabled());""",1)
if 'app_song_chordslab_noise_filter' not in s:
    a="""    #[Route('/chords/status', name: 'app_song_chordslab_status', methods: ['GET'])]\n"""
    method="""    #[Route('/chords/noise-filter', name: 'app_song_chordslab_noise_filter', methods: ['POST'])]\n    public function saveChordNoiseFilter(Song $song, Request $request, EntityManagerInterface $em): JsonResponse\n    {\n        $this->requireEditor($song);\n        $payload = $request->toArray();\n        if (!$this->isCsrfTokenValid('song_chordslab_noise_filter_'.$song->getId(), (string) ($payload['_token'] ?? ''))) {\n            return $this->json(['error' => 'invalid_csrf'], Response::HTTP_FORBIDDEN);\n        }\n        $song->setChordNoiseFilterEnabled((bool) ($payload['enabled'] ?? false));\n        $em->flush();\n        return $this->json(['ok' => true, 'enabled' => $song->isChordNoiseFilterEnabled()]);\n    }\n\n"""
    s=rep(s,a,method+a,'noise filter route')
old2="""        $chord = trim((string) ($payload['chord'] ?? ''));\n        // Plain major triads use standard compact spelling: C, not redundant Cmaj.\n"""
if old2 in s:
    s=s.replace(old2,"""        $chord = trim((string) ($payload['chord'] ?? ''));\n        $chord = preg_replace('/^\\[([^\\]]+)\\]$/', '$1', $chord) ?? $chord;\n        // Plain major triads use standard compact spelling: C, not redundant Cmaj.\n""",1)
wr(p,s)

# 3) ChordsLab persistent checkbox, reset only if overrides, cache bust.
p=root/'templates/song/chordslab.html.twig'; s=rd(p)
pat=r'''<label class="chord-analysis-noise-filter">\s*<input type="checkbox" name="filter_noise" value="1">\s*<span>Filtrer applaudissements / foule pour l’analyse</span>\s*</label>'''
repl='''<label class="chord-analysis-noise-filter">\n                    <input type="checkbox" name="filter_noise" value="1" data-noise-filter\n                           data-save-url="{{ path('app_song_chordslab_noise_filter', {'_locale': app.request.locale, id: song.id}) }}"\n                           data-save-token="{{ csrf_token('song_chordslab_noise_filter_' ~ song.id) }}"\n                           {{ song.chordNoiseFilterEnabled ? 'checked' : '' }}>\n                    <span>Filtrer applaudissements / foule pour l’analyse</span>\n                </label>'''
s2,n=re.subn(pat,repl,s,count=1,flags=re.S)
if n==0 and 'data-noise-filter' not in s: die('checkbox R35.7 introuvable')
s=s2
s=s.replace("{% if chord_events %}\n            <form method=\"post\"\n                  action=\"{{ path('app_song_chordslab_reset'","{% if has_chord_overrides %}\n            <form method=\"post\"\n                  action=\"{{ path('app_song_chordslab_reset'",1)
s=re.sub(r'/assets/js/audio/ezscore-audio-engine\.js\?v=[^"]+','/assets/js/audio/ezscore-audio-engine.js?v=20260928r35_8',s)
s=re.sub(r'/assets/js/stems-mixer\.js\?v=[^"]+','/assets/js/stems-mixer.js?v=20260928r35_8',s)
s=re.sub(r'/assets/js/chordslab\.js\?v=[^"]+','/assets/js/chordslab.js?v=20260928r35_8',s)
wr(p,s)

p=root/'templates/stems/index.html.twig'; s=rd(p)
s=re.sub(r'/assets/js/audio/ezscore-audio-engine\.js\?v=[^"]+','/assets/js/audio/ezscore-audio-engine.js?v=20260928r35_8',s)
s=re.sub(r'/assets/js/stems-mixer\.js\?v=[^"]+','/assets/js/stems-mixer.js?v=20260928r35_8',s)
wr(p,s)

# 4) Explicit Opus warm-up on page load.
p=root/'public/assets/js/stems-mixer.js'; s=rd(p)
if 'engine.warmUp({enabledFirst: true})' not in s:
    a="""    engine.setMasterVolume(Number(els.volume?.value || 1));\n"""
    b="""    // R35.8: prepare Opus immediately, without autoplay.\n    queueMicrotask(() => {\n        if (typeof engine.warmUp === 'function') engine.warmUp({enabledFirst: true}).catch?.(() => {});\n    });\n\n"""+a
    s=rep(s,a,b,'mixer warmup')
wr(p,s)
p=root/'public/assets/js/audio/ezscore-audio-engine.js'; s=rd(p); s=s.replace("media.preload = 'none';","media.preload = 'auto';",1); wr(p,s)

# 5) No [] in framed chords + explicit dots across no-harmony beats + filter autosave.
p=root/'public/assets/js/chordslab.js'; s=rd(p)
old="""function normaliseLabel(chord){\n if(!chord)return chord;\n return chord.replace(/^([A-G](?:#|b)?)maj$/,'$1');\n}\n"""
if old in s:
    s=s.replace(old,"""function normaliseLabel(chord){\n if(!chord)return chord;\n chord=String(chord).trim().replace(/^\\[([^\\]]+)\\]$/,'$1');\n return chord.replace(/^([A-G](?:#|b)?)maj$/,'$1');\n}\n""",1)
old="""  if(exact)text=displayChord(exact.effective||exact.original||'.');\n  else if(beatIndex===0)text=displayChord(active?.effective||active?.original||'.');\n"""
if old in s:
    s=s.replace(old,"""  if(exact)text=displayChord(exact.effective||exact.original||'.');\n  else if((active?.effective||active?.original||'')==='.')text='.';\n  else if(beatIndex===0)text=displayChord(active?.effective||active?.original||'.');\n""",1)
if "const noiseFilter=document.querySelector('[data-noise-filter]');" not in s:
    a="""const analyzeConfirm=analyzeDialog?.querySelector('[data-chord-analyze-confirm]');\n"""
    s=rep(s,a,a+"const noiseFilter=document.querySelector('[data-noise-filter]');\n",'noise const')
if 'noise_filter_http_' not in s:
    a="""if(!measuresEl||!beats.length)return;\n"""
    listener="""if(noiseFilter){\n noiseFilter.addEventListener('change',async()=>{\n  const url=noiseFilter.dataset.saveUrl,token=noiseFilter.dataset.saveToken;if(!url||!token)return;\n  try{const response=await fetch(url,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','Accept':'application/json'},body:JSON.stringify({_token:token,enabled:noiseFilter.checked})});if(!response.ok)throw new Error(`noise_filter_http_${response.status}`)}catch(_){noiseFilter.checked=!noiseFilter.checked}\n });\n}\n"""
    s=rep(s,a,listener+a,'noise autosave')
wr(p,s)

# 6) Analysis: timeline always exists from MP3 t=0 and no-harmony beats become '.'.
p=root/'analysis/chord_timeline_analysis.py'; s=rd(p)
s,n=re.subn(r'''def extend_beats_to_zero\(beat_times,duration,tempo\):.*?\n(?=def load_mix)''', '''def extend_beats_to_zero(beat_times,duration,tempo):\n    """Preserve detected beats but guarantee that the prompter exists from MP3 t=0."""\n    bt=np.asarray(beat_times,dtype=float)\n    if bt.size==0:\n        step=60.0/tempo if tempo>20 else .5\n        return np.arange(0.0,max(duration,step)+step*.25,step,float),0\n    diffs=np.diff(bt);positive=diffs[diffs>1e-4]\n    step=float(np.median(positive)) if positive.size else (60.0/tempo if tempo>20 else .5)\n    step=max(.12,min(3.0,step))\n    if bt[0] <= max(.045,step*.10):\n        bt=bt.copy();bt[0]=0.0\n        return bt,0\n    prepend=[];t=float(bt[0])-step\n    while t>max(.045,step*.10):\n        prepend.append(t);t-=step\n    prepend.append(0.0)\n    prepend=np.asarray(sorted(set(round(max(0.0,x),6) for x in prepend)),dtype=float)\n    return np.concatenate([prepend,bt]),len(prepend)\n\n''',s,count=1,flags=re.S)
if n==0: die('extend_beats_to_zero introuvable')
a="""    rms=librosa.feature.rms(y=yh,hop_length=hop)[0]\n    floor=float(np.percentile(rms,12)) if rms.size else 0.0\n"""
if 'spectral_flatness=librosa.feature.spectral_flatness' not in s:
    s=rep(s,a,a+"    spectral_flatness=librosa.feature.spectral_flatness(y=yh,hop_length=hop)[0]\n",'flatness')
old="""        local=float(np.mean(rr))\n        is_silent=local<=max(.0025,floor*.50) or float(np.sum(segment))<=1e-6\n        silent.append(is_silent)\n        beat_vectors.append(segment/max(float(np.linalg.norm(segment)),1e-9) if not is_silent else np.zeros(12))\n"""
new="""        local=float(np.mean(rr))\n        energy_silent=local<=max(.0025,floor*.50) or float(np.sum(segment))<=1e-6\n        total=float(np.sum(segment))\n        if total>1e-9:\n            ordered=np.sort(segment);top3_ratio=float(np.sum(ordered[-3:])/total);peak_ratio=float(ordered[-1]/total)\n        else:\n            top3_ratio=0.0;peak_ratio=0.0\n        ff=spectral_flatness[min(f0,len(spectral_flatness)-1):min(max(f1,f0+1),len(spectral_flatness))] if spectral_flatness.size else np.array([0.0])\n        local_flatness=float(np.mean(ff))\n        has_harmony=(not energy_silent and top3_ratio>=0.36 and peak_ratio>=0.105 and local_flatness<=0.42)\n        no_harmony=not has_harmony\n        silent.append(no_harmony)\n        beat_vectors.append(segment/max(float(np.linalg.norm(segment)),1e-9) if has_harmony else np.zeros(12))\n"""
if old in s: s=s.replace(old,new,1)
elif 'top3_ratio' not in s: die('classification harmonie introuvable')
s=s.replace('"version":"r34-three-profiles"','"version":"r35.8-absolute-timeline"',1)
wr(p,s)

p=root/'readme.md'
if p.is_file():
    t=rd(p)
    if 'R35.8 TIMELINE / PERSIST / PRELOAD' not in t:
        t+='\n\n## R35.8 TIMELINE / PERSIST / PRELOAD\nTimeline absolue depuis t=0, mesures sans harmonie en points, filtre live persisté, préchargement Opus à l’ouverture, reset uniquement si overrides, suppression des crochets.\n'
    wr(p,t)
print('R35_8_APPLIED_OK')
