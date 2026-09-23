export default function(component){
  const data=component.data||{};
  const root=component.parentElement.querySelector('.ez-riff-root');
  if(!root)return;

  const defs=Array.isArray(data.tracks)?data.tracks:[];
  const beats=Array.isArray(data.beats)?data.beats:[];
  const words=Array.isArray(data.words)?data.words:[];
  const diagrams=data.chord_diagrams||{};

  const play=root.querySelector('.play');
  const pause=root.querySelector('.pause');
  const stop=root.querySelector('.stop');
  const seek=root.querySelector('.seek');
  const timeNode=root.querySelector('.time');
  const speed=root.querySelector('.playback-rate');
  const tracksNode=root.querySelector('.tracks');
  const master=root.querySelector('.master-volume');
  const masterValue=root.querySelector('.master-value');
  const stage=root.querySelector('.conductor-stage');
  const waveform=root.querySelector('.riff-waveform');
  const chordTrack=root.querySelector('.chord-track');
  const lyricWindow=root.querySelector('.lyric-window');
  const lyricTrack=root.querySelector('.lyric-track');
  const diagramCheck=root.querySelector('.show-diagrams');
  const diagramNode=root.querySelector('.current-diagram');
  const title=root.querySelector('.edit-title');
  const artist=root.querySelector('.edit-artist');
  const editor=root.querySelector('.edit-editor');
  const signature=root.querySelector('.edit-signature');
  const capo=root.querySelector('.edit-capo');
  const strum=root.querySelector('.edit-strum');
  const strumAlt=root.querySelector('.edit-strum-alt');
  const save=root.querySelector('.save-header');
  const summaryTitle=root.querySelector('.summary-title');
  const summaryArtist=root.querySelector('.summary-artist');
  const summaryEditor=root.querySelector('.summary-editor');
  const summarySignature=root.querySelector('.summary-signature');
  const summaryCapo=root.querySelector('.summary-capo');
  const summaryStrum=root.querySelector('.summary-strum');
  const form=root.querySelector('.editor-form');
  const editorWrap=root.querySelector('.editor-select-wrap');
  const modeBadge=root.querySelector('.mode-badge');

  const instanceId='riff16-'+String(Date.now())+'-'+Math.random().toString(36).slice(2);
  try{
    const previous=window.__EZScoreRiffstationAudioOwner;
    if(previous&&previous.id!==instanceId&&typeof previous.stop==='function')previous.stop();
  }catch(_){}

  const stepTabs=Array.from(root.querySelectorAll('.step-tab'));
  const activeStep=String(data.active_step||'1');
  stepTabs.forEach(btn=>{
    btn.classList.toggle('active',btn.dataset.step===activeStep);
    btn.onclick=()=>{
      const next=String(btn.dataset.step||'1');
      if(next!==activeStep){
        component.setStateValue('step_request',JSON.stringify({step:next,token:String(Date.now())}));
      }
    };
  });

  const text=v=>String(v??'').trim();
  const option=(value,label)=>{const o=document.createElement('option');o.value=String(value);o.textContent=String(label);return o;};
  title.value=text(data.song_title);
  artist.value=text(data.song_artist);
  strum.value=text(data.strumming_primary);
  strumAlt.value=text(data.strumming_secondary);
  summaryTitle.textContent=text(data.song_title)||'—';
  summaryArtist.textContent=text(data.song_artist)||'—';
  summaryEditor.textContent=text(data.song_editor)||'—';
  summarySignature.textContent=text(data.signature_label)||text(data.detected_signature)||'—';
  const setCapoSummary=()=>{const n=Number(data.capo||0);summaryCapo.textContent=n?('Capo '+n):'0 — sans capo';};
  setCapoSummary();
  summaryStrum.textContent=text(data.strumming_primary)||'—';
  modeBadge.textContent=text(data.step_label)||'Analyse';
  signature.innerHTML='';
  (Array.isArray(data.signature_options)?data.signature_options:[]).forEach(v=>signature.appendChild(option(v,v)));
  signature.value=text(data.signature_mode)||'Auto';
  capo.innerHTML='';
  for(let i=0;i<=12;i++)capo.appendChild(option(i,i===0?'0 — sans capo':'Capo '+i));
  capo.value=String(Number(data.capo||0));
  editor.innerHTML='';
  editor.appendChild(option('','— Aucun éditeur —'));
  (Array.isArray(data.editors)?data.editors:[]).forEach(e=>editor.appendChild(option(e.value,e.label)));
  editor.value=text(data.editor_user_id);
  editor.disabled=!Boolean(data.editor_selectable);
  if(!Boolean(data.editor_selectable))editorWrap.style.opacity='.75';
  if(Boolean(data.header_readonly)){
    form.classList.add('readonly');
    root.querySelector('.editor-details').style.display='none';
  }
  save.addEventListener('click',()=>{
    const payload={
      title:title.value,
      artist:artist.value,
      editor_user_id:editor.value,
      signature_mode:signature.value,
      capo:Number(capo.value||0),
      strumming_primary:strum.value,
      strumming_secondary:strumAlt.value,
      token:String(Date.now())
    };
    component.setStateValue('header_payload',JSON.stringify(payload));
  });

  let showDiagrams=Boolean(data.show_diagrams);
  diagramCheck.checked=showDiagrams;
  diagramCheck.addEventListener('change',()=>{
    showDiagrams=Boolean(diagramCheck.checked);
    component.setStateValue('show_diagrams',showDiagrams);
    renderDiagram(activeBeat);
  });
  lyricWindow.classList.toggle('hidden',!words.length);

  const trackState=defs.map(d=>({
    enabled:Boolean(d.enabled),
    volume:Number(d.volume??.75),
    low:Number(d.low||0),
    mid:Number(d.mid||0),
    high:Number(d.high||0)
  }));

  let context=null;
  let decoded=[];
  let trackNodes=[];
  let masterGain=null;
  let sources=[];
  let ready=false;
  let loading=false;
  let playing=false;
  let disposed=false;
  let raf=null;
  let duration=Number(data.duration_hint||0);
  let rate=1;
  let position=0;
  let startedAtContextTime=0;
  let activeBeat=-1;
  let activeWordIndex=-1;
  let lastWaveformTime=-999;

  const fmt=v=>{
    const n=Math.max(0,Number(v)||0);
    return Math.floor(n/60)+':'+String(Math.floor(n%60)).padStart(2,'0');
  };

  function dbToLinear(db){return Math.pow(10,Number(db||0)/20);}
  function compensationFor(s){
    const avg=(dbToLinear(s.low)+dbToLinear(s.mid)+dbToLinear(s.high))/3;
    if(!Number.isFinite(avg)||avg<=.0001)return 1;
    return Math.max(.72,Math.min(1.25,1/avg));
  }
  function currentTime(){
    if(!playing||!context)return position;
    return Math.max(0,Math.min(duration,position+(context.currentTime-startedAtContextTime)*rate));
  }
  function applyTrack(i,smooth=true){
    const n=trackNodes[i],s=trackState[i];
    if(!n||!context)return;
    const now=context.currentTime;
    const set=(param,value)=>{
      try{
        param.cancelScheduledValues(now);
        if(smooth)param.setTargetAtTime(value,now,.012);else param.value=value;
      }catch(_){param.value=value;}
    };
    set(n.lowGain.gain,dbToLinear(s.low));
    set(n.midGain.gain,dbToLinear(s.mid));
    set(n.highGain.gain,dbToLinear(s.high));
    set(n.trackGain.gain,(s.enabled?s.volume:0)*compensationFor(s));
  }
  function applyMaster(smooth=true){
    if(!masterGain||!context)return;
    const now=context.currentTime;
    try{
      masterGain.gain.cancelScheduledValues(now);
      if(smooth)masterGain.gain.setTargetAtTime(masterState,now,.012);else masterGain.gain.value=masterState;
    }catch(_){masterGain.gain.value=masterState;}
  }
  let masterState=1;

  function setToggleVisuals(){
    Array.from(tracksNode.querySelectorAll('.track-toggle input')).forEach((el,i)=>{
      el.checked=Boolean(trackState[i]?.enabled);
    });
  }
  function enforceSourceExclusivity(index){
    const name=String(defs[index]?.name||'');
    if(!trackState[index]?.enabled)return;
    if(name==='original'){
      trackState.forEach((s,i)=>{if(i!==index)s.enabled=false;});
    }else{
      const oi=defs.findIndex(d=>String(d.name||'')==='original');
      if(oi>=0)trackState[oi].enabled=false;
      if(name==='vocals'){
        defs.forEach((d,i)=>{
          if(['lead_vocals','backing_vocals'].includes(String(d.name||'')))trackState[i].enabled=false;
        });
      }
      if(['lead_vocals','backing_vocals'].includes(name)){
        const vi=defs.findIndex(d=>String(d.name||'')==='vocals');
        if(vi>=0)trackState[vi].enabled=false;
      }
    }
    setToggleVisuals();
    trackState.forEach((_,i)=>applyTrack(i,true));
  }

  async function readyAudio(){
    if(ready){if(context?.state==='suspended')await context.resume();return;}
    if(loading){
      while(loading)await new Promise(r=>setTimeout(r,40));
      if(context?.state==='suspended')await context.resume();
      return;
    }
    loading=true;
    play.disabled=true;
    const oldLabel=play.textContent;
    play.textContent='Chargement audio…';
    try{
      context=new (window.AudioContext||window.webkitAudioContext)({latencyHint:'interactive'});
      masterGain=context.createGain();
      masterGain.gain.value=masterState;
      masterGain.connect(context.destination);

      const buffers=await Promise.all(defs.map(async d=>{
        const response=await fetch(String(d.url||''),{cache:'force-cache'});
        if(!response.ok)throw new Error('HTTP média '+response.status+' pour '+String(d.label||d.name||'piste'));
        return context.decodeAudioData(await response.arrayBuffer());
      }));
      decoded=buffers;
      duration=Number(decoded[0]?.duration||duration||0);
      seek.max=String(Math.max(.001,duration));

      trackNodes=decoded.map(()=>{
        const lowLP=context.createBiquadFilter();
        lowLP.type='lowpass';lowLP.frequency.value=250;lowLP.Q.value=.707;
        const midHP=context.createBiquadFilter();
        midHP.type='highpass';midHP.frequency.value=250;midHP.Q.value=.707;
        const midLP=context.createBiquadFilter();
        midLP.type='lowpass';midLP.frequency.value=4000;midLP.Q.value=.707;
        const highHP=context.createBiquadFilter();
        highHP.type='highpass';highHP.frequency.value=4000;highHP.Q.value=.707;
        const lowGain=context.createGain();
        const midGain=context.createGain();
        const highGain=context.createGain();
        const bandSum=context.createGain();
        const trackGain=context.createGain();
        lowLP.connect(lowGain);lowGain.connect(bandSum);
        midHP.connect(midLP);midLP.connect(midGain);midGain.connect(bandSum);
        highHP.connect(highGain);highGain.connect(bandSum);
        bandSum.connect(trackGain);trackGain.connect(masterGain);
        return {lowLP,midHP,midLP,highHP,lowGain,midGain,highGain,bandSum,trackGain};
      });

      ready=true;
      trackState.forEach((_,i)=>applyTrack(i,false));
      applyMaster(false);
      drawWaveformWindow(position,true);
    }finally{
      loading=false;
      play.disabled=false;
      play.textContent=oldLabel||'▶ Lecture';
    }
  }

  function stopSources(){
    sources.forEach(src=>{
      try{src.stop();}catch(_){}
      try{src.disconnect();}catch(_){}
    });
    sources=[];
  }
  function startSources(offset){
    if(!context||!ready)return;
    stopSources();
    const when=context.currentTime+.030;
    sources=decoded.map((buffer,index)=>{
      const src=context.createBufferSource();
      src.buffer=buffer;
      src.playbackRate.value=rate;
      src.connect(trackNodes[index].lowLP);
      src.connect(trackNodes[index].midHP);
      src.connect(trackNodes[index].highHP);
      const safe=Math.max(0,Math.min(Number(offset)||0,Math.max(0,buffer.duration-.001)));
      src.start(when,safe);
      return src;
    });
    position=Math.max(0,Math.min(duration,Number(offset)||0));
    startedAtContextTime=when;
    playing=true;
  }
  async function playAll(){
    await readyAudio();
    if(context.state==='suspended')await context.resume();
    if(playing)return;
    if(position>=duration-.01)position=0;
    startSources(position);
  }
  function pauseAll(){
    if(!playing)return;
    position=currentTime();
    playing=false;
    stopSources();
    render(position);
  }
  function stopAll(){
    playing=false;
    stopSources();
    position=0;
    render(0);
  }
  function seekTo(v){
    const t=Math.max(0,Math.min(duration,Number(v)||0));
    position=t;
    if(playing)startSources(t);
    render(t);
  }
  function setRate(v){
    const newRate=Math.max(.5,Math.min(1.5,Number(v)||1));
    if(Math.abs(newRate-rate)<.0001)return;
    const t=currentTime();
    rate=newRate;
    if(playing)startSources(t);else position=t;
  }

  window.__EZScoreRiffstationAudioOwner={
    id:instanceId,
    stop:()=>{try{stopAll();}catch(_){}},
  };

  function slider(i,field,min,max,step,suffix){
    const w=document.createElement('div');w.className='control-cell';
    const s=document.createElement('input');s.type='range';s.min=min;s.max=max;s.step=step;s.value=trackState[i][field];
    const v=document.createElement('span');v.className='control-value';
    const ref=()=>{const n=Number(s.value);v.textContent=suffix==='dB'?((n>0?'+':'')+n.toFixed(0)+' dB'):(Math.round(n*100)+'%');};
    s.addEventListener('input',()=>{trackState[i][field]=Number(s.value);ref();applyTrack(i,true);});
    ref();w.append(s,v);return{w,s,v};
  }
  tracksNode.innerHTML='';
  defs.forEach((d,i)=>{
    const row=document.createElement('div');row.className='track';
    const n=document.createElement('div');n.className='track-name';n.textContent=String(d.label||d.name||'Piste');
    const tw=document.createElement('label');tw.className='track-toggle';
    const on=document.createElement('input');on.type='checkbox';on.checked=trackState[i].enabled;
    on.addEventListener('change',()=>{
      trackState[i].enabled=on.checked;
      enforceSourceExclusivity(i);
      applyTrack(i,true);
    });
    tw.append(on,document.createTextNode(' Actif'));
    const vol=slider(i,'volume',0,1.25,.01,'%');
    const lo=slider(i,'low',-12,12,1,'dB');
    const mi=slider(i,'mid',-12,12,1,'dB');
    const hi=slider(i,'high',-12,12,1,'dB');
    const reset=document.createElement('button');reset.className='eq-reset';reset.type='button';reset.textContent='Reset EQ';
    reset.addEventListener('click',()=>{
      ['low','mid','high'].forEach(f=>trackState[i][f]=0);
      [lo,mi,hi].forEach(o=>{o.s.value='0';o.v.textContent='0 dB';});
      applyTrack(i,true);
    });
    row.append(n,tw,vol.w,lo.w,mi.w,hi.w,reset);
    tracksNode.appendChild(row);
  });
  master.addEventListener('input',()=>{
    masterState=Number(master.value||1);
    masterValue.textContent=Math.round(masterState*100)+'%';
    applyMaster(true);
  });

  const starts=beats.map(b=>Number(b.start||0));
  const gaps=[];
  for(let i=1;i<starts.length;i++){
    const g=starts[i]-starts[i-1];
    if(Number.isFinite(g)&&g>.02)gaps.push(g);
  }
  gaps.sort((a,b)=>a-b);
  const nominal=gaps.length?gaps[Math.floor(gaps.length/2)]:.5;
  const spacing=Math.max(86,Number(data.beat_spacing||104));
  const firstStart=starts.length?Math.max(0,starts[0]):0;
  const firstX=firstStart/Math.max(.02,nominal)*spacing;
  const xBeat=i=>firstX+i*spacing;
  function beatIndex(t){
    if(!beats.length||Number(t)<starts[0])return-1;
    let lo=0,hi=starts.length-1,a=-1;
    while(lo<=hi){const m=(lo+hi)>>1;if(starts[m]<=t){a=m;lo=m+1;}else hi=m-1;}
    return a;
  }
  function metricX(t){
    t=Math.max(0,Number(t)||0);
    if(!starts.length)return t/Math.max(.02,nominal)*spacing;
    if(t<=starts[0])return firstStart>.001?firstX*(t/firstStart):0;
    const i=beatIndex(t);
    if(i<0)return 0;
    if(i>=starts.length-1)return xBeat(i)+(t-starts[i])/Math.max(.02,nominal)*spacing;
    const t0=starts[i],t1=Math.max(t0+.02,starts[i+1]);
    const p=Math.max(0,Math.min(1,(t-t0)/(t1-t0)));
    return xBeat(i)+p*spacing;
  }
  function timeForMetricX(x){
    const mx=Number(x)||0;
    if(!starts.length)return Math.max(0,mx/spacing*nominal);
    if(mx<=firstX){
      if(firstX<=.001)return 0;
      return Math.max(0,firstStart*(mx/firstX));
    }
    const f=(mx-firstX)/spacing;
    const i=Math.floor(f);
    const frac=f-i;
    if(i<0)return 0;
    if(i>=starts.length-1)return starts[starts.length-1]+(f-(starts.length-1))*nominal;
    return starts[i]+frac*(starts[i+1]-starts[i]);
  }

  const stripWidth=Math.max(1600,(beats.length?xBeat(beats.length-1):0)+spacing*8);
  chordTrack.style.width=stripWidth+'px';
  const beatsPerMeasure=Math.max(1,Number(data.beats_per_measure||4));
  const silenceChord=value=>{
    const c=String(value||'.').trim()||'.';
    return c==='.'||c.toUpperCase()==='N'||c.toUpperCase()==='NC'||c.toUpperCase()==='N.C.';
  };
  // Resolve any historical '-' hold token back to its sounding chord first.
  // Rendering can then repeat the chord explicitly on beat 1 of every measure.
  const effectiveChords=[];
  let sounding='.';
  beats.forEach((beat,index)=>{
    const raw=String(beat?.chord||'.').trim()||'.';
    if(raw==='-'){
      effectiveChords[index]=sounding;
    }else if(silenceChord(raw)){
      sounding='.';
      effectiveChords[index]='.';
    }else{
      sounding=raw;
      effectiveChords[index]=raw;
    }
  });
  const chordOf=i=>String(effectiveChords[i]??'.').trim()||'.';
  function beatTokenForMeasure(index,measureStart){
    if(index<0||index>=beats.length)return'.';
    const chord=chordOf(index);
    if(silenceChord(chord))return'.';
    // First beat of every measure is explicit, even when the same chord
    // continues from the preceding measure: [Cm|-|-|-] | [Cm|-|-|-].
    if(index===measureStart)return chord;
    const previous=chordOf(index-1);
    if(!silenceChord(previous)&&previous===chord)return'-';
    return chord;
  }

  const measureGroups=[];
  const beatCells=[];
  let measureNo=1;
  for(let start=0;start<beats.length;start+=beatsPerMeasure,measureNo+=1){
    const group=document.createElement('div');
    group.className='measure-group';
    group.dataset.measureStart=String(start);
    group.dataset.measureNo=String(measureNo);
    group.style.left=xBeat(start)+'px';
    group.style.width=(beatsPerMeasure*spacing)+'px';

    const number=document.createElement('span');
    number.className='measure-number';
    number.textContent='#'+measureNo;

    const row=document.createElement('div');
    row.className='measure-beats';
    row.style.setProperty('--beats',String(beatsPerMeasure));

    for(let offset=0;offset<beatsPerMeasure;offset+=1){
      const index=start+offset;
      const cell=document.createElement('span');
      cell.className='measure-beat';
      cell.dataset.beatIndex=String(index);
      cell.dataset.measureNo=String(measureNo);
      cell.textContent=index<beats.length?beatTokenForMeasure(index,start):'.';
      cell.title='Mesure '+measureNo+' · beat '+(offset+1)+'/'+beatsPerMeasure;
      row.appendChild(cell);
      if(index<beats.length)beatCells[index]=cell;
    }

    group.append(number,row);
    chordTrack.appendChild(group);
    measureGroups.push(group);
  }

  // The lyric line is a single continuous baseline.  We lay words out for
  // readability, then move that one line only when the active word changes.
  const wordNodes=words.map((word,index)=>{
    const node=document.createElement('span');
    node.className='word-token';
    node.dataset.wordIndex=String(index);
    node.textContent=String(word?.text||'').trim();
    lyricTrack.appendChild(node);
    return node;
  });
  const wordXs=[];
  function layoutWords(){
    let cursor=0;
    wordNodes.forEach((node,index)=>{
      const width=Math.max(12,node.getBoundingClientRect().width||node.offsetWidth||12);
      const center=cursor+width/2;
      wordXs[index]=center;
      node.style.left=center+'px';
      cursor+=width+18;
    });
    lyricTrack.style.width=Math.max(stage.clientWidth,cursor+240)+'px';
    renderWords(currentTime(),true);
  }
  function activeWord(t){
    if(!words.length)return-1;
    let lo=0,hi=words.length-1,a=-1;
    while(lo<=hi){
      const m=(lo+hi)>>1;
      if(Number(words[m].start||0)<=t){a=m;lo=m+1;}else hi=m-1;
    }
    return a;
  }
  function renderWords(t,force=false){
    if(!words.length)return;
    const wi=activeWord(t);
    if(!force&&wi===activeWordIndex)return;
    activeWordIndex=wi;
    wordNodes.forEach((node,index)=>{
      node.classList.toggle('past',wi>=0&&index<wi);
      node.classList.toggle('current',index===wi);
    });
    const axis=lineX();
    if(wi>=0&&Number.isFinite(wordXs[wi])){
      // Current word remains on the verse baseline and is centered under
      // the same playhead as the active beat.  No separate floating label.
      lyricTrack.style.setProperty('transform','translate3d('+(axis-wordXs[wi])+'px,0,0)','important');
    }else if(wordXs.length){
      lyricTrack.style.setProperty('transform','translate3d('+(axis+160-wordXs[0])+'px,0,0)','important');
    }
  }
  requestAnimationFrame(layoutWords);
  if(document.fonts?.ready){
    document.fonts.ready.then(()=>requestAnimationFrame(layoutWords)).catch(()=>{});
  }

  function renderDiagram(i){
    if(!showDiagrams||i<0){diagramNode.innerHTML='';diagramNode.classList.remove('visible');return;}
    const chord=chordOf(i);
    const svg=String(diagrams[chord]||'');
    diagramNode.innerHTML=svg;
    diagramNode.classList.toggle('visible',Boolean(svg));
  }
  function lineX(){
    const raw=getComputedStyle(root).getPropertyValue('--line-x').trim();
    const pct=raw.endsWith('%')?Number.parseFloat(raw)/100:.36;
    return Math.max(80,stage.clientWidth*(Number.isFinite(pct)?pct:.36));
  }

  function drawWaveformWindow(t,force=false){
    if(!ready||!decoded[0]||!waveform)return;
    if(!force&&Math.abs(t-lastWaveformTime)<.08)return;
    lastWaveformTime=t;
    const cssW=Math.max(1,Math.floor(stage.clientWidth));
    const cssH=112;
    const dpr=Math.max(1,Math.min(2,window.devicePixelRatio||1));
    if(waveform.width!==Math.floor(cssW*dpr)||waveform.height!==Math.floor(cssH*dpr)){
      waveform.width=Math.floor(cssW*dpr);
      waveform.height=Math.floor(cssH*dpr);
      waveform.style.width=cssW+'px';
      waveform.style.height=cssH+'px';
    }
    const ctx=waveform.getContext('2d');
    if(!ctx)return;
    ctx.setTransform(dpr,0,0,dpr,0,0);
    ctx.clearRect(0,0,cssW,cssH);
    const channel=decoded[0].getChannelData(0);
    const sr=decoded[0].sampleRate;
    const playX=lineX();
    ctx.strokeStyle='rgba(90,175,255,.72)';
    ctx.lineWidth=1;
    ctx.beginPath();
    for(let x=0;x<cssW;x+=2){
      const tx=timeForMetricX(metricX(t)+(x-playX));
      const center=Math.max(0,Math.min(channel.length-1,Math.floor(tx*sr)));
      const span=Math.max(1,Math.floor(sr*Math.max(.01,nominal)/spacing*2));
      let peak=0;
      const from=Math.max(0,center-span);
      const to=Math.min(channel.length,center+span);
      const step=Math.max(1,Math.floor((to-from)/24));
      for(let i=from;i<to;i+=step){const v=Math.abs(channel[i]||0);if(v>peak)peak=v;}
      const amp=Math.min(1,peak)*cssH*.43;
      const mid=cssH*.52;
      ctx.moveTo(x,mid-amp);
      ctx.lineTo(x,mid+amp);
    }
    ctx.stroke();
  }

  function render(t){
    const tm=Math.max(0,Number(t)||0);
    seek.value=String(tm);
    timeNode.textContent=fmt(tm)+' / '+fmt(duration);
    const x=lineX();
    chordTrack.style.transform='translate3d('+(x-metricX(tm))+'px,0,0)';
    const bi=beatIndex(tm);
    if(bi!==activeBeat){
      activeBeat=bi;
      const mi=bi<0?-1:Math.floor(bi/beatsPerMeasure);
      measureGroups.forEach((group,index)=>{
        group.classList.toggle('past',mi>=0&&index<mi);
        group.classList.toggle('current',index===mi);
      });
      beatCells.forEach((cell,index)=>{
        if(!cell)return;
        cell.classList.toggle('past',bi>=0&&index<bi);
        cell.classList.toggle('current',index===bi);
      });
      renderDiagram(bi);
    }
    renderWords(tm);
    drawWaveformWindow(tm,false);
  }

  speed.addEventListener('change',()=>setRate(speed.value));
  play.addEventListener('click',()=>playAll().catch(e=>{
    root.querySelector('.hint').textContent='Erreur audio : '+String(e?.message||e);
  }));
  pause.addEventListener('click',pauseAll);
  stop.addEventListener('click',stopAll);
  seek.addEventListener('input',()=>seekTo(seek.value));
  window.addEventListener('resize',()=>{layoutWords();drawWaveformWindow(currentTime(),true);render(currentTime());});

  function tick(){
    if(disposed)return;
    const t=currentTime();
    render(t);
    if(playing&&duration>0&&t>=duration-.02)stopAll();
    raf=requestAnimationFrame(tick);
  }

  seek.max=String(Math.max(.001,duration));
  render(0);
  tick();

  return()=>{
    disposed=true;
    if(raf!==null)cancelAnimationFrame(raf);
    try{stopSources();}catch(_){}
    try{if(context)context.close();}catch(_){}
    try{
      if(window.__EZScoreRiffstationAudioOwner?.id===instanceId){
        delete window.__EZScoreRiffstationAudioOwner;
      }
    }catch(_){}
  };
}
