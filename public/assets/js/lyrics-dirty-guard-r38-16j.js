(() => {
'use strict';
const source=document.querySelector('[data-lyrics-source]');
const saveForm=document.querySelector('[data-lyrics-history-save]');
if(!source||!saveForm)return;
const state=document.querySelector('[data-lyrics-manual-state]');
let baseline=source.value,dirty=false,pending=null;
function refreshDirtyState(){dirty=source.value!==baseline;if(state){state.textContent=dirty?'Modifié — non sauvegardé':'Sauvegardé';state.classList.toggle('is-dirty',dirty)}}
function markSaved(){baseline=source.value;refreshDirtyState()}
function removeModal(){document.querySelector('[data-lyrics-dirty-modal]')?.remove()}
function stayOnPage(){pending=null;removeModal()}
function continueNavigation(){const target=pending;pending=null;removeModal();if(!target)return;if(target.kind==='link'){window.location.assign(target.href);return}if(target.kind==='form'){target.form.dataset.lyricsDirtyBypass='1';target.form.requestSubmit(target.submitter||undefined)}}
function showDirtyModal(target){if(document.querySelector('[data-lyrics-dirty-modal]'))return;pending=target;const b=document.createElement('div');b.className='ez-modal-backdrop';b.dataset.lyricsDirtyModal='';b.innerHTML=`<div class="ez-modal lyrics-dirty-modal" role="dialog" aria-modal="true" aria-labelledby="lyrics-dirty-title"><h3 id="lyrics-dirty-title">Paroles non sauvegardées</h3><p>Voulez-vous quitter la page sans sauvegarder vos modifications ?</p><div class="ez-modal-actions"><button type="button" data-dirty-stay>Rester sur la page</button><button type="button" class="danger" data-dirty-leave>Quitter sans sauvegarder</button></div></div>`;b.querySelector('[data-dirty-stay]')?.addEventListener('click',stayOnPage);b.querySelector('[data-dirty-leave]')?.addEventListener('click',continueNavigation);b.addEventListener('click',e=>{if(e.target===b)stayOnPage()});document.body.appendChild(b);b.querySelector('[data-dirty-stay]')?.focus()}
source.addEventListener('input',refreshDirtyState);
document.addEventListener('click',event=>{if(!dirty)return;const link=event.target.closest('a[href]');if(!link||link.target==='_blank'||link.hasAttribute('download'))return;const href=link.getAttribute('href')||'';if(!href||href.startsWith('#')||href.startsWith('javascript:'))return;const url=new URL(link.href,window.location.href);if(url.origin!==window.location.origin)return;event.preventDefault();event.stopPropagation();showDirtyModal({kind:'link',href:url.href})},true);
document.addEventListener('submit',event=>{if(!dirty)return;const form=event.target;if(!(form instanceof HTMLFormElement)||form===saveForm)return;if(form.dataset.lyricsDirtyBypass==='1'){delete form.dataset.lyricsDirtyBypass;return}event.preventDefault();event.stopPropagation();showDirtyModal({kind:'form',form,submitter:event.submitter instanceof HTMLElement?event.submitter:null})},true);
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&document.querySelector('[data-lyrics-dirty-modal]'))stayOnPage()});
document.addEventListener('ezscore:lyrics-history-saved',markSaved);
document.addEventListener('ezscore:lyrics-history-restored',markSaved);
// Intentionally no beforeunload: browsers force their own native dialog there.
refreshDirtyState();
})();