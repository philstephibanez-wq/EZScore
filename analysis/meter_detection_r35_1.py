#!/usr/bin/env python3
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import librosa

CANDIDATES = ("2/4", "3/4", "4/4", "6/8")

@dataclass(frozen=True)
class MeterResult:
    signature: str
    phase: int
    confidence: float
    scores: dict[str, float]
    sources: dict[str, str]

def _z(x):
    x=np.asarray(x,dtype=float)
    return x if x.size==0 else (x-np.mean(x))/(np.std(x)+1e-9)

def _sample(feature, beat_frames):
    if len(feature)==0 or len(beat_frames)==0: return np.zeros(len(beat_frames))
    return _z(feature[np.clip(np.asarray(beat_frames,dtype=int),0,len(feature)-1)])

def _bass_activity(y,sr,hop,beat_frames):
    if y is None or len(y)==0: return np.zeros(len(beat_frames))
    cqt=np.abs(librosa.cqt(y=y,sr=sr,hop_length=hop,fmin=librosa.note_to_hz("C1"),n_bins=36,bins_per_octave=12))
    low=np.mean(cqt[:24],axis=0)
    delta=np.r_[0.0,np.maximum(0.0,np.diff(low))]
    return _sample(low+0.75*delta,beat_frames)

def _harmonic_change(y,sr,hop,beat_frames):
    chroma=librosa.feature.chroma_cqt(y=y,sr=sr,hop_length=hop)
    if chroma.shape[1]<2: return np.zeros(len(beat_frames))
    chroma/=np.maximum(np.linalg.norm(chroma,axis=0,keepdims=True),1e-9)
    d=np.zeros(chroma.shape[1]);d[1:]=1.0-np.sum(chroma[:,1:]*chroma[:,:-1],axis=0)
    return _sample(d,beat_frames)

def _phase_score(signal,period,phase):
    n=len(signal)
    if n<period*3:return -1e6
    pos=(np.arange(n)-phase)%period
    down=signal[pos==0]; other=signal[pos!=0]
    accent=float(np.mean(down)-np.mean(other)) if down.size and other.size else 0.0
    accent=float(np.clip(accent,-1.25,1.25))
    bars=[signal[s:s+period] for s in range(phase,n-period+1,period)]
    if len(bars)<3:return -1e6
    matrix=np.vstack(bars);profile=np.mean(matrix,axis=0);den=np.linalg.norm(profile)+1e-9
    consistency=float(np.mean([np.dot(row,profile)/((np.linalg.norm(row)+1e-9)*den) for row in matrix]))
    # Long-horizon coherence dominates immediate accent: reggae/syncopation safe.
    return 0.35*accent+0.65*consistency

def _six_eight_bonus(rhythm,phase):
    if len(rhythm)<18:return 0.0
    pos=(np.arange(len(rhythm))-phase)%6
    strong=rhythm[(pos==0)|(pos==3)];rest=rhythm[(pos!=0)&(pos!=3)]
    if not strong.size or not rest.size:return 0.0
    return float(np.clip(np.mean(strong)-np.mean(rest),-1.0,1.0))*0.18

def detect_meter(*, rhythm_y, harmonic_y, bass_y, sr, hop, onset, beat_frames):
    beat_frames=np.asarray(beat_frames,dtype=int)
    if beat_frames.size<8:
        return MeterResult("4/4",0,0.0,{"4/4":0.0},{"rhythm":"mix","bass":"unavailable","harmony":"mix"})
    rhythm=_sample(onset,beat_frames)
    bass=_bass_activity(bass_y,sr,hop,beat_frames)
    harmony=_harmonic_change(harmonic_y,sr,hop,beat_frames)
    fused=0.62*rhythm+0.25*bass+0.13*harmony
    periods={"2/4":2,"3/4":3,"4/4":4,"6/8":6}
    best={}
    for sig,period in periods.items():
        candidate=(-1e9,0)
        for phase in range(period):
            score=(0.50*_phase_score(fused,period,phase)+0.28*_phase_score(rhythm,period,phase)+0.14*_phase_score(bass,period,phase)+0.08*_phase_score(harmony,period,phase))
            if sig=="6/8":score+=_six_eight_bonus(rhythm,phase)
            if sig=="4/4":score+=0.025
            if score>candidate[0]:candidate=(float(score),phase)
        best[sig]=candidate
    ordered=sorted(best.items(),key=lambda kv:kv[1][0],reverse=True)
    sig,(top,phase)=ordered[0];second=ordered[1][1][0] if len(ordered)>1 else top
    return MeterResult(sig,int(phase),float(np.clip(0.5+(top-second),0.0,1.0)),{k:round(v[0],5) for k,v in best.items()},{"rhythm":"drums_or_mix","bass":"bass_stem" if bass_y is not None else "derived_from_harmony","harmony":"harmony_stems_or_mix"})
