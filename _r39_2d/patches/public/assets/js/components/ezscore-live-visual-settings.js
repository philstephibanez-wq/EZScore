(() => {
'use strict';

const root = document.querySelector('[data-ez-live-settings]');
if (!root) return;

const form = root.querySelector('[data-chord-settings-form]');
const state = root.querySelector('[data-chord-settings-state]');
const capo = root.querySelector('[data-chordslab-capo]');
const signature = root.querySelector('[data-chordslab-timesig]');
const profile = root.querySelector('[data-chordslab-profile]');
const diagram = root.querySelector('[data-chordslab-diagram]');
const onChordsLab = Boolean(document.querySelector('[data-chordslab]'));
const onLyricsLab = Boolean(document.querySelector('[data-lyricslab]'));
const diagramKey = 'ezscore:visual:guitar-diagram';

function setState(text) {
    if (state) state.textContent = text;
}

function restoreDiagramState() {
    if (!diagram) return;
    try {
        const stored = localStorage.getItem(diagramKey);
        if (stored === '1' || stored === '0') diagram.checked = stored === '1';
    } catch (_) {}
}

function persistDiagramState() {
    if (!diagram) return;
    try {
        localStorage.setItem(diagramKey, diagram.checked ? '1' : '0');
    } catch (_) {}
}

async function saveAndReloadForLyrics() {
    if (!form || !onLyricsLab) return;
    setState('Enregistrement…');
    try {
        const response = await fetch(form.action, {
            method: 'POST',
            body: new FormData(form),
            credentials: 'same-origin',
            headers: {'Accept': 'application/json'}
        });
        if (!response.ok) throw new Error(`settings_http_${response.status}`);
        setState('Enregistré');
        location.reload();
    } catch (error) {
        console.error('EZScore shared visual settings save failed', error);
        setState('Échec enregistrement');
    }
}

restoreDiagramState();

diagram?.addEventListener('change', () => {
    persistDiagramState();
    /* ChordsLab already owns diagram show/hide. Lyrics will consume this state
       when the shared diagram component is reintroduced. */
});

if (onLyricsLab) {
    [capo, signature, profile].forEach(control => {
        control?.addEventListener('change', saveAndReloadForLyrics);
    });
}

/* On ChordsLab, chordslab.js remains the sole owner of immediate select behavior. */
if (onChordsLab) {
    setState('Enregistré automatiquement');
}
})();
