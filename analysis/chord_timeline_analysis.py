#!/usr/bin/env python3
from __future__ import annotations

import argparse, importlib.util, json, time
from pathlib import Path
import numpy as np
import librosa
from meter_detection_r35_2 import detect_meter

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

NOTE_TO_PC={
    "C":0,"C#":1,"Db":1,"D":2,"D#":3,"Eb":3,"E":4,"F":5,
    "F#":6,"Gb":6,"G":7,"G#":8,"Ab":8,"A":9,"A#":10,"Bb":10,"B":11,
}
MAJOR_KEY_TRIADS={0:"major",2:"minor",4:"minor",5:"major",7:"major",9:"minor",11:"dim"}
MINOR_KEY_TRIADS={0:"minor",2:"dim",3:"major",5:"minor",7:"major",8:"major",10:"major"}

def parse_harmonic_chord(label):
    text=str(label or ".").strip()
    if not text or text in {".","N"}:return None
    text=text.split("/",1)[0].strip()
    root_name=None
    for candidate in sorted(NOTE_TO_PC,key=len,reverse=True):
        if text.startswith(candidate):
            root_name=candidate
            break
    if root_name is None:return None
    suffix=text[len(root_name):]
    if suffix.startswith("maj"):
        quality="major"
    elif suffix.startswith("m") and not suffix.startswith("maj"):
        quality="minor"
    elif suffix.startswith("dim") or "m7b5" in suffix:
        quality="dim"
    elif suffix.startswith("aug") or suffix.startswith("+"):
        quality="aug"
    elif suffix.startswith("sus"):
        quality="sus"
    else:
        quality="major"
    dominant=(suffix.startswith("7") or suffix.startswith("9") or suffix.startswith("11") or suffix.startswith("13"))
    return NOTE_TO_PC[root_name],quality,dominant

def chroma_key_score(chroma_mean,root,mode):
    if chroma_mean is None or float(np.sum(chroma_mean))<=1e-9:return 0.0
    x=np.asarray(chroma_mean,dtype=float)
    x=x/max(float(np.linalg.norm(x)),1e-9)
    profile=np.roll(MAJOR if mode=="major" else MINOR,root)
    return cosine(x,profile)

def key_score_from_segments(segments,root,mode,chroma_mean=None):
    degree_map=MAJOR_KEY_TRIADS if mode=="major" else MINOR_KEY_TRIADS
    total=0.0
    weighted=0.0
    tonic_duration=0.0
    dominant_duration=0.0
    parsed_segments=[]

    for segment in segments or []:
        parsed=parse_harmonic_chord(segment.get("chord"))
        if parsed is None:continue
        start=float(segment.get("start",0.0) or 0.0)
        end=float(segment.get("end",start) or start)
        duration=max(0.0,end-start)
        if duration<=1e-6:continue
        chord_root,quality,is_dominant=parsed
        rel=(chord_root-root)%12
        expected=degree_map.get(rel)

        value=-0.28
        if expected is not None:
            value=0.30
            if quality==expected:value=1.00
            elif quality=="sus":value=0.58
            if mode=="minor" and rel==7 and quality=="major":
                value=1.22
            if rel==7 and is_dominant:
                value+=0.18

        if rel==0:
            tonic_match=((mode=="major" and quality=="major") or (mode=="minor" and quality=="minor"))
            if tonic_match:
                value+=0.60
                tonic_duration+=duration
            else:
                value-=0.20

        if rel==7:
            dominant_duration+=duration

        total+=duration
        weighted+=duration*value
        parsed_segments.append((chord_root,quality,is_dominant,duration))

    if total<=1e-6:return None

    score=weighted/total
    score+=0.38*(tonic_duration/total)
    if mode=="minor":
        score+=0.20*(dominant_duration/total)

    if parsed_segments:
        last_root,last_quality,_,_=parsed_segments[-1]
        if last_root==root:
            if (mode=="major" and last_quality=="major") or (mode=="minor" and last_quality=="minor"):
                score+=0.16

    score+=0.18*chroma_key_score(chroma_mean,root,mode)
    return float(score)

