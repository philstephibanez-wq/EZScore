/* EZScore R39.2 — collision-safe syllable rendering.
 * Contract: visual collision repair only. Never modifies X/time geometry.
 */
(() => {
'use strict';

function applyCollisionLayout(root){
  const lane=root.querySelector('.lyrics-ribbon-syllables');
  if(!lane)return;

  const nodes=[...lane.querySelectorAll('.lyrics-ribbon-syllable')];
  if(!nodes.length)return;

  nodes.forEach(node=>{
    node.style.removeProperty('--ez-font-scale');
    node.style.removeProperty('--ez-y-offset');
    node.classList.remove('collision-tight','collision-row-1','collision-row-2');
  });

  const measured=nodes.map(node=>{
    const r=node.getBoundingClientRect();
    return {node,left:r.left,right:r.right,width:r.width,center:(r.left+r.right)/2};
  }).sort((a,b)=>a.center-b.center);

  const minGap=3;
  let prev=null;

  for(const item of measured){
    if(!prev){prev=item;continue}

    const overlap=(prev.right+minGap)-item.left;
    if(overlap<=0){prev=item;continue}

    const combined=Math.max(1,(prev.width+item.width));
    const ratio=Math.min(1,overlap/combined);

    // First choice: compact typography slightly.
    // No horizontal translation is ever applied.
    const scale=Math.max(0.78,1-ratio*1.9);
    item.node.style.setProperty('--ez-font-scale',String(scale));
    item.node.classList.add('collision-tight');

    // Re-measure after compacting.
    const nr=item.node.getBoundingClientRect();
    const stillOverlap=(prev.right+minGap)-nr.left;

    if(stillOverlap>0){
      // Second choice: alternate vertical micro-rows.
      const prevRow=prev.node.classList.contains('collision-row-1')?1:
                    prev.node.classList.contains('collision-row-2')?2:0;
      const row=prevRow===1?2:1;
      item.node.classList.add(row===1?'collision-row-1':'collision-row-2');
      item.node.style.setProperty('--ez-y-offset',row===1?'-11px':'11px');
    }

    const finalRect=item.node.getBoundingClientRect();
    prev={node:item.node,left:finalRect.left,right:finalRect.right,width:finalRect.width,center:(finalRect.left+finalRect.right)/2};
  }

  root.dataset.collisionLayout='r39.2';
}

function install(){
  const root=document.querySelector('[data-lyricslab]');
  if(!root)return;

  const observer=new MutationObserver(()=>requestAnimationFrame(()=>applyCollisionLayout(root)));
  const lane=root.querySelector('.lyrics-ribbon-syllables');
  if(lane)observer.observe(lane,{childList:true,subtree:true});

  window.addEventListener('resize',()=>requestAnimationFrame(()=>applyCollisionLayout(root)));
  document.fonts?.ready?.then(()=>requestAnimationFrame(()=>applyCollisionLayout(root)));
  setTimeout(()=>applyCollisionLayout(root),100);
  setTimeout(()=>applyCollisionLayout(root),350);
}

if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',install,{once:true});
else install();
})();
