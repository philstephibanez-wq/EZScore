#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
import librosa

NOTES=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
MAJOR=np.array([6.35,2.23,3.48,2.33,4.38,4.09,2.52,5.19,2.39,3.66,2.29,2.88],float)
MINOR=np.array([6.33,2.68,3.52,5.38,2.60,3.53,2.54,4.75,3.98,2.69,3.34,3.17],float)
TRIADS={'major':([0,4,7],''),'minor':([0,3,7],'m')}
INTER={'7':([0,4,7,10],'7'),'min7':([0,3,7,10],'m7'),'sus2':([0,2,7],'sus2'),'sus4':([0,5,7],'sus4'),'dim':([0,3,6],'dim')}
EXTRA={'maj7':([0,4,7,11],'maj7'),'aug':([0,4,8],'aug'),'6':([0,4,7,9],'6'),'min6':([0,3,7,9],'m6'),'add9':([0,2,4,7],'add9')}

def cosine(a,b):
    d=float(np.linalg.norm(a)*np.linalg.norm(b)); return 0.0 if d<=1e-12 else float(np.dot(a,b)/d)

def detect_key(chroma):
    x=np.mean(chroma,axis=1)
    if float(np.sum(x))<=1e-9:return None,None
    x=x/max(float(np.linalg.norm(x)),1e-9);best=(None,None,-1e9)
    for root in range(12):
        for prof,mode,sfx in ((np.roll(MAJOR,root),'major',''),(np.roll(MINOR,root),'minor','m')):
            s=cosine(x,prof)
            if s>best[2]:best=(root,mode,s)
    return NOTES[best[0]]+('' if best[1]=='major' else 'm'),(best[0],best[1])

def diatonic(key):
    if key is None:return set()
    root,mode=key;ints=[0,2,4,5,7,9,11] if mode=='major' else [0,2,3,5,7,8,10]
    return {(root+i)%12 for i in ints}

def tmpl(root,ints):
    v=np.full(12,.04,float);v[root]=1.35
    for i in ints:v[(root+i)%12]=1.0
    return v/max(float(np.linalg.norm(v)),1e-9)

def candidates(level):
    q=dict(TRIADS)
    if level=='intermediate':q.update(INTER)
    elif level=='expert':q.update(INTER);q.update(EXTRA)
    out=[]
    for root in range(12):
        for name,(ints,sfx) in q.items():
            penalty=0.0 if name in TRIADS else (.075 if level=='intermediate' else .025)
            out.append((root,name,NOTES[root]+sfx,tmpl(root,ints),penalty))
    return out

def meter(onset,frames):
    if len(frames)<12:return '4/4'
    st=onset[np.clip(frames,0,len(onset)-1)];st=(st-np.mean(st))/(np.std(st)+1e-9)
    def sc(p):
        m=[float(np.mean(st[np.arange(len(st))%p==phase])) for phase in range(p)]
        return max(m)-float(np.mean(m))
    scores={'3/4':sc(3),'4/4':sc(4),'6/8':sc(6)};ordered=sorted(scores.items(),key=lambda kv:kv[1],reverse=True)
    return '4/4' if ordered[0][1]-ordered[1][1]<.10 else ordered[0][0]

def nbeats(sig):
    try:return max(1,int(sig.split('/',1)[0]))
    except:return 4

def load_mix(paths,sr=11025):
    ys=[];mx=0
    for p in paths:
        if not p or not Path(p).is_file():continue
        y,_=librosa.load(str(p),sr=sr,mono=True);ys.append(y);mx=max(mx,len(y))
    if not ys:raise RuntimeError('no usable harmony source')
    mix=np.zeros(mx,np.float32)
    for y in ys:mix[:len(y)]+=y.astype(np.float32)
    mix/=len(ys);return librosa.util.normalize(mix),sr

