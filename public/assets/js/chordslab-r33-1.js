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
const key='ezscore.chordslab.keepAwake';

function installR343Styles(){
 if(document.getElementById('ezscore-r34-3-style'))return;
 const style=document.createElement('style');
 style.id='ezscore-r34-3-style';
 style.textContent=`
 /* R34.3 — readable rich chords + clean guitar toggle */
 .chord-slot.is-long,
 .chord-slot.is-very-long{
   font-size:inherit!important;
   letter-spacing:normal!important;
 }
 .chord-label-root{
   font-size:1em!important;
   font-weight:800!important;
   line-height:1!important;
   flex:0 0 auto;
 }
 .chord-label-suffix{
   font-size:.82em!important;
   line-height:1!important;
   flex:0 0 auto;
   margin-left:1px;
 }
 .chord-quality-maj{
   font-size:.68em!important;
   line-height:1!important;
   vertical-align:super!important;
   letter-spacing:0!important;
   margin:0 1px 0 0!important;
 }
 .chord-label-bass{
   font-size:.78em!important;
   line-height:1!important;
 }

 .chordslab-settings-grid .chordslab-diagram-toggle,
 .chordslab-settings-grid .chordslab-diagram-inline{
   grid-column:1 / -1!important;
   display:flex!important;
   width:max-content!important;
   max-width:100%!important;
   align-items:center!important;
   gap:8px!important;
   padding:2px 0!important;
   margin:0!important;
 }
 .chordslab-settings-grid .chordslab-diagram-toggle > span,
 .chordslab-settings-grid .chordslab-diagram-inline > span{
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
 .chordslab-settings-grid .chordslab-diagram-toggle input[type="checkbox"],
 .chordslab-settings-grid .chordslab-diagram-inline input[type="checkbox"]{
   flex:0 0 auto!important;
   margin:0!important;
 }
 .chordslab-settings-save-state{
   grid-column:1 / -1!important;
   min-width:0!important;
   white-space:nowrap!important;
   margin-top:-4px!important;
 }

 @media(max-width:640px){
   .chordslab-settings-grid .chordslab-diagram-toggle,
   .chordslab-settings-grid .chordslab-diagram-inline{
     width:100%!important;
   }
   .chordslab-settings-grid .chordslab-diagram-toggle > span,
   .chordslab-settings-grid .chordslab-diagram-inline > span{
     white-space:normal!important;
   }
 }
 `;
 document.head.appendChild(style);
}

installR343Styles();

function centerSlot(slot,smooth=true){
 if(!slot||!playbackActive)return;
 const sr=strip.getBoundingClientRect();
 const cr=slot.getBoundingClientRect();
 const delta=(cr.left+cr.width/2)-(sr.left+sr.width/2);
 if(Math.abs(delta)>2){
   strip.scrollBy({left:delta,behavior:smooth?'smooth':'auto'});
 }
}

function cancelAutoScroll(){
 const left=strip.scrollLeft;
 strip.scrollTo({left,behavior:'auto'});
}

root.addEventListener('ezscore:chord-current',e=>{
 if(!playbackActive)return;
 const seq=e.detail?.beatSeq;
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
 const w=wakeLock;
 wakeLock=null;
 if(w){
   try{await w.release()}catch(_){}
 }
}

if(keepAwake){
 const saved=localStorage.getItem(key);
 keepAwake.checked=saved===null?true:saved==='1';
 keepAwake.addEventListener('change',()=>{
   localStorage.setItem(key,keepAwake.checked?'1':'0');
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
 cancelAutoScroll();
 releaseWakeLock();
});

mixer?.querySelector('[data-mixer-stop]')?.addEventListener('click',()=>{
 playbackActive=false;
 cancelAutoScroll();
 releaseWakeLock();
});

document.addEventListener('visibilitychange',()=>{
 if(document.visibilityState==='visible')requestWakeLock();
 else releaseWakeLock();
});

window.addEventListener('pagehide',releaseWakeLock);
window.addEventListener('beforeunload',releaseWakeLock);

})();
