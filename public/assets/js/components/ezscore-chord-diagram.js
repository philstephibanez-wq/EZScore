(() => {
'use strict';

const SHAPES = {
    C:'x32010', Cm:'x35543', C7:'x32310', Cmaj7:'x32000', Cadd9:'x32030', Cm7:'x35343', Csus2:'x30033', Csus4:'x33011',
    D:'xx0232', Dm:'xx0231', D7:'xx0212', Dmaj7:'xx0222', Dm7:'xx0211', Dadd9:'xx0230', Dsus2:'xx0230', Dsus4:'xx0233',
    E:'022100', Em:'022000', E7:'020100', Emaj7:'021100', Em7:'022030', Esus4:'022200',
    F:'133211', Fm:'133111', F7:'131211', Fmaj7:'xx3210', Fadd9:'103211', Fm7:'131111', Fsus4:'133311',
    G:'320003', Gm:'355333', G7:'320001', Gmaj7:'320002', Gadd9:'320203', Gsus4:'330013', G6:'320000',
    A:'x02220', Am:'x02210', A7:'x02020', Amaj7:'x02120', Am7:'x02010', Aadd9:'x02420', Asus2:'x02200', Asus4:'x02230',
    B:'x24442', Bm:'x24432', B7:'x21202', Bmaj7:'x24342', Bm7:'x20202', Bsus4:'x24452'
};

const escapeHtml = (value) => String(value).replace(/[&<>"']/g, ch => ({
    '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#039;'
}[ch]));

function simpleChord(chord) {
    return String(chord || '').trim().replace(/\/.*$/, '');
}

function render(host, chord) {
    if (!(host instanceof Element)) return false;

    const value = String(chord || '').trim();
    if (!value || value === '.') {
        host.hidden = true;
        host.innerHTML = '';
        return false;
    }

    host.hidden = false;
    const shape = SHAPES[simpleChord(value)];

    if (!shape) {
        host.innerHTML = `<strong class="chord-diagram-title">${escapeHtml(value)}</strong><small>Diagramme non disponible</small>`;
        return true;
    }

    let marks = '';
    shape.split('').forEach((fret, i) => {
        const x = 18 + i * 18;
        if (fret === 'x') {
            marks += `<text x="${x}" y="12" text-anchor="middle" font-size="10">×</text>`;
        } else if (fret === '0') {
            marks += `<circle cx="${x}" cy="10" r="4" fill="none" stroke="currentColor"/>`;
        } else {
            marks += `<circle cx="${x}" cy="${27 + (Number(fret) - 1) * 18}" r="5" fill="currentColor"/>`;
        }
    });

    host.innerHTML =
        `<strong class="chord-diagram-title">${escapeHtml(value)}</strong>` +
        `<svg viewBox="0 0 120 105" role="img" aria-label="${escapeHtml(value)}">` +
        `<g stroke="currentColor" fill="none">` +
        `<path d="M18 18V90M36 18V90M54 18V90M72 18V90M90 18V90M108 18V90"/>` +
        `<path d="M18 18H108M18 36H108M18 54H108M18 72H108M18 90H108"/>` +
        `</g>${marks}</svg>`;

    return true;
}

window.EZScoreChordDiagram = Object.freeze({render});
})();
