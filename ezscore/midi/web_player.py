"""Browser SoundFont editor player synchronized to the original song."""

from __future__ import annotations

import base64
import html
import json

import streamlit as st

# GeneralUser GS is GM/GS compatible and can be cached by the browser/CDN.
DEFAULT_SOUNDFONT_URL = (
    "https://cdn.jsdelivr.net/gh/mrbumpy409/GeneralUser-GS@main/"
    "GeneralUser-GS.sf2"
)

_LIBFLUID_URL = (
    "https://cdn.jsdelivr.net/npm/js-synthesizer@1.13.0/"
    "externals/libfluidsynth-2.4.6.js"
)
_JS_SYNTH_URL = (
    "https://cdn.jsdelivr.net/npm/js-synthesizer@1.13.0/"
    "dist/js-synthesizer.min.js"
)


def _audio_mime(extension: str) -> str:
    return {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".ogg": "audio/ogg",
        ".m4a": "audio/mp4",
        ".aac": "audio/aac",
        ".flac": "audio/flac",
    }.get(str(extension or "").lower(), "audio/mpeg")


def render_editor_midi_player(
    audio_bytes: bytes,
    extension: str,
    midi_events,
    instrument_label: str,
    program: int,
    soundfont_url: str = DEFAULT_SOUNDFONT_URL,
):
    """Render the online editor's MP3 + SoundFont MIDI comparison player.

    The original media element is the master clock. FluidSynth runs inside
    the browser through js-synthesizer; no OS MIDI port is required.
    """
    if not midi_events:
        return

    audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
    mime = _audio_mime(extension)
    events_json = json.dumps(midi_events, ensure_ascii=False)
    instrument_json = json.dumps(str(instrument_label), ensure_ascii=False)
    soundfont_json = json.dumps(str(soundfont_url), ensure_ascii=False)

    document = r'''<!doctype html>
<html><head><meta charset="utf-8">
<style>
html,body{margin:0;padding:0;background:transparent;color:#ddd;font-family:Arial,Helvetica,sans-serif}
.wrap{border:1px solid rgba(130,140,160,.32);border-radius:10px;padding:12px 14px;background:rgba(120,130,145,.05)}
audio{width:100%}.controls{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:10px}
label{font-size:12px;opacity:.9;display:flex;flex-direction:column;gap:4px}
input[type=range]{width:100%}button{margin-top:9px;min-height:34px;border-radius:7px;border:1px solid rgba(130,140,160,.5);background:#20242a;color:#eee;padding:5px 10px}
.state{margin-top:8px;font-size:12px;opacity:.86}.now{margin-top:6px;font-size:15px;font-weight:700}.hint{margin-top:5px;font-size:11px;opacity:.68}
</style>
<script src="__LIBFLUID__"></script>
<script src="__JSSYNTH__"></script>
</head><body><div class="wrap">
<audio id="song" controls preload="metadata" src="data:__MIME__;base64,__AUDIO__"></audio>
<div class="controls">
<label>Volume chanson<input id="songVol" type="range" min="0" max="1.5" step="0.01" value="0.85"></label>
<label>Volume MIDI<input id="midiVol" type="range" min="0" max="2" step="0.01" value="0.65"></label>
</div>
<button id="init" type="button">Charger le synthé MIDI</button>
<div class="state" id="state">Synthé non chargé · Instrument : __INSTRUMENT__</div>
<div class="now" id="now">Accord : —</div>
<div class="hint">MP3 maître · FluidSynth/SoundFont dans le navigateur · aucune sortie MIDI système requise.</div>
</div>
<script>
const events=__EVENTS__;
const PROGRAM=__PROGRAM__;
const SF_URL=__SOUNDFONT__;
const audio=document.getElementById('song');
const initBtn=document.getElementById('init');
const state=document.getElementById('state');
const now=document.getElementById('now');
const songVol=document.getElementById('songVol');
const midiVol=document.getElementById('midiVol');
let ctx=null,synth=null,sfontId=null,synthNode=null,mediaSource=null,songGain=null;
let cursor=0,timer=null,lastMediaTime=0,ready=false;

function lowerBound(t){let lo=0,hi=events.length;while(lo<hi){const m=(lo+hi)>>1;if(events[m].time<t)lo=m+1;else hi=m;}return lo;}
function silence(){if(!synth)return;try{synth.midiAllNotesOff();synth.midiAllSoundsOff();}catch(e){}}
function selectProgram(){if(synth&&sfontId!==null){synth.midiProgramSelect(0,sfontId,0,PROGRAM);}}
function resetAt(t){silence();selectProgram();cursor=lowerBound(Math.max(0,t-0.003));now.textContent='Accord : —';lastMediaTime=t;}
function dispatch(e){if(!synth)return;if(e.kind==='program'){selectProgram();return;}if(e.kind==='note_on'){synth.midiNoteOn(0,e.data1,e.data2||0);if(e.chord)now.textContent='Accord : '+e.chord;}else if(e.kind==='note_off'){synth.midiNoteOff(0,e.data1);}}
function pump(){if(!ready||audio.paused||audio.ended)return;const t=audio.currentTime;if(t+0.04<lastMediaTime||Math.abs(t-lastMediaTime)>0.35)resetAt(t);lastMediaTime=t;while(cursor<events.length&&events[cursor].time<=t+0.008){const e=events[cursor++];if(e.time>=t-0.035||e.kind==='program')dispatch(e);}}
function startScheduler(){if(timer)clearInterval(timer);timer=setInterval(pump,8);pump();}
function stopScheduler(){if(timer){clearInterval(timer);timer=null;}}

async function initSynth(){
  if(ready){if(ctx&&ctx.state==='suspended')await ctx.resume();return;}
  initBtn.disabled=true;state.textContent='Chargement FluidSynth…';
  try{
    await JSSynth.waitForReady();
    ctx=new (window.AudioContext||window.webkitAudioContext)({latencyHint:'interactive'});
    synth=new JSSynth.Synthesizer();
    synth.init(ctx.sampleRate,{initialGain:parseFloat(midiVol.value),reverbActive:false,chorusActive:false});
    synthNode=synth.createAudioNode(ctx,512);synthNode.connect(ctx.destination);
    mediaSource=ctx.createMediaElementSource(audio);songGain=ctx.createGain();songGain.gain.value=parseFloat(songVol.value);mediaSource.connect(songGain);songGain.connect(ctx.destination);audio.volume=1;
    state.textContent='Chargement SoundFont…';
    const response=await fetch(SF_URL,{cache:'force-cache'});if(!response.ok)throw new Error('SoundFont HTTP '+response.status);
    const sf=await response.arrayBuffer();sfontId=await synth.loadSFont(sf);selectProgram();
    ready=true;state.textContent='Prêt · '+__INSTRUMENT_JSON__;initBtn.textContent='Synthé MIDI prêt';
  }catch(err){console.error(err);state.textContent='Erreur synthé/SoundFont : '+err.message;initBtn.disabled=false;}
}

initBtn.addEventListener('click',async()=>{await initSynth();if(ctx&&ctx.state==='suspended')await ctx.resume();});
songVol.addEventListener('input',()=>{if(songGain)songGain.gain.value=parseFloat(songVol.value);});
midiVol.addEventListener('input',()=>{if(synth)synth.setGain(parseFloat(midiVol.value));});
audio.addEventListener('play',async()=>{if(!ready){audio.pause();state.textContent='Cliquez d’abord sur « Charger le synthé MIDI ».';return;}if(ctx.state==='suspended')await ctx.resume();resetAt(audio.currentTime);startScheduler();});
audio.addEventListener('pause',()=>{stopScheduler();silence();});
audio.addEventListener('ended',()=>{stopScheduler();silence();});
audio.addEventListener('seeking',()=>{stopScheduler();silence();});
audio.addEventListener('seeked',()=>{if(ready)resetAt(audio.currentTime);if(ready&&!audio.paused)startScheduler();});
window.addEventListener('beforeunload',()=>{stopScheduler();silence();try{synth&&synth.close();}catch(e){};});
</script></body></html>'''

    html_doc = (
        document
        .replace("__LIBFLUID__", _LIBFLUID_URL)
        .replace("__JSSYNTH__", _JS_SYNTH_URL)
        .replace("__MIME__", mime)
        .replace("__AUDIO__", audio_b64)
        .replace("__EVENTS__", events_json)
        .replace("__PROGRAM__", str(int(program)))
        .replace("__SOUNDFONT__", soundfont_json)
        .replace("__INSTRUMENT__", html.escape(str(instrument_label)))
        .replace("__INSTRUMENT_JSON__", instrument_json)
    )
    st.html(html_doc, width="stretch", unsafe_allow_javascript=True)