def detect_key_from_segments(segments,chroma_mean=None):
    ranked=[]
    for root in range(12):
        for mode in ("major","minor"):
            score=key_score_from_segments(segments,root,mode,chroma_mean)
            if score is not None:
                ranked.append((float(score),root,mode))

    if not ranked:
        key,info=detect_key(chroma_mean)
        return key,info,0.0,"chroma_no_parseable_hq_segments"

    ranked.sort(reverse=True)
    best_score,root,mode=ranked[0]
    second_score=ranked[1][0] if len(ranked)>1 else best_score
    confidence=max(0.0,best_score-second_score)
    key=NOTES[root]+("" if mode=="major" else "m")
    return key,(root,mode),float(confidence),"lv-chordia-duration+chroma-tiebreak"

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
    # Canonical musical grid: keep audio timestamps unchanged, but number beats
    # from the detected musical downbeat. Beats before the first downbeat belong
    # to pickup/pre-roll measure -1; the first real downbeat is measure 0 beat 0.
    bpm=max(1,int(bpm))
    phase=int(phase)%bpm
    relative=int(i)-phase
    return relative//bpm,relative%bpm

def suppress_crowd_noise(y,sr,hop=512):
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
    """Preserve detected beats but guarantee that the prompter exists from MP3 t=0."""
    bt=np.asarray(beat_times,dtype=float)
    if bt.size==0:
        step=60.0/tempo if tempo>20 else .5
        return np.arange(0.0,max(duration,step)+step*.25,step,float),0
    diffs=np.diff(bt);positive=diffs[diffs>1e-4]
    step=float(np.median(positive)) if positive.size else (60.0/tempo if tempo>20 else .5)
    step=max(.12,min(3.0,step))
    if bt[0] <= max(.045,step*.10):
        bt=bt.copy();bt[0]=0.0
        return bt,0
    prepend=[];t=float(bt[0])-step
    while t>max(.045,step*.10):
        prepend.append(t);t-=step
    prepend.append(0.0)
    prepend=np.asarray(sorted(set(round(max(0.0,x),6) for x in prepend)),dtype=float)
    return np.concatenate([prepend,bt]),len(prepend)

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


CHORD_ENGINE="lv-chordia"
CHORD_DICTIONARY="submission"

def quality_chord_engine_available():
    try:
        return importlib.util.find_spec("lv_chordia") is not None
    except Exception:
        return False

def ezscore_chord_label(raw):
    label=str(raw or "N").strip()
    if not label or label=="N":return "."
    bass=""
    if "/" in label:
        label,bass_part=label.split("/",1)
        bass_part=bass_part.strip()
        if bass_part:bass="/"+bass_part
    if ":" not in label:return label+bass
    root,quality=label.split(":",1)
    root=root.strip();quality=quality.strip()
    quality_map={
        "maj":"","min":"m","7":"7","maj7":"maj7","min7":"m7",
        "dim":"dim","dim7":"dim7","hdim7":"m7b5","aug":"aug",
        "sus2":"sus2","sus4":"sus4","min6":"m6","maj6":"6",
        "min9":"m9","maj9":"maj9","9":"9","11":"11","13":"13",
    }
    return f"{root}{quality_map.get(quality,quality)}{bass}"

def analyze_chords_absolute(audio_path):
    if not quality_chord_engine_available():
        raise RuntimeError(
            "Moteur d'accords haute qualité absent : installez `lv-chordia==1.1.0`. "
            "EZScore refuse tout fallback chroma silencieux."
        )
    from lv_chordia.chord_recognition import chord_recognition

    # Exact historical EZScore contract: no device argument here.
    # The Worker environment itself remains CUDA-only for EZScore processing.
    raw_segments=chord_recognition(
        audio_path=str(audio_path),
        chord_dict_name=CHORD_DICTIONARY,
    )

    segments=[]
    for item in raw_segments or []:
        start=float(item.get("start_time",0.0) or 0.0)
        end=float(item.get("end_time",start) or start)
        raw=str(item.get("chord","N") or "N").strip()
        if end<=start:continue
        segments.append({
            "start":start,
            "end":end,
            "chord":ezscore_chord_label(raw),
            "raw_chord":raw,
        })
    if not segments:
        raise RuntimeError("lv-chordia n'a retourné aucun segment harmonique exploitable.")
    return segments

