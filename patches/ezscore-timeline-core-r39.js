/* EZScore R39 — canonical musical timeline shared by ChordsLab and LyricsLab. */
(() => {
'use strict';
if (window.EZScoreTimelineCoreR39) return;

const num=(v,d=0)=>{const n=Number(v);return Number.isFinite(n)?n:d};
const parseSignature=value=>{const m=/^(\d+)\/(\d+)$/.exec(String(value||'4/4'));return m?{num:Math.max(1,Number(m[1])),den:Math.max(1,Number(m[2]))}:{num:4,den:4}};
const median=values=>{const a=values.filter(Number.isFinite).slice().sort((x,y)=>x-y);if(!a.length)return null;const i=Math.floor(a.length/2);return a.length%2?a[i]:(a[i-1]+a[i])/2};

function create({beats,timeSignature='4/4',spacing=166,preserveSourcePosition=true}) {
  const sig=parseSignature(timeSignature);
  const ordered=(Array.isArray(beats)?beats:[])
    .map((event,sourceSeq)=>({event,sourceSeq,startMs:num(event?.start_ms)}))
    .filter(row=>Number.isFinite(row.startMs))
    .sort((a,b)=>a.startMs-b.startMs||a.sourceSeq-b.sourceSeq);

  const projectionBeats=ordered.map((row,seq)=>{
    const sourceMeasure=Number(row.event?.measure_index),sourceBeat=Number(row.event?.beat_index);
    const sourceValid=preserveSourcePosition&&Number.isInteger(sourceMeasure)&&Number.isInteger(sourceBeat);
    return {...row.event,
      display_seq:seq,
      display_measure_index:sourceValid?sourceMeasure:Math.floor(seq/sig.num),
      display_beat_index:sourceValid?sourceBeat:seq%sig.num,
      display_start_ms:row.startMs};
  });

  const starts=projectionBeats.map(b=>num(b.start_ms)),deltas=[];
  for(let i=1;i<starts.length;i++){const d=starts[i]-starts[i-1];if(d>20)deltas.push(d)}
  const nominalMs=median(deltas)||500;
  const firstStartMs=Math.max(0,starts[0]||0),firstX=(firstStartMs/Math.max(20,nominalMs))*spacing;
  const xBeat=i=>firstX+i*spacing;

  function beatIndexAtMs(ms){
    ms=Math.max(0,num(ms));if(!starts.length||ms<starts[0])return-1;
    let lo=0,hi=starts.length-1,a=-1;
    while(lo<=hi){const m=(lo+hi)>>1;if(starts[m]<=ms){a=m;lo=m+1}else hi=m-1}
    return a;
  }
  function timeToX(ms){
    ms=Math.max(0,num(ms));if(!starts.length)return 0;
    if(ms<=starts[0])return firstStartMs>1?firstX*(ms/firstStartMs):0;
    const i=beatIndexAtMs(ms);if(i<0)return 0;
    if(i>=starts.length-1)return xBeat(i)+(ms-starts[i])/Math.max(20,nominalMs)*spacing;
    const t0=starts[i],t1=Math.max(t0+20,starts[i+1]),p=Math.max(0,Math.min(1,(ms-t0)/(t1-t0)));
    return xBeat(i)+p*spacing;
  }
  function beatPhaseAtMs(ms){
    const i=beatIndexAtMs(ms);if(i<0)return{beatIndex:-1,phase:0};
    const t0=starts[i],t1=i+1<starts.length?Math.max(t0+20,starts[i+1]):t0+nominalMs;
    return{beatIndex:i,phase:Math.max(0,Math.min(1,(num(ms)-t0)/(t1-t0)))};
  }
  function activeEventAt(events,ms){let current=null;for(const e of(events||[])){if(num(e.start_ms)<=ms)current=e;else break}return current}
  function eventStartingInBeat(events,beatIndex){
    const a=starts[beatIndex];if(!Number.isFinite(a))return null;
    const b=beatIndex+1<starts.length?starts[beatIndex+1]:a+nominalMs;
    return(events||[]).find(e=>num(e.start_ms)>=a&&num(e.start_ms)<b)||null;
  }
  function chordProjection(events,displayChord=(v=>v)){
    const sorted=(events||[]).slice().sort((a,b)=>num(a.start_ms)-num(b.start_ms)||(num(a.id)-num(b.id)));
    return projectionBeats.map((beat,seq)=>{
      const exact=eventStartingInBeat(sorted,seq),active=exact||activeEventAt(sorted,num(beat.start_ms));let text='-';
      if(exact)text=displayChord(exact.effective||exact.original||'.');
      else if((active?.effective||active?.original||'')==='.')text='.';
      else if(num(beat.display_beat_index)===0)text=displayChord(active?.effective||active?.original||'.');
      return{seq,beat,startMs:num(beat.start_ms),beatId:beat.id||null,eventId:exact?.id||null,activeEventId:active?.id||null,text,editable:!!beat.id};
    });
  }
  return{signature:sig,beats:projectionBeats,starts,spacing,nominalMs,xBeat,beatIndexAtMs,beatPhaseAtMs,timeToX,activeEventAt,eventStartingInBeat,chordProjection};
}

async function saveBeatOverride({urlTemplate,beatId,token,chord,profile}){
  const url=String(urlTemplate||'').replace('__BEAT__',String(beatId));if(!url)throw new Error('missing_beat_override_url');
  const response=await fetch(url,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','Accept':'application/json'},body:JSON.stringify({_token:token,chord,profile})});
  if(!response.ok)throw new Error(`beat_override_http_${response.status}`);
  return response.json().catch(()=>({ok:true}));
}

function syllableChunks(original,syllables){
  const source=String(original||'');if(!Array.isArray(syllables)||!syllables.length)return[source];
  const chunks=[];let cursor=0;const isLetter=c=>/\p{L}/u.test(c);
  for(let i=0;i<syllables.length;i++){
    const want=[...String(syllables[i]?.text||'')].filter(isLetter).length||1;let letters=0,out='';
    while(cursor<source.length){const ch=source[cursor++];out+=ch;if(isLetter(ch))letters++;if(letters>=want)break}
    if(i===syllables.length-1&&cursor<source.length)out+=source.slice(cursor);
    chunks.push(out||String(syllables[i]?.text||''));
  }
  return chunks;
}

function flattenSyllables(words){
  const rows=[];
  (words||[]).forEach((word,wordIndex)=>{
    const p=(word&&typeof word.payload==='object'&&word.payload)?word.payload:{};
    const syllables=Array.isArray(p.syllables)&&p.syllables.length?p.syllables:null;
    if(!syllables){
      const ms=num(p.cue_ms??word.start_ms);
      rows.push({wordIndex,syllableIndex:0,syllableCount:1,text:String(word.effective||word.original||''),display:String(word.effective||word.original||''),nucleusMs:ms,startMs:num(word.start_ms,ms),endMs:num(word.end_ms,ms+80),fallback:true,word});
      return;
    }
    const chunks=syllableChunks(String(word.effective||word.original||''),syllables);
    syllables.forEach((s,syllableIndex)=>{
      const nucleus=num(s.nucleus_ms??s.start_ms??p.cue_ms??word.start_ms);
      rows.push({wordIndex,syllableIndex,syllableCount:syllables.length,text:String(s.text||chunks[syllableIndex]||''),display:String(chunks[syllableIndex]||s.text||'')+(syllableIndex<syllables.length-1?'-':''),nucleusMs:nucleus,startMs:num(s.start_ms,nucleus),endMs:num(s.end_ms,nucleus+60),fallback:false,word});
    });
  });
  return rows.sort((a,b)=>a.nucleusMs-b.nucleusMs||a.wordIndex-b.wordIndex||a.syllableIndex-b.syllableIndex);
}

window.EZScoreTimelineCoreR39={create,saveBeatOverride,flattenSyllables,syllableChunks,version:'r39.0'};
})();
