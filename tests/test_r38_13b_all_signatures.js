const fs=require('fs');
const path=require('path');
const rootPath=process.argv[2]||'H:\\EZScore_v1';
const src=fs.readFileSync(path.join(rootPath,'public','assets','js','lyricslab-r37.js'),'utf8');
const m=src.match(/function buildCanonicalProjection\(inputBeats\)\{[\s\S]*?\n\}(?=\nconst canonicalProjection=buildCanonicalProjection\(sourceBeats\);)/);
if(!m) throw new Error('projection function not found');

function run(signature){
  const root={dataset:{timeSignature:signature}};
  const source=[];
  // Deliberately stale source grouping: 4 source beats per source measure.
  // The display projection must ignore these measure boundaries.
  for(let i=0;i<24;i++){
    source.push({id:i,start_ms:i*500,measure_index:Math.floor(i/4),beat_index:i%4,effective:i%5===0?'C':'-'});
  }
  const fn=new Function('root',`${m[0]}; return buildCanonicalProjection;`)(root);
  const p=fn(source);
  const n=Number(signature.split('/')[0]);

  if(p.beats.length!==source.length) throw new Error(`${signature}: beat count changed`);
  if(p.beats.some(b=>b.displaySynthetic)) throw new Error(`${signature}: synthetic beat found`);
  for(let i=0;i<p.beats.length;i++){
    const b=p.beats[i];
    if(b.display_seq!==i) throw new Error(`${signature}: bad display_seq @${i}`);
    if(b.display_measure_index!==Math.floor(i/n)) throw new Error(`${signature}: bad measure @${i}`);
    if(b.display_beat_index!==i%n) throw new Error(`${signature}: bad slot @${i}`);
    if(i && !(Number(b.display_start_ms)>Number(p.beats[i-1].display_start_ms))){
      throw new Error(`${signature}: non-monotonic display time @${i}`);
    }
  }
  // Specifically prove every display measure boundary is one and only one slot later.
  for(let i=n;i<p.beats.length;i+=n){
    const dt=p.beats[i].display_start_ms-p.beats[i-1].display_start_ms;
    if(dt!==500) throw new Error(`${signature}: boundary discontinuity @${i}: ${dt}`);
  }
}

['2/4','3/4','4/4','6/8'].forEach(run);
console.log('R38_13B_ALL_SIGNATURES_CONTINUOUS_OK');
