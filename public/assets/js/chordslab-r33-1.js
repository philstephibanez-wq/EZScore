(() => {
'use strict';

const root=document.querySelector('[data-chordslab]');
const strip=root?.querySelector('[data-chordslab-measures]');
const keepAwake=document.querySelector('[data-chordslab-wakelock]');
const mixer=document.querySelector('[data-stem-mixer]');
const diagramToggle=document.querySelector('[data-chordslab-diagram]');
if(!root||!strip)return;

let wakeLock=null;
let playbackActive=false;
const wakeKey='ezscore.chordslab.keepAwake';

function installR345Styles(){
    if(document.getElementById('ezscore-r34-5-style'))return;
    const style=document.createElement('style');
    style.id='ezscore-r34-5-style';
    style.textContent=`
/* R34.5 — final high-priority ChordsLab visual corrections */
.chord-measure-notation .chord-slot.is-long,
.chord-measure-notation .chord-slot.is-very-long{
    font-size:14px!important;
    letter-spacing:normal!important;
}
.chord-measure-notation .chord-slot .chord-label-root{
    font-size:15px!important;
    font-weight:800!important;
    line-height:1!important;
    flex:0 0 auto!important;
}
.chord-measure-notation .chord-slot .chord-label-suffix{
    font-size:11px!important;
    line-height:1!important;
    flex:0 0 auto!important;
    margin-left:1px!important;
}
.chord-measure-notation .chord-slot .chord-quality-maj{
    display:inline-block!important;
    font-size:8px!important;
    line-height:1!important;
    vertical-align:super!important;
    margin:0 1px 0 0!important;
    letter-spacing:0!important;
}
.chord-measure-notation .chord-slot .chord-label-bass{
    font-size:10px!important;
    line-height:1!important;
    margin-left:1px!important;
}

.chordslab-settings-grid .chordslab-diagram-toggle,
.chordslab-settings-grid .chordslab-diagram-inline{
    grid-column:1 / -1!important;
    display:flex!important;
    grid-template-columns:none!important;
    align-items:center!important;
    gap:8px!important;
    width:max-content!important;
    max-width:100%!important;
    padding:0!important;
    margin:0!important;
}
.chordslab-settings-grid .chordslab-diagram-toggle>span,
.chordslab-settings-grid .chordslab-diagram-inline>span{
    display:inline!important;
    margin:0!important;
    white-space:nowrap!important;
    font-size:13px!important;
    line-height:1.2!important;
    font-weight:600!important;
    text-transform:none!important;
    letter-spacing:0!important;
    color:#eef5f8!important;
}
.chordslab-settings-grid .chordslab-diagram-toggle input[type=checkbox],
.chordslab-settings-grid .chordslab-diagram-inline input[type=checkbox]{
    flex:0 0 auto!important;
    margin:0!important;
}
.chordslab-settings-save-state{
    grid-column:1 / -1!important;
    margin-top:-3px!important;
    min-width:0!important;
    white-space:nowrap!important;
}

.chordslab-tempo-runtime{
    display:grid;
    gap:3px;
}
.chordslab-tempo-runtime span{
    font-size:10px;
    text-transform:uppercase;
    color:#91a3ad;
    letter-spacing:.05em;
}
.chordslab-tempo-runtime strong{
    font-size:15px;
}

@media(max-width:640px){
    .chordslab-settings-grid .chordslab-diagram-toggle,
    .chordslab-settings-grid .chordslab-diagram-inline{
        width:100%!important;
    }
    .chordslab-settings-grid .chordslab-diagram-toggle>span,
    .chordslab-settings-grid .chordslab-diagram-inline>span{
        white-space:normal!important;
    }
}`;
    document.head.appendChild(style);
}

function installTempo(){
    const card=document.querySelector('.chordslab-song-card');
    if(!card||card.querySelector('[data-chordslab-tempo-runtime]'))return;

    let beats=[];
    try{beats=JSON.parse(root.dataset.beats||'[]')}catch(_){beats=[]}
    if(!Array.isArray(beats)||beats.length<3)return;

    const deltas=[];
    for(let i=1;i<beats.length;i++){
        const d=Number(beats[i].start_ms)-Number(beats[i-1].start_ms);
        if(Number.isFinite(d)&&d>=180&&d<=2000)deltas.push(d);
    }
    if(!deltas.length)return;

    deltas.sort((a,b)=>a-b);
    const mid=Math.floor(deltas.length/2);
    const median=deltas.length%2?deltas[mid]:(deltas[mid-1]+deltas[mid])/2;
    const tempo=Math.round(60000/median);
    if(!Number.isFinite(tempo)||tempo<=0)return;

    const box=document.createElement('div');
    box.className='chordslab-tempo-runtime';
    box.dataset.chordslabTempoRuntime='1';
    box.innerHTML=`<span>Tempo</span><strong>Tempo = ${tempo}</strong>`;
    card.appendChild(box);
}

function centerSlot(slot,smooth=true){
    if(!playbackActive||!slot)return;
    const sr=strip.getBoundingClientRect();
    const cr=slot.getBoundingClientRect();
    const delta=(cr.left+cr.width/2)-(sr.left+sr.width/2);
    if(Math.abs(delta)>2){
        strip.scrollBy({left:delta,behavior:smooth?'smooth':'auto'});
    }
}

root.addEventListener('ezscore:chord-current',event=>{
    if(!playbackActive)return;
    const seq=event.detail?.beatSeq;
    if(seq===undefined||seq===null)return;
    centerSlot(strip.querySelector(`.chord-slot[data-beat-seq="${seq}"]`),true);
});

async function requestWakeLock(){
    if(!playbackActive||!keepAwake?.checked||!('wakeLock' in navigator)||document.visibilityState!=='visible')return;
    try{
        if(!wakeLock)wakeLock=await navigator.wakeLock.request('screen');
    }catch(_){
        wakeLock=null;
    }
}

async function releaseWakeLock(){
    const current=wakeLock;
    wakeLock=null;
    if(current){
        try{await current.release()}catch(_){}
    }
}

if(keepAwake){
    const saved=localStorage.getItem(wakeKey);
    keepAwake.checked=saved===null?true:saved==='1';
    keepAwake.addEventListener('change',()=>{
        localStorage.setItem(wakeKey,keepAwake.checked?'1':'0');
        if(keepAwake.checked)requestWakeLock();
        else releaseWakeLock();
    });
}

mixer?.querySelector('[data-mixer-play]')?.addEventListener('click',()=>{
    playbackActive=true;
    requestWakeLock();
});

mixer?.querySelector('[data-mixer-pause]')?.addEventListener('click',()=>{
    playbackActive=false;
    releaseWakeLock();
});

mixer?.querySelector('[data-mixer-stop]')?.addEventListener('click',()=>{
    playbackActive=false;
    releaseWakeLock();
});

document.addEventListener('visibilitychange',()=>{
    if(document.visibilityState==='visible')requestWakeLock();
    else releaseWakeLock();
});

window.addEventListener('pagehide',releaseWakeLock);
window.addEventListener('beforeunload',releaseWakeLock);

installR345Styles();
installTempo();

})();
