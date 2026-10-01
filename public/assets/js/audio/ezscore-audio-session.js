(() => {
    'use strict';
    const NativeEngine = window.EZScoreAudioEngine;
    if (typeof NativeEngine !== 'function' || window.EZScoreAudioSession) return;
    let active = null;

    const currentSongId = () => {
        const root = document.querySelector('[data-stem-mixer][data-song-id]');
        if (root?.dataset.songId) return String(root.dataset.songId);
        const match = location.pathname.match(/\/song\/(\d+)(?:\/|$)/);
        return match ? match[1] : '';
    };

    const disposeActive = () => {
        if (!active) return;
        try { active.engine.dispose(); } catch (_) {}
        active = null;
    };

    const prepareEngine = (engine) => {
        if (engine.__ezscoreSessionPrepared) return engine;
        engine.__ezscoreSessionPrepared = true;
        const nativeAddTrack = engine.addTrack.bind(engine);
        engine.addTrack = (config) => {
            const existing = engine.tracks?.get(config?.key);
            if (existing && existing.url === config.url) {
                engine.setTrackEnabled(config.key, Boolean(config.enabled));
                engine.setTrackVolume(config.key, Number(config.volume));
                return existing;
            }
            return nativeAddTrack(config);
        };
        return engine;
    };

    const acquire = (args) => {
        const songId = currentSongId();
        if (active && active.songId !== songId) disposeActive();
        if (!active || active.engine.disposed) {
            active = {songId, engine: prepareEngine(Reflect.construct(NativeEngine, args))};
        }
        return active.engine;
    };

    window.EZScoreAudioEngine = new Proxy(NativeEngine, {
        construct(_target, args) { return acquire(args); }
    });

    window.EZScoreAudioSession = Object.freeze({
        get engine() { return active?.engine || null; },
        currentSongId,
        isAlive(songId = null) {
            if (!active || active.engine.disposed) return false;
            return songId === null || String(songId) === active.songId;
        },
        invalidate(songId = null) {
            if (!active) return;
            if (songId !== null && String(songId) !== active.songId) return;
            disposeActive();
        }
    });

    window.addEventListener('pagehide', disposeActive, {once: true});
})();
