#!/usr/bin/env python3
from __future__ import annotations
import argparse,difflib,json,os,re,time,unicodedata
from pathlib import Path

def write_json(path,payload):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(p.suffix+'.tmp')
    tmp.write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
    tmp.replace(p)

def prog(path,pct,stage,message):
    if path:write_json(path,{'percent':int(pct),'stage':stage,'message':message,'updated_at':time.time()})

def norm(s):
    s=unicodedata.normalize('NFKD',s.lower())
    s=''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9']+",'',s)

def supplied_tokens(text):
    out=[];lines=text.replace('\r\n','\n').replace('\r','\n').split('\n')
    for li,line in enumerate(lines):
        words=re.findall(r'\S+',line)
        for wi,w in enumerate(words):
            out.append({'text':w,'norm':norm(w),'line_break_after':wi==len(words)-1 and li<len(lines)-1})
    return out

def asr_words(result):
    out=[]
    for seg in result.get('segments',[]):
        for w in seg.get('words',[]) or []:
            txt=str(w.get('word','')).strip()
            if not txt:continue
            out.append({'text':txt,'norm':norm(txt),'start_ms':int(round(float(w.get('start',0))*1000)),'end_ms':int(round(float(w.get('end',w.get('start',0)))*1000)),'confidence':float(w.get('probability',0.0) or 0.0)})
    return out

def interpolate(rows):
    known=[i for i,r in enumerate(rows) if r.get('start_ms') is not None]
    if not known:return rows
    for i,r in enumerate(rows):
        if r.get('start_ms') is not None:continue
        left=max((k for k in known if k<i),default=None);right=min((k for k in known if k>i),default=None)
        if left is not None and right is not None:
            span=max(1,right-left);ratio=(i-left)/span;a=rows[left]['end_ms'];b=rows[right]['start_ms']
            t=int(round(a+(b-a)*ratio));r['start_ms']=t;r['end_ms']=t+120;r['confidence']=0.35
        elif left is not None:
            t=rows[left]['end_ms']+max(80,(i-left-1)*180);r['start_ms']=t;r['end_ms']=t+160;r['confidence']=0.25
        elif right is not None:
            t=max(0,rows[right]['start_ms']-max(160,(right-i)*180));r['start_ms']=t;r['end_ms']=min(rows[right]['start_ms'],t+160);r['confidence']=0.25
    return rows

def align(provided,recognized):
    a=[r['norm'] for r in provided];b=[r['norm'] for r in recognized]
    sm=difflib.SequenceMatcher(a=a,b=b,autojunk=False)
    rows=[dict(r,start_ms=None,end_ms=None,confidence=0.0) for r in provided]
    for tag,i1,i2,j1,j2 in sm.get_opcodes():
        if tag=='equal':
            for di,dj in zip(range(i1,i2),range(j1,j2)):
                for k in ('start_ms','end_ms','confidence'):rows[di][k]=recognized[dj][k]
        elif tag=='replace':
            n=min(i2-i1,j2-j1)
            for off in range(n):
                src=recognized[j1+off];rows[i1+off].update(start_ms=src['start_ms'],end_ms=src['end_ms'],confidence=max(0.2,src['confidence']*.6))
    return interpolate(rows)

def model_path():
    explicit=os.environ.get('EZSCORE_WHISPER_MODEL')
    if explicit and Path(explicit).is_file():return explicit
    for p in [r'H:\EZScoreModels\whisper\large-v3-turbo.pt',r'H:\EZScoreModels\whisper\medium.pt',r'H:\EZScoreModels\whisper\small.pt']:
        if Path(p).is_file():return p
    raise RuntimeError('No EZScore Whisper model found')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--audio',required=True);ap.add_argument('--lyrics-file',required=True);ap.add_argument('--output',required=True)
    ap.add_argument('--progress-file');ap.add_argument('--language',default='fr')
    a=ap.parse_args()
    text=Path(a.lyrics_file).read_text(encoding='utf-8');provided=supplied_tokens(text)
    if not provided:raise RuntimeError('Lyrics text is empty')
    prog(a.progress_file,5,'load','Chargement du texte fourni')
    import torch
    if not torch.cuda.is_available():raise RuntimeError('CUDA required for LyricsLab; CPU fallback disabled')
    import whisper
    prog(a.progress_file,15,'model','Chargement Whisper CUDA')
    model=whisper.load_model(model_path(),device='cuda')
    prog(a.progress_file,28,'transcribe','Repérage temporel des mots')
    result=model.transcribe(a.audio,language=a.language,fp16=True,word_timestamps=True,condition_on_previous_text=True,verbose=False)
    recognized=asr_words(result)
    if not recognized:raise RuntimeError('Whisper returned no timed words')
    prog(a.progress_file,72,'align','Alignement du texte fourni sur l’audio')
    rows=align(provided,recognized)
    words=[{'text':r['text'],'start_ms':int(r['start_ms'] or 0),'end_ms':int(r['end_ms'] or (r['start_ms'] or 0)+120),'line_break_after':bool(r['line_break_after']),'confidence':round(float(r.get('confidence',0.0)),4)} for r in rows]
    write_json(a.output,{'ok':True,'version':'r36.0-provided-text-whisper-anchor','language':a.language,'provided_words':len(provided),'recognized_words':len(recognized),'words':words})
    prog(a.progress_file,100,'complete','Paroles ancrées sur la timeline')

if __name__=='__main__':main()