def chord_for_interval(segments,start,end):
    t0=float(start);t1=max(t0+1e-6,float(end))
    best=None;best_overlap=0.0
    for segment in segments or []:
        s0=float(segment.get("start",0.0) or 0.0)
        s1=float(segment.get("end",s0) or s0)
        overlap=max(0.0,min(t1,s1)-max(t0,s0))
        if overlap>best_overlap:
            best_overlap=overlap;best=segment
    if best is None:
        midpoint=(t0+t1)*0.5
        best=min(
            segments or [],
            key=lambda segment:abs(
                ((float(segment.get("start",0.0))+float(segment.get("end",0.0)))*0.5)-midpoint
            ),
            default=None,
        )
        if best is None:return ".",0.0
    ratio=best_overlap/max(1e-6,t1-t0)
    return str(best.get("chord",".") or "."),float(max(0.0,min(1.0,ratio)))

def simplify_chord(label,level):
    text=str(label or ".").strip()
    if not text or text in {"N","."}:return "."
    bass=""
    if "/" in text:
        text,bass_part=text.split("/",1);bass="/"+bass_part
    root=text
    suffix=""
    for i,ch in enumerate(text):
        if i>0 and (ch=="m" or ch.isdigit() or ch in {"+","s"}):
            root=text[:i];suffix=text[i:];break
    if level=="expert":return text+bass
    is_minor=suffix.startswith("m") and not suffix.startswith("maj")
    if level=="beginner":
        return root+("m" if is_minor else "")
    if suffix in {"","m","7","m7","sus2","sus4","dim"}:
        return text
    if is_minor:return root+"m"
    return root

def metric_projection_diagnostics(segments,beat_times,bpm,phase):
    bt=np.asarray(beat_times,dtype=float)
    if bt.size==0:
        return {"raw_transitions":[]}
    rows=[]
    downbeats=[i for i in range(len(bt)) if position(i,phase,bpm)[1]==0]
    for segment in segments or []:
        t=float(segment.get("start",0.0) or 0.0)
        nearest=int(np.argmin(np.abs(bt-t)))
        nearest_ms=float(bt[nearest]*1000.0)
        mi,bi=position(nearest,phase,bpm)
        nearest_down=min(downbeats,key=lambda i:abs(float(bt[i])-t)) if downbeats else nearest
        dmi,dbi=position(nearest_down,phase,bpm)
        rows.append({
            "raw_start_ms":int(round(t*1000.0)),
            "raw_end_ms":int(round(float(segment.get("end",t) or t)*1000.0)),
            "chord":str(segment.get("chord",".") or "."),
            "raw_chord":str(segment.get("raw_chord","") or ""),
            "nearest_beat_seq":nearest,
            "nearest_beat_start_ms":int(round(nearest_ms)),
            "nearest_beat_delta_ms":int(round(t*1000.0-nearest_ms)),
            "nearest_measure_index":mi,
            "nearest_beat_index":bi,
            "nearest_downbeat_seq":nearest_down,
            "nearest_downbeat_start_ms":int(round(float(bt[nearest_down])*1000.0)),
            "nearest_downbeat_delta_ms":int(round(t*1000.0-float(bt[nearest_down])*1000.0)),
            "nearest_downbeat_measure_index":dmi,
            "nearest_downbeat_beat_index":dbi,
        })
    return {"raw_transitions":rows}

def _metric_z(values):
    x=np.asarray(values,dtype=float)
    if x.size==0:return x
    return (x-np.mean(x))/(np.std(x)+1e-9)

def _compound_signature_model(signature,bpm):
    sig=str(signature or "").strip()
    if sig=="6/8":
        return {"compound":True,"subdivisions":6,"group":3,"pulses":2,"reference":"2/4"}
    if sig=="9/8":
        return {"compound":True,"subdivisions":9,"group":3,"pulses":3,"reference":"3/4"}
    if sig=="12/8":
        return {"compound":True,"subdivisions":12,"group":3,"pulses":4,"reference":"4/4"}
    return {
        "compound":False,
        "subdivisions":max(1,int(bpm)),
        "group":1,
        "pulses":max(1,int(bpm)),
        "reference":sig or f"{bpm}/4",
    }

def _transition_evidence(segments,beat_times,tolerance):
    bt=np.asarray(beat_times,dtype=float)
    out=[]
    previous=None
    for segment in segments or []:
        chord=str(segment.get("chord",".") or ".")
        start=float(segment.get("start",0.0) or 0.0)
        if previous is None:
            previous=chord
            continue
        if chord==previous:
            continue
        nearest=int(np.argmin(np.abs(bt-start)))
        delta=abs(float(bt[nearest])-start)
        closeness=float(np.exp(-0.5*(delta/tolerance)**2))
        out.append((nearest,closeness))
        previous=chord
    return out

