const fs=require('fs'), path=require('path');
const rootPath=process.argv[2]||'H:\\EZScore_v1';
const src=fs.readFileSync(path.join(rootPath,'public','assets','js','lyricslab-r37.js'),'utf8');

if(!src.includes('const left=xBeat(i),next=')) throw new Error('left declaration missing');
if(src.includes(';left=xBeat(i),next=')) throw new Error('undeclared left assignment remains');

const match=src.match(/function buildChords\(\)\{[\s\S]*?\n?\}/);
if(!match) throw new Error('buildChords not found');

console.log('R38_13C_CHORD_RUNTIME_DECLARATION_OK');
