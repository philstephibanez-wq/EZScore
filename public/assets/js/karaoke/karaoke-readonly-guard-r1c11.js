/* R1.C11 — LyricsLab visual renderer, score editing disabled in Karaoke. */
(() => {
'use strict';
const root = document.querySelector('[data-karaoke-readonly]');
if (!root) return;

root.addEventListener('click', (event) => {
  if (event.target.closest('.lyrics-ribbon-beat.editable')) {
    event.preventDefault();
    event.stopImmediatePropagation();
  }
}, true);

const strip = () => {
  root.querySelectorAll('.lyrics-ribbon-beat.editable').forEach((node) => {
    node.classList.remove('editable');
    node.removeAttribute('data-beat-id');
    node.removeAttribute('data-active-event-id');
  });
};
strip();

const observer = new MutationObserver(strip);
observer.observe(root, {subtree:true, childList:true});
window.addEventListener('pagehide', () => observer.disconnect(), {once:true});
})();