def _phase_mean(feature,indices):
    x=np.asarray(feature,dtype=float)
    idx=np.asarray(indices,dtype=int)
    if x.size==0 or idx.size==0:return 0.0
    idx=idx[(idx>=0)&(idx<len(x))]
    return float(np.mean(x[idx])) if idx.size else 0.0

def select_musical_downbeat_phase(onset,beat_times,segments,bpm,sr,hop,bass_y=None,prior_phase=None,signature=None):
    """Strict compound -> n/4 metric model.

    Compound signatures are solved in two independent stages:
      A) find the ternary grouping offset (which eighth-note begins each dotted beat),
      B) run the equivalent n/4 bar-phase choice on those dotted beats only.
    """
    bt=np.asarray(beat_times,dtype=float)
    model=_compound_signature_model(signature,bpm)
    period=int(model["subdivisions"])
    if bt.size<max(period*3,8):
        phase=int(prior_phase or 0)%max(1,period)
        return phase,0.0,[],[]

    beat_frames=np.clip(
        librosa.time_to_frames(bt,sr=sr,hop_length=hop),
        0,max(0,len(onset)-1),
    )
    rhythm=_metric_z(np.asarray(onset,dtype=float)[beat_frames]) if len(onset) else np.zeros(len(bt),float)

    if bass_y is not None and len(bass_y):
        bass_onset=librosa.onset.onset_strength(y=bass_y,sr=sr,hop_length=hop)
        bass_frames=np.clip(
            librosa.time_to_frames(bt,sr=sr,hop_length=hop),
            0,max(0,len(bass_onset)-1),
        )
        bass=_metric_z(np.asarray(bass_onset,dtype=float)[bass_frames]) if len(bass_onset) else np.zeros(len(bt),float)
    else:
        bass=np.zeros(len(bt),float)

    step=float(np.median(np.diff(bt))) if len(bt)>1 else .5
    tolerance=max(.08,min(.45,step*.42))
    transitions=_transition_evidence(segments,bt,tolerance)
    n=len(bt)

    if bool(model["compound"]):
        group=int(model["group"])
        pulses=int(model["pulses"])

        # A — choose which subdivision starts each compound pulse.
        grouping_rows=[]
        for offset in range(group):
            pulse_starts=np.arange(offset,n,group,dtype=int)
            nonstarts=np.asarray(
                [i for i in range(n) if (i-offset)%group!=0],
                dtype=int,
            )
            rhythm_score=_phase_mean(rhythm,pulse_starts)-_phase_mean(rhythm,nonstarts)
            bass_score=_phase_mean(bass,pulse_starts)-_phase_mean(bass,nonstarts)

            chord_values=[]
            for nearest,closeness in transitions:
                aligned=((nearest-offset)%group)==0
                chord_values.append(closeness*(1.0 if aligned else -0.35))
            chord_score=float(np.mean(chord_values)) if chord_values else 0.0

            score=(
                .30*float(np.clip(rhythm_score,-2.0,2.0))
                +.20*float(np.clip(bass_score,-2.0,2.0))
                +.50*chord_score
            )
            grouping_rows.append({
                "group_offset":int(offset),
                "score":round(float(score),6),
                "rhythm":round(float(rhythm_score),6),
                "bass":round(float(bass_score),6),
                "chords":round(float(chord_score),6),
                "transition_count":len(transitions),
                "reference":model["reference"],
            })

        grouping_ranked=sorted(grouping_rows,key=lambda row:row["score"],reverse=True)
        winning_offset=int(grouping_ranked[0]["group_offset"])
        pulse_starts=np.arange(winning_offset,n,group,dtype=int)

        # B — now treat these compound pulses exactly like the equivalent n/4.
        bar_rows=[]
        pulse_ord=np.arange(len(pulse_starts),dtype=int)
        for pulse_phase in range(pulses):
            bar_starts=pulse_starts[(pulse_ord-pulse_phase)%pulses==0]
            other_pulses=pulse_starts[(pulse_ord-pulse_phase)%pulses!=0]

            rhythm_bar=_phase_mean(rhythm,bar_starts)-_phase_mean(rhythm,other_pulses)
            bass_bar=_phase_mean(bass,bar_starts)-_phase_mean(bass,other_pulses)

            chord_values=[]
            for nearest,closeness in transitions:
                if (nearest-winning_offset)%group!=0:
                    continue
                ordinal=(nearest-winning_offset)//group
                rel=(ordinal-pulse_phase)%pulses
                chord_values.append(closeness*(1.0 if rel==0 else 0.15))
            chord_score=float(np.mean(chord_values)) if chord_values else 0.0

            score=(
                .62*chord_score
                +.25*float(np.clip(rhythm_bar,-2.0,2.0))
                +.13*float(np.clip(bass_bar,-2.0,2.0))
            )
            subdivision_phase=(winning_offset+group*pulse_phase)%period
            bar_rows.append({
                "phase":int(subdivision_phase),
                "pulse_phase":int(pulse_phase),
                "score":round(float(score),6),
                "rhythm":round(float(rhythm_bar),6),
                "bass":round(float(bass_bar),6),
                "chords":round(float(chord_score),6),
                "group_offset":winning_offset,
                "reference":model["reference"],
            })

        ranked=sorted(bar_rows,key=lambda row:row["score"],reverse=True)
        winner=int(ranked[0]["phase"])
        top=float(ranked[0]["score"])
        second=float(ranked[1]["score"]) if len(ranked)>1 else top
        confidence=float(np.clip(top-second,0.0,1.0))
        return winner,confidence,grouping_rows,bar_rows

    # Simple n/4 meters: direct bar phase on the beat grid.
    indices=np.arange(n,dtype=int)
    rows=[]
    period=max(1,period)
    for phase in range(period):
        pos=(indices-phase)%period
        down=indices[pos==0]
        rest=indices[pos!=0]
        rhythm_bar=_phase_mean(rhythm,down)-_phase_mean(rhythm,rest)
        bass_bar=_phase_mean(bass,down)-_phase_mean(bass,rest)

        chord_values=[]
        for nearest,closeness in transitions:
            rel=int(pos[nearest])
            chord_values.append(closeness*(1.0 if rel==0 else -0.18))
        chord_score=float(np.mean(chord_values)) if chord_values else 0.0

        score=(
            .46*float(np.clip(rhythm_bar,-2.0,2.0))
            +.18*float(np.clip(bass_bar,-2.0,2.0))
            +.36*chord_score
        )
        rows.append({
            "phase":int(phase),
            "score":round(float(score),6),
            "rhythm":round(float(rhythm_bar),6),
            "bass":round(float(bass_bar),6),
            "chords":round(float(chord_score),6),
            "reference":model["reference"],
        })

    ranked=sorted(rows,key=lambda row:row["score"],reverse=True)
    winner=int(ranked[0]["phase"])
    top=float(ranked[0]["score"])
    second=float(ranked[1]["score"]) if len(ranked)>1 else top
    confidence=float(np.clip(top-second,0.0,1.0))
    return winner,confidence,[],rows

