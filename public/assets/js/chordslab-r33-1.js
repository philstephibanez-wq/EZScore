(() => {
'use strict';
const root=document.querySelector('[data-chordslab]');
const strip=root?.querySelector('[data-chordslab-measures]');
const keepAwake=document.querySelector('[data-chordslab-wakelock]');
const mixer=document.querySelector('[data-stem-mixer]');
if(!root||!strip)return;
let wakeLock=null;
let playbackActive=false;
const key='ezscore.chordslab.keepAwake';
function centerSlot(slot,smooth=true){
 if(!playbackActive||!slot)return;
 const sr=strip.getBoundingClientRect(),cr=slot.getBoundingClientRect();
 const delta=(cr.left+cr.width/2)-(sr.left+sr.width/2);
 if(Math.abs(delta)>2)strip.scrollBy({left:delta,behavior:smooth?'smooth':'auto'});
}
root.addEventListener('ezscore:chord-current',e=>{
 if(!playbackActive)return;
 const seq=e.detail?.beatSeq;
 if(seq===undefined||seq===null)return;
 centerSlot(strip.querySelector(`.chord-slot[data-beat-seq="${seq}"]`),true);
});
async function requestWakeLock(){
 if(!playbackActive||!keepAwake?.checked||!('wakeLock' in navigator)||document.visibilityState!=='visible')return;
 try{if(!wakeLock)wakeLock=await navigator.wakeLock.request('screen')}catch(_){wakeLock=null}
}
async function releaseWakeLock(){const w=wakeLock;wakeLock=null;if(w){try{await w.release()}catch(_){}}}
if(keepAwake){
 const saved=localStorage.getItem(key);
 keepAwake.checked=saved===null?true:saved==='1';
 keepAwake.addEventListener('change',()=>{
  localStorage.setItem(key,keepAwake.checked?'1':'0');
  if(keepAwake.checked)requestWakeLock();else releaseWakeLock();
 });
}
mixer?.querySelector('[data-mixer-play]')?.addEventListener('click',()=>{playbackActive=true;requestWakeLock()});
mixer?.querySelector('[data-mixer-pause]')?.addEventListener('click',()=>{playbackActive=false;releaseWakeLock()});
mixer?.querySelector('[data-mixer-stop]')?.addEventListener('click',()=>{playbackActive=false;releaseWakeLock()});
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')requestWakeLock();else releaseWakeLock()});
window.addEventListener('pagehide',releaseWakeLock);
window.addEventListener('beforeunload',releaseWakeLock);
})();
