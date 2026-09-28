(() => {
'use strict';
for(const card of document.querySelectorAll('[data-lab-song-card]')){
 const out=card.querySelector('[data-lab-tempo]'); if(!out)continue;
 let beats=[]; try{beats=JSON.parse(card.dataset.labBeats||'[]')}catch(_){beats=[]}
 if(!Array.isArray(beats)||beats.length<3){out.textContent='Tempo = —';continue}
 const d=[]; for(let i=1;i<beats.length;i++){const x=Number(beats[i].start_ms)-Number(beats[i-1].start_ms);if(Number.isFinite(x)&&x>=180&&x<=2000)d.push(x)}
 if(!d.length){out.textContent='Tempo = —';continue} d.sort((a,b)=>a-b); const m=Math.floor(d.length/2); const med=d.length%2?d[m]:(d[m-1]+d[m])/2; const bpm=Math.round(60000/med); out.textContent=Number.isFinite(bpm)&&bpm>0?`Tempo = ${bpm}`:'Tempo = —';
}
})();
