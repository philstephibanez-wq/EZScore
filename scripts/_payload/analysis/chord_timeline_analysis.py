#!/usr/bin/env python3
from __future__ import annotations

import argparse, json, time
from pathlib import Path
import numpy as np
import librosa

NOTES=["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
MAJOR=np.array([6.35,2.23,3.48,2.33,4.38,4.09,2.52,5.19,2.39,3.66,2.29,2.88],float)
MINOR=np.array([6.33,2.68,3.52,5.38,2.60,3.53,2.54,4.75,3.98,2.69,3.34,3.17],float)

TRIADS={
    "major":([0,4,7],""),
    "minor":([0,3,7],"m"),
}
MID={
    "7":([0,4,7,10],"7"),
    "min7":([0,3,7,10],"m7"),
    "sus2":([0,2,7],"sus2"),
    "sus4":([0,5,7],"sus4"),
    "dim":([0,3,6],"dim"),
}
EXPERT={
    "maj7":([0,4,7,11],"maj7"),
    "aug":([0,4,8],"aug"),
    "6":([0,4,7,9],"6"),
    "min6":([0,3,7,9],"m6"),
    "add9":([0,2,4,7],"add9"),
}

PROFILES=("beginner","intermediate","expert")

def write_json(path,payload):
    if not path:return
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(p.suffix+".tmp")
    tmp.write_text(json.dumps(payload,ensure_ascii=False),encoding="utf-8")
    tmp.replace(p)

def prog(path,pct,stage,msg):
    write_json(path,{"percent":int(max(0,min(100,pct))),"stage":stage,"message":msg,"updated_at":time.time()})

def cosine(a,b):
    d=float(np.linalg.norm(a)*np.linalg.norm(b))
    return 0.0 if d<=1e-12 else float(np.dot(a,b)/d)

def detect_key(chroma_mean):
    if float(np.sum(chroma_mean))<=1e-9:return None,None
    x=chroma_mean/max(float(np.linalg.norm(chroma_mean)),1e-9)
    best=(None,None,-1e9)
    for root in range(12):
        for profile,mode,suffix in ((np.roll(MAJOR,root),"major",""),(np.roll(MINOR,root),"minor","m")):
            s=cosine(x,profile)
            if s>best[2]:best=(root,mode,s)
    root,mode,_=best
    return NOTES[root]+("" if mode=="major" else "m"),(root,mode)

def diatonic_roots(info):
    if info is None:return set()
    root,mode=info
    ints=[0,2,4,5,7,9,11] if mode=="major" else [0,2,3,5,7,8,10]
    return {(root+i)%12 for i in ints}

def template(root,intervals):
    v=np.full(12,.04,float);v[root]=1.35
    for i in intervals:v[(root+i)%12]=1.0
    return v/max(float(np.linalg.norm(v)),1e-9)

def candidates(level):
    q=dict(TRIADS)
    if level in ("intermediate","expert"):q.update(MID)
    if level=="expert":q.update(EXPERT)
    out=[]
    for root in range(12):
        for name,(ints,suffix) in q.items():
            if name in TRIADS:pen=0.0
            elif level=="intermediate":pen=.105
            else:pen=.025
            out.append({"root":root,"quality":name,"label":NOTES[root]+suffix,"template":template(root,ints),"complexity":pen})
    return out

def numerator(sig):
    try:return max(1,int(sig.split("/",1)[0]))
    except:return 4

def detect_signature(onset,beat_frames):
    if len(beat_frames)<12:return "4/4"
    s=onset[np.clip(beat_frames,0,len(onset)-1)]
    s=(s-np.mean(s))/(np.std(s)+1e-9)
    def score(period):
        means=[]
        for phase in range(period):
            vals=s[np.arange(len(s))%period==phase]
            if vals.size:means.append(float(np.mean(vals)))
        return max(means)-float(np.mean(means)) if means else -1e9
    c={"3/4":score(3),"4/4":score(4),"6/8":score(6)}
    ordered=sorted(c.items(),key=lambda x:x[1],reverse=True)
    return "4/4" if len(ordered)>1 and ordered[0][1]-ordered[1][1]<.10 else ordered[0][0]

def detect_downbeat_phase(onset,beat_frames,bpm):
    if bpm<=1 or len(beat_frames)<bpm*3:return 0,0.0
    s=onset[np.clip(beat_frames,0,len(onset)-1)]
    s=(s-np.mean(s))/(np.std(s)+1e-9)
    scores=[]
    for phase in range(bpm):
        a=s[np.arange(len(s))%bpm==phase]
        o=s[np.arange(len(s))%bpm!=phase]
        scores.append(float(np.mean(a))-float(np.mean(o)) if a.size and o.size else -1e9)
    ordered=sorted(enumerate(scores),key=lambda x:x[1],reverse=True)
    phase,top=ordered[0];second=ordered[1][1] if len(ordered)>1 else -1e9
    conf=top-second
    return (0,conf) if conf<.12 else (int(phase),conf)

def position(i,phase,bpm):
    if phase<=0:return i//bpm,i%bpm
    if i<phase:return 0,bpm-phase+i
    shifted=i-phase
    return 1+shifted//bpm,shifted%bpm

def load_mix(paths,sr=11025):
    signals=[];target=0
    for path in paths:
        if not path or not Path(path).is_file():continue
        y,_=librosa.load(str(path),sr=sr,mono=True)
        if y.size:signals.append(y);target=max(target,len(y))
    if not signals:raise RuntimeError("no usable harmony source")
    mix=np.zeros(target,np.float32)
    for y in signals:mix[:len(y)]+=y.astype(np.float32)
    mix/=max(1,len(signals))
    return librosa.util.normalize(mix),sr

def decode_profile(level,beat_vectors,silent,in_key,beat_times,bpm,phase):
    cs=candidates(level)
    n=len(beat_vectors)
    if n==0:raise RuntimeError("no beats detected")

    scores=[]
    for i,vec in enumerate(beat_vectors):
        if silent[i]:
            scores.append(np.full(len(cs),-9.0))
            continue
        row=[]
        for c in cs:
            s=float(np.dot(vec,c["template"]))-c["complexity"]
            if c["root"] in in_key:s+=.035
            row.append(s)
        scores.append(np.array(row,float))

    transition={"beginner":.155,"intermediate":.105,"expert":.055}[level]
    dp=np.full((n,len(cs)),-1e9,float)
    prev=np.full((n,len(cs)),-1,int)
    dp[0]=scores[0]
    for t in range(1,n):
        if silent[t]:
            dp[t]=dp[t-1];prev[t]=np.arange(len(cs));continue
        for s,c in enumerate(cs):
            best=-1e9;bestp=0
            for p,pc in enumerate(cs):
                penalty=0.0 if p==s else transition
                if pc["root"]==c["root"] and pc["quality"]!=c["quality"]:penalty*=.60
                value=dp[t-1,p]+scores[t][s]-penalty
                if value>best:best=value;bestp=p
            dp[t,s]=best;prev[t,s]=bestp

    states=[0]*n;states[-1]=int(np.argmax(dp[-1]))
    for t in range(n-1,0,-1):states[t-1]=int(prev[t,states[t]])

    labels=[];confs=[];last="."
    for i,state in enumerate(states):
        if silent[i]:
            labels.append(last);confs.append(0.0);continue
        c=cs[state];ordered=np.sort(scores[i]);margin=float(ordered[-1]-ordered[-2]) if len(ordered)>1 else 0.0
        label=c["label"]

        # Beginner is strictly simple major/minor.
        if level=="beginner":
            label=NOTES[c["root"]]+("m" if c["quality"]=="minor" else "")

        # Intermediate keeps extensions only when the evidence is clear.
        if level=="intermediate" and c["quality"] not in TRIADS and margin<.105:
            label=NOTES[c["root"]]+("m" if c["quality"]=="min7" else "")

        # Standard guitar spelling: plain major triad is always "C", never "Cmaj".
        if label.endswith("maj") and not label.endswith("maj7"):
            label=label[:-3]

        labels.append(label);last=label
        confs.append(max(0.0,min(1.0,.55+margin*2.5)))

    chords=[];previous=None
    for i,(label,conf) in enumerate(zip(labels,confs)):
        if label==previous:continue
        mi,bi=position(i,phase,bpm)
        chords.append({
            "start_ms":int(round(float(beat_times[i])*1000)),
            "measure_index":mi,
            "beat_index":bi,
            "subdivision_index":None,
            "chord":label,
            "confidence":round(float(conf),4),
        })
        previous=label
    return chords

def analyse(source,stems,drums,requested_signature,progress_file=None):
    prog(progress_file,5,"load","Chargement des sources audio")
    harmonic=[p for p in stems if p and Path(p).is_file()]
    if harmonic:
        yh,sr=load_mix(harmonic);harmonic_source="stems"
    else:
        yh,sr=load_mix([source]);harmonic_source="original"

    if drums and Path(drums).is_file():
        yr,_=librosa.load(str(drums),sr=sr,mono=True);yr=librosa.util.normalize(yr);rhythm_source="drums"
    else:
        yr=yh;rhythm_source=harmonic_source

    prog(progress_file,18,"beats","Détection des beats")
    hop=512
    onset=librosa.onset.onset_strength(y=yr,sr=sr,hop_length=hop)
    tempo_value,beat_frames=librosa.beat.beat_track(onset_envelope=onset,sr=sr,hop_length=hop,trim=False)
    beat_frames=np.asarray(beat_frames,dtype=int)
    beat_times=librosa.frames_to_time(beat_frames,sr=sr,hop_length=hop)
    ta=np.asarray(tempo_value).reshape(-1);tempo=float(ta[0]) if ta.size else 0.0
    duration=float(librosa.get_duration(y=yh,sr=sr))
    if len(beat_times)<4:
        step=60.0/tempo if tempo>20 else .5
        beat_times=np.arange(0.0,duration,step,float)
        beat_frames=librosa.time_to_frames(beat_times,sr=sr,hop_length=hop)

    signature=detect_signature(onset,beat_frames) if requested_signature=="auto" else requested_signature
    bpm=numerator(signature)
    phase,phase_conf=detect_downbeat_phase(onset,beat_frames,bpm)

    prog(progress_file,32,"chroma","Extraction de l’harmonie")
    chroma=librosa.feature.chroma_cqt(y=yh,sr=sr,hop_length=hop)
    chroma=np.maximum(chroma,0.0)
    key,key_info=detect_key(np.mean(chroma,axis=1));in_key=diatonic_roots(key_info)
    rms=librosa.feature.rms(y=yh,hop_length=hop)[0]
    floor=float(np.percentile(rms,12)) if rms.size else 0.0

    beat_vectors=[];silent=[]
    for i,start in enumerate(beat_times):
        end=beat_times[i+1] if i+1<len(beat_times) else min(duration,start+max(.25,60.0/max(tempo,60.0)))
        f0=max(0,int(librosa.time_to_frames(start,sr=sr,hop_length=hop)))
        f1=min(chroma.shape[1],max(f0+1,int(librosa.time_to_frames(end,sr=sr,hop_length=hop))))
        if f0>=chroma.shape[1]:
            beat_vectors.append(np.zeros(12));silent.append(True);continue
        segment=np.mean(chroma[:,f0:f1],axis=1)
        rr=rms[min(f0,len(rms)-1):min(max(f1,f0+1),len(rms))] if rms.size else np.array([1.0])
        local=float(np.mean(rr))
        is_silent=local<=max(.0025,floor*.50) or float(np.sum(segment))<=1e-6
        silent.append(is_silent)
        beat_vectors.append(segment/max(float(np.linalg.norm(segment)),1e-9) if not is_silent else np.zeros(12))

    prog(progress_file,50,"beginner","Construction du profil Débutant")
    beginner=decode_profile("beginner",beat_vectors,silent,in_key,beat_times,bpm,phase)
    prog(progress_file,63,"intermediate","Construction du profil Intermédiaire")
    intermediate=decode_profile("intermediate",beat_vectors,silent,in_key,beat_times,bpm,phase)
    prog(progress_file,76,"expert","Construction du profil Expert")
    expert=decode_profile("expert",beat_vectors,silent,in_key,beat_times,bpm,phase)

    prog(progress_file,88,"timeline","Construction de la timeline commune")
    beats=[]
    for i,t in enumerate(beat_times):
        mi,bi=position(i,phase,bpm)
        beats.append({"start_ms":int(round(float(t)*1000)),"measure_index":mi,"beat_index":bi,"subdivision_index":None})

    return {
        "ok":True,
        "version":"r34-three-profiles",
        "tempo_bpm":round(tempo,3),
        "time_signature":signature,
        "key":key,
        "harmony_source":harmonic_source,
        "rhythm_source":rhythm_source,
        "downbeat_phase":phase,
        "downbeat_confidence":round(float(phase_conf),4),
        "beats":beats,
        "profiles":{
            "beginner":{"chords":beginner},
            "intermediate":{"chords":intermediate},
            "expert":{"chords":expert},
        },
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--audio",required=True)
    p.add_argument("--stem",action="append",default=[])
    p.add_argument("--drums")
    # Kept for backward compatibility with R33 worker command; R34 always computes all profiles.
    p.add_argument("--level",choices=PROFILES,default="intermediate")
    p.add_argument("--time-signature",default="auto")
    p.add_argument("--progress-file")
    p.add_argument("--output")
    a=p.parse_args()
    try:
        result=analyse(Path(a.audio),a.stem,a.drums,a.time_signature,a.progress_file)
        prog(a.progress_file,96,"write","Écriture des trois profils")
        if a.output:
            write_json(a.output,result)
            counts={k:len(v["chords"]) for k,v in result["profiles"].items()}
            print(json.dumps({"ok":True,"output":a.output,"profiles":counts,"beats":len(result["beats"])},ensure_ascii=False))
        else:
            print(json.dumps(result,ensure_ascii=False))
        prog(a.progress_file,100,"complete","Trois profils harmoniques terminés")
        return 0
    except Exception as exc:
        prog(a.progress_file,100,"error",str(exc))
        print(json.dumps({"ok":False,"error":f"{type(exc).__name__}: {exc}"},ensure_ascii=False))
        return 1

if __name__=="__main__":
    raise SystemExit(main())
