#!/usr/bin/env python3
from __future__ import annotations

import shutil, subprocess, sys
from pathlib import Path

BASE_COMMIT='feb01ace289f751cc6a64e1aa6478fc3b5b59bb4'
ROOT=Path(sys.argv[1] if len(sys.argv)>1 else r'H:\EZScore_v1').resolve()
REL='analysis/chord_timeline_analysis.py'
TARGET=ROOT/REL

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

def write_atomic(path,text):
    tmp=path.with_suffix(path.suffix+'.r41j.tmp')
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
    original=TARGET.read_bytes()
    source=git_show(REL)
    baseline=[
      ('def detect_key(chroma_mean):' in source,'legacy key helper'),
      ('key,_=detect_key(np.mean(chroma,axis=1))' in source,'legacy chroma key call'),
      ('segments=analyze_chords_absolute(Path(source))' in source,'HQ chord call'),
      ('"key":key,' in source,'output key field'),
      ('"version":"r41.0b-hq-lv-chordia-historical-call"' in source,'analysis version'),
    ]
    bad=[name for ok,name in baseline if not ok]
    if bad: raise RuntimeError('R41.0J baseline mismatch: '+', '.join(bad)+'. STOP.')
    try:
        anchor='''def diatonic_roots(info):\n'''
        key_block = 'NOTE_TO_PC={\n    "C":0,"C#":1,"Db":1,"D":2,"D#":3,"Eb":3,"E":4,"F":5,\n    "F#":6,"Gb":6,"G":7,"G#":8,"Ab":8,"A":9,"A#":10,"Bb":10,"B":11,\n}\nMAJOR_KEY_TRIADS={0:"major",2:"minor",4:"minor",5:"major",7:"major",9:"minor",11:"dim"}\nMINOR_KEY_TRIADS={0:"minor",2:"dim",3:"major",5:"minor",7:"major",8:"major",10:"major"}\n\ndef parse_harmonic_chord(label):\n    text=str(label or ".").strip()\n    if not text or text in {".","N"}:return None\n    text=text.split("/",1)[0].strip()\n    root_name=None\n    for candidate in sorted(NOTE_TO_PC,key=len,reverse=True):\n        if text.startswith(candidate):\n            root_name=candidate\n            break\n    if root_name is None:return None\n    suffix=text[len(root_name):]\n    if suffix.startswith("maj"):\n        quality="major"\n    elif suffix.startswith("m") and not suffix.startswith("maj"):\n        quality="minor"\n    elif suffix.startswith("dim") or "m7b5" in suffix:\n        quality="dim"\n    elif suffix.startswith("aug") or suffix.startswith("+"):\n        quality="aug"\n    elif suffix.startswith("sus"):\n        quality="sus"\n    else:\n        quality="major"\n    dominant=(suffix.startswith("7") or suffix.startswith("9") or suffix.startswith("11") or suffix.startswith("13"))\n    return NOTE_TO_PC[root_name],quality,dominant\n\ndef chroma_key_score(chroma_mean,root,mode):\n    if chroma_mean is None or float(np.sum(chroma_mean))<=1e-9:return 0.0\n    x=np.asarray(chroma_mean,dtype=float)\n    x=x/max(float(np.linalg.norm(x)),1e-9)\n    profile=np.roll(MAJOR if mode=="major" else MINOR,root)\n    return cosine(x,profile)\n\ndef key_score_from_segments(segments,root,mode,chroma_mean=None):\n    degree_map=MAJOR_KEY_TRIADS if mode=="major" else MINOR_KEY_TRIADS\n    total=0.0\n    weighted=0.0\n    tonic_duration=0.0\n    dominant_duration=0.0\n    parsed_segments=[]\n\n    for segment in segments or []:\n        parsed=parse_harmonic_chord(segment.get("chord"))\n        if parsed is None:continue\n        start=float(segment.get("start",0.0) or 0.0)\n        end=float(segment.get("end",start) or start)\n        duration=max(0.0,end-start)\n        if duration<=1e-6:continue\n        chord_root,quality,is_dominant=parsed\n        rel=(chord_root-root)%12\n        expected=degree_map.get(rel)\n\n        value=-0.28\n        if expected is not None:\n            value=0.30\n            if quality==expected:value=1.00\n            elif quality=="sus":value=0.58\n            if mode=="minor" and rel==7 and quality=="major":\n                value=1.22\n            if rel==7 and is_dominant:\n                value+=0.18\n\n        if rel==0:\n            tonic_match=((mode=="major" and quality=="major") or (mode=="minor" and quality=="minor"))\n            if tonic_match:\n                value+=0.60\n                tonic_duration+=duration\n            else:\n                value-=0.20\n\n        if rel==7:\n            dominant_duration+=duration\n\n        total+=duration\n        weighted+=duration*value\n        parsed_segments.append((chord_root,quality,is_dominant,duration))\n\n    if total<=1e-6:return None\n\n    score=weighted/total\n    score+=0.38*(tonic_duration/total)\n    if mode=="minor":\n        score+=0.20*(dominant_duration/total)\n\n    if parsed_segments:\n        last_root,last_quality,_,_=parsed_segments[-1]\n        if last_root==root:\n            if (mode=="major" and last_quality=="major") or (mode=="minor" and last_quality=="minor"):\n                score+=0.16\n\n    score+=0.18*chroma_key_score(chroma_mean,root,mode)\n    return float(score)\n\ndef detect_key_from_segments(segments,chroma_mean=None):\n    ranked=[]\n    for root in range(12):\n        for mode in ("major","minor"):\n            score=key_score_from_segments(segments,root,mode,chroma_mean)\n            if score is not None:\n                ranked.append((float(score),root,mode))\n\n    if not ranked:\n        key,info=detect_key(chroma_mean)\n        return key,info,0.0,"chroma_no_parseable_hq_segments"\n\n    ranked.sort(reverse=True)\n    best_score,root,mode=ranked[0]\n    second_score=ranked[1][0] if len(ranked)>1 else best_score\n    confidence=max(0.0,best_score-second_score)\n    key=NOTES[root]+("" if mode=="major" else "m")\n    return key,(root,mode),float(confidence),"lv-chordia-duration+chroma-tiebreak"\n\n'
        source=rep(source,anchor,key_block+'def diatonic_roots(info):\n','key scorer insertion')
        old='''    prog(progress_file,30,"key","Estimation de la tonalité")\n    chroma=librosa.feature.chroma_cqt(y=yh,sr=sr,hop_length=hop)\n    chroma=np.maximum(chroma,0.0)\n    key,_=detect_key(np.mean(chroma,axis=1))\n\n    prog(progress_file,42,"chords_hq","Reconnaissance harmonique continue lv-chordia")\n    segments=analyze_chords_absolute(Path(source))\n\n    prog(progress_file,58,"beginner","Projection du profil Débutant")\n'''
        new='''    prog(progress_file,30,"key_features","Préparation du signal de tonalité")\n    chroma=librosa.feature.chroma_cqt(y=yh,sr=sr,hop_length=hop)\n    chroma=np.maximum(chroma,0.0)\n    chroma_mean=np.mean(chroma,axis=1)\n\n    prog(progress_file,42,"chords_hq","Reconnaissance harmonique continue lv-chordia")\n    segments=analyze_chords_absolute(Path(source))\n\n    prog(progress_file,52,"key","Estimation de la tonalité depuis les accords HQ")\n    key,_,key_confidence,key_method=detect_key_from_segments(segments,chroma_mean)\n\n    prog(progress_file,58,"beginner","Projection du profil Débutant")\n'''
        source=rep(source,old,new,'analysis key pipeline')
        source=rep(source,'"version":"r41.0b-hq-lv-chordia-historical-call"','"version":"r41.0j-hq-key-from-chords"','version')
        source=rep(source,'        "key":key,\n','        "key":key,\n        "key_confidence":round(float(key_confidence),4),\n        "key_method":key_method,\n','key metadata')
        contracts=[
          ('def detect_key_from_segments(segments,chroma_mean=None):' in source,'new key detector'),
          ('if mode=="minor" and rel==7 and quality=="major":' in source,'minor dominant evidence'),
          ('lv-chordia-duration+chroma-tiebreak' in source,'method metadata'),
          ('key,_,key_confidence,key_method=detect_key_from_segments(segments,chroma_mean)' in source,'HQ key call'),
          ('"key_confidence":round(float(key_confidence),4)' in source,'confidence output'),
          ('"key_method":key_method' in source,'method output'),
          ('segments=analyze_chords_absolute(Path(source))' in source,'HQ engine preserved'),
          ('def project_profile(level,segments,beat_times,bpm,phase,tempo):' in source,'projection preserved'),
        ]
        failed=[name for ok,name in contracts if not ok]
        if failed: raise RuntimeError('R41.0J2 invariant failed: '+', '.join(failed))
        write_atomic(TARGET,source)
        p=subprocess.run([sys.executable,'-m','py_compile',str(TARGET)],cwd=str(ROOT),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',check=False)
        if p.returncode!=0: raise RuntimeError('py_compile failed:\n'+p.stdout)
        print('[CACHE] Clearing Symfony dev cache...')
        cache_clear('dev')
        print('[CACHE] Clearing Symfony prod cache...')
        cache_clear('prod')
        print('R41_0J2_HQ_SONG_KEY_INSTALL_OK')
        return 0
    except Exception:
        TARGET.write_bytes(original)
        try:
            print('[ROLLBACK] Re-clearing Symfony dev cache on restored file...')
            cache_clear('dev')
        except Exception as e: print(f'[ROLLBACK WARNING] dev cache clear failed: {e}',file=sys.stderr)
        try:
            print('[ROLLBACK] Re-clearing Symfony prod cache on restored file...')
            cache_clear('prod')
        except Exception as e: print(f'[ROLLBACK WARNING] prod cache clear failed: {e}',file=sys.stderr)
        raise

if __name__=='__main__':
    try: raise SystemExit(main())
    except Exception as exc:
        print(f'ERROR: {exc}',file=sys.stderr)
        raise SystemExit(1)
