"""Riffstation-style harmonic timeline helpers."""

from __future__ import annotations

import os
import tempfile

import librosa
import numpy as np
import plotly.graph_objects as go
import streamlit as st


def chord_regions(beats):
    regions=[]; current=None
    for beat in beats:
        chord=str(beat.get("accord","") or "")
        if chord==".":
            if current is not None: regions.append(current); current=None
            continue
        start=float(beat.get("temps",0.0)); end=float(beat.get("fin",start))
        if current is not None and current["accord"]==chord: current["fin"]=end
        else:
            if current is not None: regions.append(current)
            current={"accord":chord,"debut":start,"fin":end}
    if current is not None: regions.append(current)
    return regions


@st.cache_data(show_spinner=False)
def waveform_preview_cache(audio_bytes, extension, max_points=1800):
    suffix=str(extension or ".bin"); fd,path=tempfile.mkstemp(suffix=suffix); os.close(fd)
    try:
        with open(path,"wb") as f: f.write(audio_bytes)
        y,sr=librosa.load(path,sr=8000,mono=True)
    finally:
        try: os.remove(path)
        except OSError: pass
    if len(y)==0: return {"times":[],"amplitude":[],"duration":0.0}
    max_points=max(200,int(max_points)); step=max(1,int(np.ceil(len(y)/max_points)))
    chunks=[]; times=[]
    for start in range(0,len(y),step):
        chunk=y[start:start+step]
        if len(chunk)==0: continue
        chunks.append(float(np.max(np.abs(chunk)))); times.append(float(start/sr))
    arr=np.asarray(chunks,dtype=np.float64); peak=float(np.max(arr)) if len(arr) else 0.0
    if peak>0: arr=arr/peak
    return {"times":times,"amplitude":arr.tolist(),"duration":float(len(y)/sr)}


def _section_label(section):
    custom=str(section.get("custom_label","") or "").strip()
    if custom: return custom
    cluster=section.get("cluster","")
    return f"Bloc {cluster}" if cluster else "Bloc"


def create_harmonic_timeline(beats, sections, audio_bytes, extension):
    waveform=waveform_preview_cache(audio_bytes,extension); regions=chord_regions(beats); fig=go.Figure()
    times=waveform.get("times",[]); amplitudes=waveform.get("amplitude",[])
    if times and amplitudes:
        fig.add_trace(go.Scatter(x=times,y=amplitudes,mode="lines",name="Waveform",line=dict(width=1),hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=times,y=[-float(v) for v in amplitudes],mode="lines",name="Waveform",line=dict(width=1),hoverinfo="skip",showlegend=False))
    palette=["#ff7a18","#2f80ed","#27ae60","#9b51e0","#eb5757","#f2c94c","#56ccf2","#6fcf97","#bb6bd9","#f2994a","#219653","#2d9cdb"]; colors={}
    for region in regions:
        chord=region["accord"]; colors.setdefault(chord,palette[len(colors)%len(palette)])
        x0=float(region["debut"]); x1=float(region["fin"])
        fig.add_shape(type="rect",x0=x0,x1=x1,y0=-1.48,y1=-1.12,line=dict(width=0),fillcolor=colors[chord],opacity=0.95,layer="above")
        fig.add_trace(go.Scatter(x=[(x0+x1)/2.0],y=[-1.30],mode="text",text=[chord],textfont=dict(size=12),hovertemplate=f"<b>{chord}</b><br>{x0:.2f}s → {x1:.2f}s<extra></extra>",showlegend=False))
    for section in sections:
        x0=float(section.get("time_start",0.0)); x1=float(section.get("time_end",x0)); fig.add_vline(x=x0,line_width=1,opacity=0.20)
        if x1>x0: fig.add_annotation(x=(x0+x1)/2.0,y=1.18,text=_section_label(section),showarrow=False,font=dict(size=10))
    duration=float(waveform.get("duration",0.0) or max([float(b.get("fin",0.0)) for b in beats]+[1.0])); tick_step=30.0 if duration>=90.0 else 15.0
    tickvals=list(np.arange(0.0,duration+tick_step,tick_step)); ticktext=[f"{int(v//60):02d}:{int(v%60):02d}" for v in tickvals]
    fig.update_layout(height=430,margin=dict(l=10,r=10,t=36,b=30),showlegend=False,dragmode="zoom",hovermode="closest",xaxis=dict(title="Temps",range=[0,duration],tickmode="array",tickvals=tickvals,ticktext=ticktext,rangeslider=dict(visible=True),fixedrange=False),yaxis=dict(range=[-1.62,1.30],visible=False,fixedrange=True))
    return fig
