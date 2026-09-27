(() => {
'use strict';
const modal=document.querySelector('[data-ez-confirm-modal]'); if(!modal)return;
const message=modal.querySelector('[data-ez-confirm-message]'),ok=modal.querySelector('[data-ez-confirm-ok]'),cancel=modal.querySelector('[data-ez-confirm-cancel]');
let pending=null,lastFocus=null;
const close=()=>{modal.hidden=true;pending=null;if(lastFocus?.focus)lastFocus.focus();};
const open=(text,action,focusEl)=>{pending=action;lastFocus=focusEl||document.activeElement;message.textContent=text||'Confirmer cette action ?';modal.hidden=false;setTimeout(()=>cancel.focus(),0);};
document.addEventListener('click',e=>{const trigger=e.target.closest('[data-ez-confirm]');if(!trigger)return;const text=trigger.getAttribute('data-ez-confirm')||'Confirmer cette action ?';const form=trigger.form;if(form&&trigger.type==='submit'){if(trigger.dataset.ezConfirmed==='1'){delete trigger.dataset.ezConfirmed;return}e.preventDefault();open(text,()=>{trigger.dataset.ezConfirmed='1';form.requestSubmit(trigger)},trigger)}else if(trigger.tagName==='A'){e.preventDefault();open(text,()=>location.href=trigger.href,trigger)}});
document.addEventListener('submit',e=>{const form=e.target.closest('form[data-ez-confirm]');if(!form||form.dataset.ezConfirmed==='1')return;e.preventDefault();open(form.getAttribute('data-ez-confirm'),()=>{form.dataset.ezConfirmed='1';form.requestSubmit()},form)});
ok.addEventListener('click',()=>{const fn=pending;modal.hidden=true;pending=null;if(fn)fn()});cancel.addEventListener('click',close);modal.addEventListener('click',e=>{if(e.target===modal)close()});document.addEventListener('keydown',e=>{if(!modal.hidden&&e.key==='Escape')close()});
})();