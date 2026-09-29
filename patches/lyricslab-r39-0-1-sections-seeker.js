/* R39.0.1 — restore sections + manual seeker on canonical timeline */
(() => {
'use strict';
const Previous=window.EZScoreLyricsTimelineR39;
if(!Previous||typeof Previous.mount!=='function')return;

const originalMount=Previous.mount.bind(Previous);

Previous.mount=function(root){
  originalMount(root);

  const parse=v=>{try{return JSON.parse(v||'[]')}catch(_){return[]}};
  const words=parse(root.dataset.lyrics);
  const beats=parse(root.dataset.beats).slice().sort((a,b)=>Number(a.start_ms)-Number(b.start_ms));
  const sourceBox=document.querySelector('[data-lyrics-source]');
  const panel=root.closest('section');
  const title=panel?.querySelector('.chordslab-prompter-head h2');
  const mixer=document.querySelector('[data-stem-mixer]');
  const stage=root.querySelector('[data-stage]');

  function payload(w){return w&&typeof w.payload==='object'&&w.payload?w.payload:{}}
  function declaredSections(text){
    const out=[];
    String(text||'').replace(/\r\n?/g,'\n').split('\n').forEach(line=>{
      const s=line.trim();if(!s)return;
      let m=/^\[([^\[\]\r\n]{1,120})\]$/.exec(s);
      if(!m)m=/^([^\r\n:]{1,120}):$/.exec(s);
      if(m&&m[1].trim())out.push({label:m[1].trim(),start:null});
    });
    return out;
  }
  function nextBeatAtOrAfter(sec){
    const ms=Math.max(0,Number(sec||0)*1000);
    for(const b of beats)if(Number(b.start_ms)>=ms)return Number(b.start_ms)/1000;
    return Number(sec||0);
  }
  function buildSections(){
    const declared=declaredSections(sourceBox?.value||'');
    if(!declared.length)return[];
    const transitions=[];let previous='';
    words.forEach((w,i)=>{
      const label=String(payload(w).section_label||'').trim();
      if(label&&label!==previous){transitions.push({label,start:Number(w.start_ms||0)/1000,index:i});previous=label}
    });
    let cursor=0;
    declared.forEach((section,index)=>{
      for(let j=cursor;j<transitions.length;j++){
        if(transitions[j].label===section.label){section.start=transitions[j].start;cursor=j+1;break}
      }
      if(section.start==null){
        if(index===0)section.start=0;
        else{
          const prev=declared[index-1];
          let end=Number(prev.start||0);
          for(const w of words){
            if(String(payload(w).section_label||'').trim()===prev.label){
              end=Math.max(end,Number(w.end_ms||w.start_ms||0)/1000);
            }
          }
          section.start=nextBeatAtOrAfter(end);
        }
      }
    });
    for(let i=1;i<declared.length;i++)declared[i].start=Math.max(Number(declared[i-1].start||0),Number(declared[i].start||0));
    return declared;
  }

  const sections=buildSections();
  let currentSection=-1;

  if(title&&sections.length){
    let nav=panel.querySelector('[data-section-nav]');
    if(!nav){
      nav=document.createElement('div');
      nav.className='lyrics-section-nav';
      nav.dataset.sectionNav='';
      title.insertAdjacentElement('afterend',nav);
    }
    nav.innerHTML='';
    sections.forEach((s,i)=>{
      const b=document.createElement('button');
      b.type='button';b.className='lyrics-section-chip';b.dataset.sectionIndex=String(i);b.textContent=s.label;
      b.addEventListener('click',()=>{
        mixer?.dispatchEvent(new CustomEvent('ezscore:request-seek',{detail:{time:s.start}}));
        updateSection(s.start);
      });
      nav.appendChild(b);
    });
  }

  function updateSection(sec){
    if(!sections.length)return;
    const i=sections.reduce((a,s,idx)=>Number(s.start)<=sec?idx:a,-1);
    if(i===currentSection)return;
    currentSection=i;
    panel?.querySelectorAll('.lyrics-section-chip.current').forEach(e=>e.classList.remove('current'));
    panel?.querySelector(`.lyrics-section-chip[data-section-index="${i}"]`)?.classList.add('current');
  }

  /* Dedicated manual seeker for chord editing. It drives the shared audio clock;
     it never changes timeline geometry. */
  let seeker=root.querySelector('[data-lyrics-manual-seeker]');
  if(!seeker&&stage){
    const shell=document.createElement('div');
    shell.className='lyrics-manual-seeker';
    shell.innerHTML='<label><span>Position</span><input type="range" min="0" max="1" step="0.01" value="0" data-lyrics-manual-seeker><output data-lyrics-manual-seeker-time>0:00.00</output></label>';
    stage.insertAdjacentElement('beforebegin',shell);
    seeker=shell.querySelector('[data-lyrics-manual-seeker]');
  }
  const output=root.querySelector('[data-lyrics-manual-seeker-time]');
  const durationSec=Math.max(
    Number(beats.at(-1)?.start_ms||0),
    Number(words.at(-1)?.end_ms||words.at(-1)?.start_ms||0)
  )/1000;
  if(seeker)seeker.max=String(Math.max(1,durationSec+2));

  const fmt=sec=>{
    sec=Math.max(0,Number(sec)||0);
    const m=Math.floor(sec/60),s=sec-m*60;
    return `${m}:${s.toFixed(2).padStart(5,'0')}`;
  };

  let dragging=false;
  function seekTo(value){
    const sec=Math.max(0,Math.min(Number(seeker?.max||0),Number(value)||0));
    if(output)output.textContent=fmt(sec);
    mixer?.dispatchEvent(new CustomEvent('ezscore:request-seek',{detail:{time:sec}}));
    updateSection(sec);
  }
  seeker?.addEventListener('pointerdown',()=>{dragging=true});
  seeker?.addEventListener('pointerup',()=>{dragging=false;seekTo(seeker.value)});
  seeker?.addEventListener('input',()=>seekTo(seeker.value));
  seeker?.addEventListener('change',()=>seekTo(seeker.value));

  mixer?.addEventListener('ezscore:audio-timeupdate',e=>{
    const sec=Math.max(0,Number(e.detail?.time||0));
    if(seeker&&!dragging)seeker.value=String(sec);
    if(output)output.textContent=fmt(sec);
    updateSection(sec);
  });

  root.dataset.sectionsRestored='r39.0.1';
  root.dataset.manualSeeker='r39.0.1';
};
})();
