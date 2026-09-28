(() => {
'use strict';

const root = document.querySelector('[data-lyricslab]');
if (!root) return;

const parse = value => {
    try { return JSON.parse(value || '[]'); }
    catch (_) { return []; }
};

const beats = parse(root.dataset.beats).sort((a,b) => a.start_ms - b.start_ms);
const chords = parse(root.dataset.chords).sort((a,b) => a.start_ms - b.start_ms);
const lyrics = parse(root.dataset.lyrics).sort((a,b) => a.start_ms - b.start_ms);
const measuresEl = root.querySelector('[data-lyrics-measures]');
const capo = Number(root.dataset.capo || 0);

const NOTE_TO_PC = {C:0,'C#':1,Db:1,D:2,'D#':3,Eb:3,E:4,F:5,'F#':6,Gb:6,G:7,'G#':8,Ab:8,A:9,'A#':10,Bb:10,B:11};
const SHARP = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'];

function displayChord(chord) {
    if (!chord || chord === '.') return chord || '.';
    const match = /^([A-G](?:#|b)?)(.*)$/.exec(chord);
    if (!match) return chord;
    const pc = NOTE_TO_PC[match[1]];
    if (pc === undefined) return chord;
    return SHARP[(pc - capo + 120) % 12] + match[2];
}

function activeChord(ms) {
    let current = null;
    for (const event of chords) {
        if (event.start_ms <= ms) current = event;
        else break;
    }
    return current;
}

function nextBeatStart(index) {
    if (index + 1 < beats.length) return beats[index + 1].start_ms;
    const previous = index > 0 ? beats[index - 1].start_ms : 0;
    return beats[index].start_ms + Math.max(250, beats[index].start_ms - previous);
}

function build() {
    const measures = new Map();

    beats.forEach((beat, index) => {
        const measureIndex = Number.isInteger(beat.measure_index) ? beat.measure_index : 0;
        if (!measures.has(measureIndex)) measures.set(measureIndex, []);

        const end = nextBeatStart(index);
        const exact = chords.find(event => event.start_ms >= beat.start_ms && event.start_ms < end);
        const active = exact || activeChord(beat.start_ms);

        let chordText = '-';
        if (exact) {
            chordText = displayChord(exact.effective || exact.original || '.');
        } else if ((active?.effective || active?.original || '') === '.') {
            chordText = '.';
        } else if ((beat.beat_index ?? 0) === 0) {
            chordText = displayChord(active?.effective || active?.original || '.');
        }

        const words = lyrics.filter(word => word.start_ms >= beat.start_ms && word.start_ms < end);
        measures.get(measureIndex).push({beat, index, chordText, words});
    });

    measuresEl.innerHTML = '';

    for (const [measureIndex, slots] of measures) {
        const measure = document.createElement('div');
        measure.className = 'chord-measure';
        measure.dataset.measureIndex = String(measureIndex);

        const number = document.createElement('small');
        number.className = 'chord-measure-number';
        number.textContent = String(Number(measureIndex) + 1);
        measure.appendChild(number);

        const notation = document.createElement('div');
        notation.className = 'chord-measure-notation';

        for (const slot of slots) {
            const cell = document.createElement('div');
            cell.className = 'chord-slot lyricslab-beat';
            cell.dataset.beatSeq = String(slot.index);

            const chord = document.createElement('div');
            chord.className = 'lyricslab-chord';
            chord.textContent = slot.chordText;
            cell.appendChild(chord);

            const words = document.createElement('div');
            words.className = 'lyricslab-words';

            slot.words.forEach(word => {
                const button = document.createElement('button');
                button.type = 'button';
                button.className = 'lyricslab-word';
                button.textContent = word.effective || word.original || '';
                button.dataset.eventId = String(word.id);
                button.dataset.startMs = String(word.start_ms);
                button.dataset.endMs = String(word.end_ms || word.start_ms + 250);
                words.appendChild(button);
            });

            cell.appendChild(words);
            notation.appendChild(cell);
        }

        measure.appendChild(notation);
        measuresEl.appendChild(measure);
    }
}

async function editWord(button) {
    const id = button.dataset.eventId;
    if (!id) return;

    const input = document.createElement('input');
    input.className = 'lyricslab-word-input';
    input.value = button.textContent || '';
    button.replaceWith(input);
    input.focus();
    input.select();

    const restore = () => build();

    const save = async () => {
        const text = input.value.trim();
        if (!text) { restore(); return; }

        const url = root.dataset.editUrlTemplate.replace('__EVENT__', id);
        const response = await fetch(url, {
            method: 'POST',
            credentials: 'same-origin',
            headers: {'Content-Type':'application/json','Accept':'application/json'},
            body: JSON.stringify({_token: root.dataset.editToken, text}),
        });

        if (!response.ok) {
            input.classList.add('is-error');
            return;
        }

        const data = await response.json();
        const event = lyrics.find(row => String(row.id) === String(id));
        if (event) {
            event.override = data.override;
            event.effective = data.effective;
        }
        build();
    };

    input.addEventListener('keydown', event => {
        if (event.key === 'Enter') { event.preventDefault(); save(); }
        if (event.key === 'Escape') { event.preventDefault(); restore(); }
    });
    input.addEventListener('blur', save, {once:true});
}

measuresEl.addEventListener('click', event => {
    const button = event.target.closest('.lyricslab-word[data-event-id]');
    if (button) editWord(button);
});

document.querySelector('[data-stem-mixer]')?.addEventListener('ezscore:audio-timeupdate', event => {
    const ms = Number(event.detail?.time || 0) * 1000;

    let currentBeat = -1;
    for (let i = 0; i < beats.length; i++) {
        if (beats[i].start_ms <= ms) currentBeat = i;
        else break;
    }

    measuresEl.querySelectorAll('.is-current').forEach(node => node.classList.remove('is-current'));

    if (currentBeat >= 0) {
        const cell = measuresEl.querySelector(`.chord-slot[data-beat-seq="${currentBeat}"]`);
        cell?.classList.add('is-current');
        cell?.closest('.chord-measure')?.classList.add('is-current');
    }

    measuresEl.querySelectorAll('.lyricslab-word').forEach(word => {
        const start = Number(word.dataset.startMs || 0);
        const end = Number(word.dataset.endMs || start + 250);
        word.classList.toggle('is-current', ms >= start && ms < Math.max(end, start + 120));
    });

    measuresEl.querySelector('.lyricslab-word.is-current')
        ?.scrollIntoView({behavior:'smooth', inline:'center', block:'nearest'});
});

build();

const source = document.querySelector('[data-lyrics-source]');
const saveState = document.querySelector('[data-lyrics-save-state]');
let saveTimer = null;

source?.addEventListener('input', () => {
    if (saveState) saveState.textContent = 'Modifié…';
    clearTimeout(saveTimer);
    saveTimer = setTimeout(async () => {
        try {
            const response = await fetch(source.dataset.saveUrl, {
                method: 'POST',
                credentials: 'same-origin',
                headers: {'Content-Type':'application/json','Accept':'application/json'},
                body: JSON.stringify({_token: source.dataset.saveToken, text: source.value}),
            });
            if (!response.ok) throw new Error();
            if (saveState) saveState.textContent = 'Enregistré';
        } catch (_) {
            if (saveState) saveState.textContent = 'Échec enregistrement';
        }
    }, 500);
});

const progressPanel = document.querySelector('[data-lyrics-progress]');
const statusUrl = progressPanel?.dataset.statusUrl || '';
const progressBar = progressPanel?.querySelector('progress');
const progressText = progressPanel?.querySelector('[data-lyrics-progress-text]');
const progressPercent = progressPanel?.querySelector('[data-lyrics-progress-percent]');

async function poll() {
    if (!statusUrl) return;

    try {
        const response = await fetch(statusUrl, {
            headers: {Accept:'application/json'},
            cache: 'no-store',
            credentials: 'same-origin',
        });

        if (response.ok) {
            const data = await response.json();
            const status = String(data.status || '');

            if (status === 'queued' || status === 'running') {
                progressPanel.hidden = false;
                progressBar.value = Number(data.progress || 0);
                progressPercent.textContent = `${Number(data.progress || 0)}%`;
                progressText.textContent = status === 'queued'
                    ? 'Analyse en attente du Worker…'
                    : (data.mode === 'extract' ? 'Extraction des paroles en cours…' : 'Analyse des paroles en cours…');
            } else if (status === 'failed') {
                progressPanel.hidden = false;
                progressPercent.textContent = 'Erreur';
                progressText.textContent = data.error || 'Analyse en échec';
            } else if (status === 'completed') {
                const key = `ezscore.lyrics.job.reloaded.${data.job_id}`;
                if (data.job_id && sessionStorage.getItem(key) !== '1') {
                    sessionStorage.setItem(key, '1');
                    location.reload();
                    return;
                }
                progressPanel.hidden = true;
            } else {
                progressPanel.hidden = true;
            }
        }
    } catch (_) {}

    setTimeout(poll, 900);
}

poll();
})();
