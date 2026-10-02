(() => {
    'use strict';
    const root = document.querySelector('[data-concert-master]');
    if (!root) return;
    const $ = (selector) => root.querySelector(selector);
    const csrf = root.dataset.csrf || '';
    const createButton = $('[data-concert-create]');
    const controls = $('[data-concert-controls]');
    const errorBox = $('[data-concert-error]');
    const positionInput = $('[data-concert-position]');
    const tempoInput = $('[data-concert-tempo]');

    let sessionId = null;
    let masterKey = null;
    let playing = false;
    let basePositionMs = 0;
    let baseClock = performance.now();

    const currentPositionMs = () => {
        if (!playing) return basePositionMs;
        const tempo = Math.max(.25, Math.min(2, Number(tempoInput.value || 1)));
        return basePositionMs + (performance.now() - baseClock) * tempo;
    };

    const setError = (message = '') => {
        errorBox.hidden = !message;
        errorBox.textContent = message;
    };

    const request = async (url, options = {}) => {
        const response = await fetch(url, {
            cache: 'no-store',
            ...options,
            headers: {Accept: 'application/json', ...(options.headers || {})},
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(payload.error || `HTTP_${response.status}`);
        return payload;
    };

    const renderSession = (session) => {
        if (!session) return;
        $('[data-concert-session]').textContent = session.id || '—';
        $('[data-concert-revision]').textContent = String(session.revision ?? '—');
        $('[data-concert-participants]').textContent = String((session.participants || []).length);
    };

    const publish = async () => {
        basePositionMs = currentPositionMs();
        baseClock = performance.now();
        const payload = await request(`/api/concert/session/${encodeURIComponent(sessionId)}/state`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': csrf,
                'X-Concert-Master-Key': masterKey,
            },
            body: JSON.stringify({
                song_id: $('[data-concert-song-id]').value || null,
                song_title: $('[data-concert-song-title]').value || '',
                playing,
                position_ms: Math.round(basePositionMs),
                tempo: Number(tempoInput.value || 1),
            }),
        });
        renderSession(payload.session);
        $('[data-concert-state]').textContent = playing ? 'Lecture' : 'Pause';
    };

    const refreshMasterState = async () => {
        if (!sessionId || !masterKey) return;
        try {
            const payload = await request(`/api/concert/session/${encodeURIComponent(sessionId)}/master-state`, {
                headers: {'X-Concert-Master-Key': masterKey},
            });
            renderSession(payload.session);
        } catch (error) {
            setError(`État session : ${error.message}`);
        }
    };

    createButton.addEventListener('click', async () => {
        createButton.disabled = true;
        setError('');
        try {
            const payload = await request('/api/concert/session', {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf},
                body: '{}',
            });
            sessionId = payload.session.id;
            masterKey = payload.master_key;
            controls.hidden = false;
            createButton.textContent = 'Session créée';
            $('[data-concert-follow-url]').value = payload.follow_url;
            renderSession(payload.session);
            setInterval(refreshMasterState, 1500);
        } catch (error) {
            createButton.disabled = false;
            setError(`Création impossible : ${error.message}`);
        }
    });

    $('[data-concert-play]').addEventListener('click', async () => {
        basePositionMs = currentPositionMs();
        baseClock = performance.now();
        playing = !playing;
        $('[data-concert-play]').textContent = playing ? 'Pause' : 'Play';
        try {
            await publish();
        } catch (error) {
            playing = !playing;
            $('[data-concert-play]').textContent = playing ? 'Pause' : 'Play';
            setError(`Publication impossible : ${error.message}`);
        }
    });

    $('[data-concert-send]').addEventListener('click', async () => {
        basePositionMs = Math.max(0, Number(positionInput.value || 0) * 1000);
        baseClock = performance.now();
        try {
            setError('');
            await publish();
        } catch (error) {
            setError(`Publication impossible : ${error.message}`);
        }
    });

    $('[data-concert-copy]').addEventListener('click', async () => {
        const input = $('[data-concert-follow-url]');
        if (!input.value) return;
        try {
            await navigator.clipboard.writeText(input.value);
            $('[data-concert-copy]').textContent = 'Copié';
            setTimeout(() => {$('[data-concert-copy]').textContent = 'Copier';}, 1200);
        } catch (_) {
            input.select();
        }
    });

    setInterval(() => {
        if (!controls.hidden) positionInput.value = (currentPositionMs() / 1000).toFixed(1);
    }, 100);
})();
