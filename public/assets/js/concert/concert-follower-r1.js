(() => {
    'use strict';
    const root = document.querySelector('[data-concert-follower]');
    if (!root) return;
    const $ = (selector) => root.querySelector(selector);
    const sessionId = root.dataset.sessionId || '';
    const inviteToken = root.dataset.inviteToken || '';

    let clientId = '';
    let clientKey = '';
    let latest = null;
    let receivedAt = performance.now();
    let failures = 0;

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

    const clientHeaders = () => ({
        'X-Concert-Client-Id': clientId,
        'X-Concert-Client-Key': clientKey,
    });

    const apply = (session) => {
        latest = session;
        receivedAt = performance.now();
        failures = 0;
        const state = session?.state || {};
        $('[data-follower-song]').textContent = state.song_title || (state.song_id ? `Morceau #${state.song_id}` : 'Aucun morceau');
        $('[data-follower-master]').textContent = session.master_name || '—';
        $('[data-follower-tempo]').textContent = `${Number(state.tempo || 1).toFixed(2)}×`;
        $('[data-follower-revision]').textContent = String(session.revision ?? '—');
        $('[data-follower-participants]').textContent = String((session.participants || []).length);
        $('[data-follower-play]').textContent = state.playing ? 'LECTURE' : 'PAUSE';
    };

    const join = async () => {
        const platform = navigator.userAgentData?.platform || navigator.platform || 'browser';
        const payload = await request(`/api/concert/session/${encodeURIComponent(sessionId)}/join`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({invite_token: inviteToken, name: `Follower ${platform}`, device_type: 'browser'}),
        });
        clientId = payload.client_id;
        clientKey = payload.client_key;
        apply(payload.session);
        $('[data-follower-connection]').textContent = 'Connecté';
    };

    const poll = async () => {
        if (!clientId || !clientKey) return;
        try {
            const payload = await request(`/api/concert/session/${encodeURIComponent(sessionId)}/client-state`, {headers: clientHeaders()});
            apply(payload.session);
            $('[data-follower-connection]').textContent = 'Connecté';
        } catch (error) {
            failures += 1;
            if (failures >= 3) $('[data-follower-connection]').textContent = `Connexion perdue (${error.message})`;
        }
    };

    const heartbeat = async () => {
        if (!clientId || !clientKey) return;
        try {
            await request(`/api/concert/session/${encodeURIComponent(sessionId)}/heartbeat`, {method: 'POST', headers: clientHeaders()});
        } catch (_) {}
    };

    const renderClock = () => {
        const state = latest?.state || {};
        let position = Number(state.position_ms || 0);
        if (state.playing) {
            const tempo = Math.max(.25, Math.min(2, Number(state.tempo || 1)));
            position += (performance.now() - receivedAt) * tempo;
        }
        const totalTenths = Math.max(0, Math.floor(position / 100));
        const minutes = Math.floor(totalTenths / 600);
        const seconds = Math.floor((totalTenths % 600) / 10);
        const tenths = totalTenths % 10;
        $('[data-follower-position]').textContent = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}.${tenths}`;
        requestAnimationFrame(renderClock);
    };

    join().then(() => {
        setInterval(poll, 500);
        setInterval(heartbeat, 5000);
    }).catch((error) => {
        $('[data-follower-connection]').textContent = `Connexion impossible (${error.message})`;
    });

    requestAnimationFrame(renderClock);
})();
