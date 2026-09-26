#!/usr/bin/env python3
from __future__ import annotations

import argparse, json, time
from pathlib import Path
import numpy as np
import librosa

NOTES=["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
MAJOR=np.array([6.35,2.23,3.48,2.33,4.38,4.09,2.52,5.19,2.39,3.66,2.29,2.88],float)
MINOR=np.array([6.33,2.68,3.52,5.38,2.60,3.53,2.54,4.75,3.98,2.69,3.34,3.17],float)
TRIADS={"major":([0,4,7],""),"minor":([0,3,7],"m")}
MID={"7":([0,4,7,10],"7"),"min7":([0,3,7,10],"m7"),"sus2":([0,2,7],"sus2"),"sus4":([0,5,7],"sus4"),"dim":([0,3,6],"dim")}
EXPERT={"maj7":([0,4,7,11],"maj7"),"aug":([0,4,8],"aug"),"6":([0,4,7,9],"6"),"min6":([0,3,7,9],"m6"),"add9":([0,2,4,7],"add9")}

def write_json(path,payload):
    if not path:return
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(p.suffix+".tmp");tmp.write_text(json.dumps(payload,ensure_ascii=False),encoding="utf-8");tmp.replace(p)
def prog(path,pct,stage,msg): write_json(path,{"percent":int(max(0,min(100,pct))),"stage":stage,"message":msg,"updated_at":time.time()})
def cosine(a,b):
    den=float(np.linalg.norm(a)*np.linalg.norm(b));return 0.0 if den<=1e-12 else float(np.dot(a,b)/den)
def detect_key(mean):
    if float(np.sum(mean))<=1e-9:return None,None
    x=mean/max(float(np.linalg.norm(mean)),1e-9);best=(None,None,-1e9)
    for r in range(12):
        for prof,mode,suffix in ((np.roll(MAJOR,r),"major",""),(np.roll(MINOR,r),"minor","m")):
            sc=cosine(x,prof)
            if sc>best[2]:best=(r,mode,sc)
    r,mode,_=best;return NOTES[r]+("" if mode=="major" else "m"),(r,mode)
def diatonic(info):
    if info is None:return set()
    r,mode=info;ints=[0,2,4,5,7,9,11] if mode=="major" else [0,2,3,5,7,8,10]
    return {(r+i)%12 for i in ints}
def tmpl(root,intervals):
    v=np.full(12,.04,float);v[root]=1.35
    for i in intervals:v[(root+i)%12]=1.0
    return v/max(float(np.linalg.norm(v)),1e-9)
def candidates(level):
    q=dict(TRIADS)
    if level in ("intermediate","expert"):q.update(MID)
    if level=="expert":q.update(EXPERT)
    out=[]
    for r in range(12):
        for name,(ints,suffix) in q.items():
            complexity=0.0 if name in TRIADS else (0.105 if level=="intermediate" else 0.025)
            out.append({"root":r,"quality":name,"label":NOTES[r]+suffix,"template":tmpl(r,ints),"complexity":complexity})
    return out
def signature_score(onset,frames):
    if len(frames)<12:return "4/4"
    s=onset[np.clip(frames,0,len(onset)-1)];s=(s-np.mean(s))/(np.std(s)+1e-9)
    def score(period):
        m=[float(np.mean(s[np.arange(len(s))%period==p])) for p in range(period)]
        return max(m)-float(np.mean(m))
    vals={"3/4":score(3),"4/4":score(4),"6/8":score(6)}
    ordered=sorted(vals.items(),key=lambda x:x[1],reverse=True)
    return "4/4" if ordered[0][1]-ordered[1][1]<.10 else ordered[0][0]
def num(sig):
    try:return max(1,int(sig.split("/",1)[0]))
    except:return 4
def downbeat_phase(onset,frames,n):
    if n<=1 or len(frames)<n*3:return 0,0.0
    s=onset[np.clip(frames,0,len(onset)-1)];s=(s-np.mean(s))/(np.std(s)+1e-9)
    vals=[]
    for p in range(n):
        a=s[np.arange(len(s))%n==p];b=s[np.arange(len(s))%n!=p]
        vals.append(float(np.mean(a))-float(np.mean(b)))
    order=sorted(enumerate(vals),key=lambda x:x[1],reverse=True)
    confidence=order[0][1]-order[1][1]
    return (0,confidence) if confidence<.12 else (int(order[0][0]),confidence)
def pos(i,phase,n):
    if phase<=0:return i//n,i%n
    if i<phase:return 0,n-phase+i
    j=i-phase;return 1+j//n,j%n
def load_mix(paths,sr=11025):
    sigs=[];length=0
    for path in paths:
        if path and Path(path).is_file():
            y,_=librosa.load(str(path),sr=sr,mono=True)
            if y.size:sigs.append(y);length=max(length,len(y))
    if not sigs:raise RuntimeError("no usable harmony source")
    mix=np.zeros(length,np.float32)
    for y in sigs:mix[:len(y)]+=y.astype(np.float32)
    mix/=max(1,len(sigs));return librosa.util.normalize(mix),sr

def analyse(source,stems,drums,level,requested,progress_file):
    prog(progress_file,5,"load","Chargement des sources audio")
    harmonic_paths=[p for p in stems if p and Path(p).is_file()]
    if harmonic_paths:y,sr=load_mix(harmonic_paths);hsource="stems"
    else:y,sr=load_mix([source]);hsource="original"
    if drums and Path(drums).is_file(): rhythm,_=librosa.load(str(drums),sr=sr,mono=True);rhythm=librosa.util.normalize(rhythm);rsource="drums"
    else:rhythm=y;rsource=hsource

    prog(progress_file,18,"beats","Détection des beats")
    hop=512;onset=librosa.onset.onset_strength(y=rhythm,sr=sr,hop_length=hop)
    tempo,frames=librosa.beat.beat_track(onset_envelope=onset,sr=sr,hop_length=hop,trim=False)
    frames=np.asarray(frames,dtype=int);times=librosa.frames_to_time(frames,sr=sr,hop_length=hop)
    tempo=float(np.asarray(tempo).reshape(-1)[0]) if np.asarray(tempo).size else 0.0
    duration=float(librosa.get_duration(y=y,sr=sr))
    if len(times)<4:
        step=60.0/tempo if tempo>20 else .5;times=np.arange(0,duration,step);frames=librosa.time_to_frames(times,sr=sr,hop_length=hop)
    sig=signature_score(onset,frames) if requested=="auto" else requested;n=num(sig)
    phase,phase_conf=downbeat_phase(onset,frames,n)

    prog(progress_file,32,"chroma","Extraction de l’harmonie")
    chroma=np.maximum(librosa.feature.chroma_cqt(y=y,sr=sr,hop_length=hop),0)
    key,keyinfo=detect_key(np.mean(chroma,axis=1));inkey=diatonic(keyinfo)
    rms=librosa.feature.rms(y=y,hop_length=hop)[0];floor=float(np.percentile(rms,12)) if rms.size else 0.0
    cands=candidates(level);scores=[];silent=[]

    prog(progress_file,50,"scoring",f"Reconnaissance des accords — {level}")
    for i,start in enumerate(times):
        end=times[i+1] if i+1<len(times) else min(duration,start+max(.25,60/max(tempo,60)))
        f0=max(0,int(librosa.time_to_frames(start,sr=sr,hop_length=hop)));f1=min(chroma.shape[1],max(f0+1,int(librosa.time_to_frames(end,sr=sr,hop_length=hop))))
        if f0>=chroma.shape[1]:scores.append(np.full(len(cands),-9.0));silent.append(True);continue
        segm=np.mean(chroma[:,f0:f1],axis=1)
        local=float(np.mean(rms[min(f0,len(rms)-1):min(max(f1,f0+1),len(rms))])) if rms.size else 1.0
        is_silent=local<=max(.0025,floor*.50) or float(np.sum(segm))<=1e-6;silent.append(is_silent)
        if is_silent:scores.append(np.full(len(cands),-9.0));continue
        seg=segm/max(float(np.linalg.norm(segm)),1e-9);row=[]
        for c in cands:
            sc=float(np.dot(seg,c["template"]))-c["complexity"]+(.035 if c["root"] in inkey else 0.0);row.append(sc)
        scores.append(np.array(row,float))

    prog(progress_file,68,"smoothing","Lissage temporel")
    nb=len(scores);ns=len(cands)
    if nb==0:raise RuntimeError("no beats detected")
    dp=np.full((nb,ns),-1e9);prev=np.full((nb,ns),-1,int);dp[0]=scores[0]
    trans={"beginner":.155,"intermediate":.105,"expert":.055}[level]
    for t in range(1,nb):
        if silent[t]:dp[t]=dp[t-1];prev[t]=np.arange(ns);continue
        for s,c in enumerate(cands):
            best=-1e9;bp=0
            for p,prior in enumerate(cands):
                penalty=0.0 if p==s else trans
                if prior["root"]==c["root"] and prior["quality"]!=c["quality"]:penalty*=.60
                val=dp[t-1,p]+scores[t][s]-penalty
                if val>best:best=val;bp=p
            dp[t,s]=best;prev[t,s]=bp
    states=[0]*nb;states[-1]=int(np.argmax(dp[-1]))
    for t in range(nb-1,0,-1):states[t-1]=int(prev[t,states[t]])
    labels=[];conf=[];last="."
    for i,state in enumerate(states):
        if silent[i]:labels.append(last);conf.append(0.0);continue
        best=cands[state];sorted_scores=np.sort(scores[i]);margin=float(sorted_scores[-1]-sorted_scores[-2]) if len(sorted_scores)>1 else 0.0
        label=best["label"]
        if level=="intermediate" and best["quality"] not in TRIADS and margin<.105:
            label=NOTES[best["root"]]+("m" if best["quality"]=="min7" else "")
        labels.append(label);last=label;conf.append(max(0,min(1,.55+margin*2.5)))

    prog(progress_file,84,"timeline","Construction de la timeline")
    beats=[]
    for i,t in enumerate(times):
        mi,bi=pos(i,phase,n);beats.append({"start_ms":int(round(float(t)*1000)),"measure_index":mi,"beat_index":bi,"subdivision_index":None})
    chords=[];previous=None
    for i,(label,cf) in enumerate(zip(labels,conf)):
        if label==previous:continue
        mi,bi=pos(i,phase,n);chords.append({"start_ms":int(round(float(times[i])*1000)),"measure_index":mi,"beat_index":bi,"subdivision_index":None,"chord":label,"confidence":round(float(cf),4)});previous=label
    return {"ok":True,"version":"r33.2-riff","level":level,"tempo_bpm":round(tempo,3),"time_signature":sig,"key":key,"harmony_source":hsource,"rhythm_source":rsource,"downbeat_phase":phase,"downbeat_confidence":round(float(phase_conf),4),"beats":beats,"chords":chords}

def main():
    p=argparse.ArgumentParser();p.add_argument("--audio",required=True);p.add_argument("--stem",action="append",default=[]);p.add_argument("--drums");p.add_argument("--level",choices=("beginner","intermediate","expert"),default="intermediate");p.add_argument("--time-signature",default="auto");p.add_argument("--progress-file");p.add_argument("--output")
    a=p.parse_args()
    try:
        result=analyse(Path(a.audio),a.stem,a.drums,a.level,a.time_signature,a.progress_file);prog(a.progress_file,96,"write","Écriture du résultat")
        if a.output:write_json(a.output,result);print(json.dumps({"ok":True,"output":a.output,"chords":len(result["chords"]),"beats":len(result["beats"])},ensure_ascii=False))
        else:print(json.dumps(result,ensure_ascii=False))
        prog(a.progress_file,100,"complete","Analyse harmonique terminée");return 0
    except Exception as exc:
        prog(a.progress_file,100,"error",str(exc));print(json.dumps({"ok":False,"error":f"{type(exc).__name__}: {exc}"},ensure_ascii=False));return 1
if __name__=="__main__":raise SystemExit(main())
