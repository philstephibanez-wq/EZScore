(() => {
'use strict';

const statusBox=document.querySelector('[data-chord-analysis-progress]');
const statusUrl=statusBox?.dataset.statusUrl||'';
const statusText=statusBox?.querySelector('[data-chord-analysis-text]');
const statusPercent=statusBox?.querySelector('[data-chord-analysis-percent]');
const progressEl=statusBox?.querySelector('progress');
const quickVolume=document.querySelector('[data-chordslab-quick-volume]');
const quickVolumeOut=document.querySelector('[data-chordslab-quick-volume-output]');
const masterVolume=document.querySelector('[data-master-volume]');
const resetForm=document.querySelector('[data-chord-reset-form]');
const resetDialog=document.querySelector('[data-chord-reset-dialog]');
const resetCancel=resetDialog?.querySelector('[data-chord-reset-cancel]');
const resetConfirm=resetDialog?.querySelector('[data-chord-reset-confirm]');
const levelSelect=document.querySelector('[name="chord_analysis_level"]');
const levelHelp=document.querySelector('[data-analysis-level-help]');

function setProgress(data){
 if(!statusBox)return;
 const status=String(data?.status||'');
 const pct=Number(data?.progress||0);
 if(status==='queued'||status==='running'){
  statusBox.hidden=false;
  if(progressEl)progressEl.value=pct;
  if(statusPercent)statusPercent.textContent=`${pct}%`;
  if(statusText)statusText.textContent=status==='queued'?'Analyse en attente du worker…':'Analyse harmonique en cours…';
  return;
 }
 if(status==='failed'){
  statusBox.hidden=false;
  if(progressEl)progressEl.value=pct;
  if(statusPercent)statusPercent.textContent='Erreur';
  if(statusText)statusText.textContent=data?.error||'Analyse harmonique en échec.';
  return;
 }
 if(status==='completed'){
  const id=String(data?.job_id||'');
  const key=`ezscore.chord.job.reloaded.${id}`;
  if(id && sessionStorage.getItem(key)!=='1'){
   sessionStorage.setItem(key,'1');
   window.location.reload();
  }
  statusBox.hidden=true;
  return;
 }
 statusBox.hidden=true;
}
async function pollStatus(){
 if(!statusUrl)return;
 try{
  const response=await fetch(statusUrl,{headers:{Accept:'application/json'},credentials:'same-origin',cache:'no-store'});
  if(response.ok)setProgress(await response.json());
 }catch(_){}
 window.setTimeout(pollStatus,900);
}
pollStatus();

if(resetForm&&resetDialog){
 resetForm.addEventListener('submit',e=>{
  if(resetForm.dataset.confirmed==='1')return;
  e.preventDefault();
  if(typeof resetDialog.showModal==='function')resetDialog.showModal();
  else{resetForm.dataset.confirmed='1';resetForm.submit();}
 });
 resetCancel?.addEventListener('click',()=>resetDialog.close());
 resetConfirm?.addEventListener('click',()=>{
  resetForm.dataset.confirmed='1';
  resetDialog.close();
  resetForm.submit();
 });
 resetDialog.addEventListener('click',e=>{if(e.target===resetDialog)resetDialog.close()});
}

function updateQuickOutput(){
 if(quickVolumeOut&&quickVolume)quickVolumeOut.textContent=`${Math.round(Number(quickVolume.value)*100)}%`;
}
function syncFromMaster(){
 if(!quickVolume||!masterVolume)return;
 quickVolume.value=masterVolume.value;
 updateQuickOutput();
}
quickVolume?.addEventListener('input',()=>{
 updateQuickOutput();
 if(masterVolume){
  masterVolume.value=quickVolume.value;
  masterVolume.dispatchEvent(new Event('input',{bubbles:true}));
 }
});
masterVolume?.addEventListener('input',syncFromMaster);
setTimeout(syncFromMaster,50);
setTimeout(syncFromMaster,600);

const levelDescriptions={
 beginner:'Accords majeurs/mineurs uniquement, changements fortement lissés.',
 intermediate:'Triades prioritaires ; 7, m7, sus et dim seulement si la preuve harmonique est nette.',
 expert:'Détection plus détaillée, enrichissements autorisés et changements moins lissés.'
};
function updateLevelHelp(){if(levelHelp&&levelSelect)levelHelp.textContent=levelDescriptions[levelSelect.value]||'';}
levelSelect?.addEventListener('change',updateLevelHelp);
updateLevelHelp();
})();