def analyse(audio,stems,drums,level,requested_sig):
    stem_paths=[p for p in stems if Path(p).is_file()]
    y,sr=load_mix(stem_paths or [audio]);harmony_source='stems' if stem_paths else 'original'
    if drums and Path(drums).is_file():yr,_=librosa.load(str(drums),sr=sr,mono=True);yr=librosa.util.normalize(yr);rhythm_source='drums'
    else:yr=y;rhythm_source=harmony_source
    hop=512;onset=librosa.onset.onset_strength(y=yr,sr=sr,hop_length=hop)
    tempo_v,frames=librosa.beat.beat_track(onset_envelope=onset,sr=sr,hop_length=hop,trim=False)
    frames=np.asarray(frames,int);times=librosa.frames_to_time(frames,sr=sr,hop_length=hop)
    tempo=float(np.asarray(tempo_v).reshape(-1)[0]) if np.asarray(tempo_v).size else 0.0
    dur=float(librosa.get_duration(y=y,sr=sr))
    if len(times)<4:
        step=60.0/tempo if tempo>20 else .5;times=np.arange(0,dur,step);frames=librosa.time_to_frames(times,sr=sr,hop_length=hop)
    sig=meter(onset,frames) if requested_sig=='auto' else requested_sig;per_measure=nbeats(sig)
    chroma=np.maximum(librosa.feature.chroma_cqt(y=y,sr=sr,hop_length=hop),0.0)
    key_name,key_info=detect_key(chroma);scale=diatonic(key_info);cands=candidates(level)
    rms=librosa.feature.rms(y=y,hop_length=hop)[0];floor=float(np.percentile(rms,12)) if rms.size else 0.0
    scores=[];silence=[]
    for i,start in enumerate(times):
        end=times[i+1] if i+1<len(times) else min(dur,start+max(.25,60/max(tempo,60)))
        f0=max(0,int(librosa.time_to_frames(start,sr=sr,hop_length=hop)));f1=min(chroma.shape[1],max(f0+1,int(librosa.time_to_frames(end,sr=sr,hop_length=hop))))
        if f0>=chroma.shape[1]:scores.append(np.full(len(cands),-9.0));silence.append(True);continue
        segm=np.mean(chroma[:,f0:f1],axis=1);local=float(np.mean(rms[min(f0,len(rms)-1):min(max(f1,f0+1),len(rms))])) if rms.size else 1.0
        silent=local<=max(.0025,floor*.5) or float(np.sum(segm))<=1e-6;silence.append(silent)
        if silent:scores.append(np.full(len(cands),-9.0));continue
        segm/=max(float(np.linalg.norm(segm)),1e-9);row=[]
        for root,name,label,tv,complexity in cands:
            s=float(np.dot(segm,tv))-complexity+(0.035 if root in scale else 0.0);row.append(s)
        scores.append(np.array(row))
    T=len(scores);S=len(cands);dp=np.full((T,S),-1e9);prev=np.full((T,S),-1,int);dp[0]=scores[0]
    change={'beginner':.115,'intermediate':.095,'expert':.060}[level]
    for t in range(1,T):
        if silence[t]:dp[t]=dp[t-1];prev[t]=np.arange(S);continue
        for s,c in enumerate(cands):
            vals=[]
            for p,prior in enumerate(cands):
                pen=0 if p==s else change*(.60 if prior[0]==c[0] else 1.0);vals.append(dp[t-1,p]+scores[t][s]-pen)
            prev[t,s]=int(np.argmax(vals));dp[t,s]=vals[prev[t,s]]
    states=[0]*T;states[-1]=int(np.argmax(dp[-1]))
    for t in range(T-1,0,-1):states[t-1]=int(prev[t,states[t]])
    labels=[];confs=[];last='.'
    for i,state in enumerate(states):
        if silence[i]:labels.append(last);confs.append(0.0);continue
        root,name,label,_,_=cands[state];sorted_scores=np.sort(scores[i]);margin=float(sorted_scores[-1]-sorted_scores[-2]) if len(sorted_scores)>1 else 0.0
        if level=='intermediate' and name not in TRIADS and margin<.085:
            label=NOTES[root]+('m' if name in ('min7',) else '')
        labels.append(label);last=label;confs.append(max(0,min(1,.55+margin*2.5)))
    beats=[{'start_ms':int(round(float(t)*1000)),'measure_index':i//per_measure,'beat_index':i%per_measure,'subdivision_index':None} for i,t in enumerate(times)]
    chords=[];last=None
    for i,(label,conf) in enumerate(zip(labels,confs)):
        if label==last:continue
        chords.append({'start_ms':int(round(float(times[i])*1000)),'measure_index':i//per_measure,'beat_index':i%per_measure,'subdivision_index':None,'chord':label,'confidence':round(float(conf),4)});last=label
    return {'ok':True,'version':'r33.1-riff','level':level,'tempo_bpm':round(tempo,3),'time_signature':sig,'key':key_name,'harmony_source':harmony_source,'rhythm_source':rhythm_source,'beats':beats,'chords':chords}

def main():
    p=argparse.ArgumentParser();p.add_argument('--audio',required=True);p.add_argument('--stem',action='append',default=[]);p.add_argument('--drums');p.add_argument('--level',choices=('beginner','intermediate','expert'),default='intermediate');p.add_argument('--time-signature',default='auto');a=p.parse_args()
    try:print(json.dumps(analyse(Path(a.audio),a.stem,a.drums,a.level,a.time_signature),ensure_ascii=False));return 0
    except Exception as exc:print(json.dumps({'ok':False,'error':f'{type(exc).__name__}: {exc}'},ensure_ascii=False));return 1
if __name__=='__main__':raise SystemExit(main())