def project_profile(level,segments,beat_times,bpm,phase,tempo):
    chords=[];previous=None
    fallback_step=60.0/tempo if tempo>20 else .5
    for i,start in enumerate(beat_times):
        end=beat_times[i+1] if i+1<len(beat_times) else float(start)+fallback_step
        label,overlap=chord_for_interval(segments,float(start),float(end))
        label=simplify_chord(label,level)
        if label==previous:continue
        mi,bi=position(i,phase,bpm)
        chords.append({
            "start_ms":int(round(float(start)*1000)),
            "measure_index":mi,
            "beat_index":bi,
            "subdivision_index":None,
            "chord":label,
            "confidence":round(float(overlap),4),
        })
        previous=label
    return chords
def decode_profile(*args,**kwargs):
    raise RuntimeError("Legacy chroma chord decoder disabled: lv-chordia HQ is mandatory.")

def analyse(source,stems,drums,requested_signature,progress_file=None,filter_noise=False):
    prog(progress_file,5,"load","Chargement des sources audio")
    harmonic=[p for p in stems if p and Path(p).is_file()]
    if harmonic:
        yh,sr=load_mix(harmonic);harmonic_source="stems"
    else:
        yh,sr=load_mix([source]);harmonic_source="original"

    if filter_noise:
        yh,_=suppress_crowd_noise(yh,sr)
    if drums and Path(drums).is_file():
        yr,_=librosa.load(str(drums),sr=sr,mono=True);yr=librosa.util.normalize(yr);rhythm_source="drums"
        if filter_noise:yr,_=suppress_crowd_noise(yr,sr)
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

    bass_y=None
    bass_path=next((p for p in harmonic if "bass" in Path(p).stem.lower()),None)
    if bass_path:
        bass_y,_=librosa.load(str(bass_path),sr=sr,mono=True)
        bass_y=librosa.util.normalize(bass_y)

    if requested_signature=="auto":
        metric=detect_meter(harmonic_y=yh,bass_y=bass_y,onset=onset,beat_frames=beat_frames,sr=sr,hop=hop)
        signature=metric.signature
        phase=metric.phase
        meter_confidence=metric.confidence
        preliminary_phase_confidence=None
        metric_scores=metric.scores
    else:
        signature=requested_signature
        bpm_manual=numerator(signature)
        phase,preliminary_phase_confidence=detect_downbeat_phase(onset,beat_frames,bpm_manual)
        meter_confidence=1.0
        metric_scores={signature:1.0}
    bpm=numerator(signature)

    beat_times,prepended_count=extend_beats_to_zero(beat_times,duration,tempo)
    if prepended_count:
        phase=(phase+prepended_count)%max(1,bpm)

    prog(progress_file,30,"key_features","Préparation du signal de tonalité")
    chroma=librosa.feature.chroma_cqt(y=yh,sr=sr,hop_length=hop)
    chroma=np.maximum(chroma,0.0)
    chroma_mean=np.mean(chroma,axis=1)

    prog(progress_file,42,"chords_hq","Reconnaissance harmonique continue lv-chordia")
    segments=analyze_chords_absolute(Path(source))

    prog(progress_file,50,"metric_phase","Calage du vrai premier temps")
    preliminary_phase=int(phase)
    phase,phase_confidence,compound_group_candidates,bar_phase_candidates=select_musical_downbeat_phase(
        onset,beat_times,segments,bpm,sr,hop,
        bass_y=bass_y,
        prior_phase=preliminary_phase,
        signature=signature,
    )

    prog(progress_file,52,"key","Estimation de la tonalité depuis les accords HQ")
    key,_,key_confidence,key_method=detect_key_from_segments(segments,chroma_mean)

    prog(progress_file,58,"beginner","Projection du profil Débutant")
    beginner=project_profile("beginner",segments,beat_times,bpm,phase,tempo)
    prog(progress_file,68,"intermediate","Projection du profil Intermédiaire")
    intermediate=project_profile("intermediate",segments,beat_times,bpm,phase,tempo)
    prog(progress_file,78,"expert","Projection du profil Expert")
    expert=project_profile("expert",segments,beat_times,bpm,phase,tempo)

    prog(progress_file,88,"timeline","Construction de la timeline commune")
    diagnostics=metric_projection_diagnostics(segments,beat_times,bpm,phase)
    beats=[]
    for i,t in enumerate(beat_times):
        mi,bi=position(i,phase,bpm)
        beats.append({
            "start_ms":int(round(float(t)*1000)),
            "measure_index":mi,
            "beat_index":bi,
            "subdivision_index":None,
        })

    return {
        "ok":True,
        "version":"r41.0o-compound-reference-meter",
        "tempo_bpm":round(tempo,3),
        "time_signature":signature,
        "key":key,
        "key_confidence":round(float(key_confidence),4),
        "key_method":key_method,
        "harmony_source":harmonic_source,
        "rhythm_source":rhythm_source,
        "noise_filter_enabled":bool(filter_noise),
        "harmonic_goal":"continuous_hq_then_project_to_canonical_beats",
        "chord_engine":CHORD_ENGINE,
        "chord_dictionary":CHORD_DICTIONARY,
        "chord_source":"original_audio",
        "downbeat_phase":phase,
        "metric_phase_offset":phase,
        "grid_positioning":"musical_downbeat_phase",
        "meter_confidence":round(float(meter_confidence),4),
        "phase_confidence":round(float(phase_confidence),4),
        "phase_preliminary":preliminary_phase,
        "phase_reference":_compound_signature_model(signature,bpm)["reference"],
        "compound_group_candidates":compound_group_candidates,
        "bar_phase_candidates":bar_phase_candidates,
        "phase_candidates":bar_phase_candidates,
        "meter_candidates":metric_scores,
        "diagnostics":diagnostics,
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
    p.add_argument("--filter-noise",action="store_true")
    p.add_argument("--progress-file")
    p.add_argument("--output")
    a=p.parse_args()
    try:
        result=analyse(Path(a.audio),a.stem,a.drums,a.time_signature,a.progress_file,a.filter_noise)
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
