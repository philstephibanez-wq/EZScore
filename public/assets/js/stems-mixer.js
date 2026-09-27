(() => {
    'use strict';

    const root = document.querySelector('[data-stem-mixer]');
    if (!root || typeof window.EZScoreAudioEngine !== 'function') return;

    const q = (selector) => root.querySelector(selector);
    const engine = new window.EZScoreAudioEngine({
        masterTrackKey: 'original',
        syncThresholdSeconds: 0.060,
        syncIntervalMs: 250,
    });

    const tracks = new Map();
    const persisted = (() => {
        try { return JSON.parse(root.dataset.mixSettings || '{}') || {}; }
        catch (_) { return {}; }
    })();
    const masterEq = persisted.master_eq && typeof persisted.master_eq === 'object'
        ? persisted.master_eq
        : {low: 0, mid: 0, high: 0};

    const els = {
        state: q('[data-mixer-state]'),
        save: q('[data-mix-save-state]'),
        seek: q('[data-mixer-seek]'),
        time: q('[data-mixer-time]'),
        play: q('[data-mixer-play]'),
        pause: q('[data-mixer-pause]'),
        stop: q('[data-mixer-stop]'),
        rate: q('[data-mixer-rate]'),
        volume: q('[data-master-volume]'),
        volumeOut: q('[data-master-volume-output]'),
        low: q('[data-master-low]'),
        lowOut: q('[data-master-low-output]'),
        mid: q('[data-master-mid]'),
        midOut: q('[data-master-mid-output]'),
        high: q('[data-master-high]'),
        highOut: q('[data-master-high-output]'),
        compression: q('[data-master-compression]'),
        compressionOut: q('[data-master-compression-output]'),
        reset: q('[data-master-fx-reset]'),
    };

    const i18n = {
        saved: root.dataset.i18nSaved || 'Saved',
        modified: root.dataset.i18nModified || 'Modified',
        saving: root.dataset.i18nSaving || 'Saving…',
        saveFailed: root.dataset.i18nSaveFailed || 'Save failed',
        ready: root.dataset.i18nReady || 'Ready',
        playing: root.dataset.i18nPlaying || 'Playing',
        paused: root.dataset.i18nPaused || 'Paused',
        finished: root.dataset.i18nFinished || 'Finished',
        audioError: root.dataset.i18nAudioErrorTemplate || 'Audio error: __ERROR__',
    };

    const fmt = (seconds) => {
        const safe = Math.max(0, Number(seconds) || 0);
        return `${Math.floor(safe / 60)}:${Math.floor(safe % 60).toString().padStart(2, '0')}`;
    };
    const dbText = (value) => {
        const n = Number(value) || 0;
        return `${n > 0 ? '+' : ''}${n.toFixed(n % 1 ? 1 : 0)} dB`;
    };

    let saveTimer = 0;
    let disposed = false;

    root.querySelectorAll('[data-mixer-track]').forEach((row) => {
        const key = row.dataset.trackKey;
        const enabled = row.querySelector('[data-track-enabled]');
        const volume = row.querySelector('[data-track-volume]');
        const output = row.querySelector('[data-track-volume-output]');
        const loader = row.querySelector('[data-track-loader]');
        const status = row.querySelector('[data-track-load-status]');
        const saved = persisted.tracks?.[key];

        if (saved && typeof saved === 'object') {
            if (typeof saved.enabled === 'boolean') enabled.checked = saved.enabled;
            if (Number.isFinite(Number(saved.volume))) volume.value = String(saved.volume);
        }

        tracks.set(key, {row, enabled, volume, output, loader, status});
        engine.addTrack({
            key,
            label: row.querySelector('strong')?.textContent?.trim() || key,
            url: row.dataset.trackUrl,
            enabled: enabled.checked,
            volume: Number(volume.value),
        });

        output.textContent = `${Math.round(Number(volume.value) * 100)}%`;
        enabled.addEventListener('change', () => {
            engine.setTrackEnabled(key, enabled.checked);
            scheduleSave();
        });
        volume.addEventListener('input', () => {
            output.textContent = `${Math.round(Number(volume.value) * 100)}%`;
            engine.setTrackVolume(key, Number(volume.value));
            scheduleSave();
        });
    });

    if (els.volume && Number.isFinite(Number(persisted.master_volume))) {
        els.volume.value = String(persisted.master_volume);
    }
    if (els.rate && Number.isFinite(Number(persisted.playback_rate))) {
        els.rate.value = String(persisted.playback_rate);
    }
    if (els.low) els.low.value = String(Number(masterEq.low) || 0);
    if (els.mid) els.mid.value = String(Number(masterEq.mid) || 0);
    if (els.high) els.high.value = String(Number(masterEq.high) || 0);
    if (els.compression) {
        els.compression.value = String(
            Number.isFinite(Number(persisted.master_compression))
                ? Number(persisted.master_compression)
                : 0
        );
    }

    const syncMasterOutputs = () => {
        if (els.volume && els.volumeOut) {
            els.volumeOut.textContent = `${Math.round(Number(els.volume.value) * 100)}%`;
        }
        if (els.lowOut) els.lowOut.textContent = dbText(els.low.value);
        if (els.midOut) els.midOut.textContent = dbText(els.mid.value);
        if (els.highOut) els.highOut.textContent = dbText(els.high.value);
        if (els.compressionOut) {
            els.compressionOut.textContent = `${Math.round(Number(els.compression.value))}%`;
        }
    };

    const applyMasterFx = () => {
        engine.setMasterEq({
            low: Number(els.low?.value || 0),
            mid: Number(els.mid?.value || 0),
            high: Number(els.high?.value || 0),
        });
        engine.setMasterCompression(Number(els.compression?.value || 0));
    };

    const serializeSettings = () => ({
        schema_version: 'ezscore.stem_mix.v2',
        master_volume: Number(els.volume?.value || 1),
        playback_rate: Number(els.rate?.value || 1),
        master_eq: {
            low: Number(els.low?.value || 0),
            mid: Number(els.mid?.value || 0),
            high: Number(els.high?.value || 0),
        },
        master_compression: Number(els.compression?.value || 0),
        tracks: Object.fromEntries(
            [...tracks.entries()].map(([key, track]) => [key, {
                enabled: track.enabled.checked,
                volume: Number(track.volume.value),
            }])
        ),
    });

    const saveSettings = async () => {
        if (disposed || !root.dataset.mixSaveUrl || !root.dataset.mixToken) return;
        if (els.save) els.save.textContent = i18n.saving;
        try {
            const response = await fetch(root.dataset.mixSaveUrl, {
                method: 'POST',
                headers: {'Accept': 'application/json', 'Content-Type': 'application/json'},
                credentials: 'same-origin',
                body: JSON.stringify({_token: root.dataset.mixToken, settings: serializeSettings()}),
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            if (els.save) els.save.textContent = i18n.saved;
        } catch (_) {
            if (els.save) els.save.textContent = i18n.saveFailed;
        }
    };

    function scheduleSave() {
        window.clearTimeout(saveTimer);
        if (els.save) els.save.textContent = i18n.modified;
        saveTimer = window.setTimeout(saveSettings, 450);
    }

    // R35.8: prepare Opus immediately, without autoplay.
    queueMicrotask(() => {
        if (typeof engine.warmUp === 'function') engine.warmUp({enabledFirst: true}).catch?.(() => {});
    });

    engine.setMasterVolume(Number(els.volume?.value || 1));
    engine.setPlaybackRate(Number(els.rate?.value || 1));
    applyMasterFx();
    syncMasterOutputs();

    els.volume?.addEventListener('input', () => {
        engine.setMasterVolume(Number(els.volume.value));
        syncMasterOutputs();
        scheduleSave();
    });
    [els.low, els.mid, els.high].forEach((input) => {
        input?.addEventListener('input', () => {
            applyMasterFx();
            syncMasterOutputs();
            scheduleSave();
        });
    });
    els.compression?.addEventListener('input', () => {
        applyMasterFx();
        syncMasterOutputs();
        scheduleSave();
    });
    els.reset?.addEventListener('click', () => {
        els.low.value = '0';
        els.mid.value = '0';
        els.high.value = '0';
        els.compression.value = '0';
        applyMasterFx();
        syncMasterOutputs();
        scheduleSave();
    });
    els.rate?.addEventListener('change', () => {
        engine.setPlaybackRate(Number(els.rate.value));
        scheduleSave();
    });

    els.play?.addEventListener('click', async () => {
        try {
            await engine.play();
        } catch (error) {
            if (els.state) {
                els.state.textContent = i18n.audioError.replace(
                    '__ERROR__',
                    error instanceof Error ? error.message : String(error)
                );
            }
        }
    });
    els.pause?.addEventListener('click', () => engine.pause());
    els.stop?.addEventListener('click', () => engine.stop());
    els.seek?.addEventListener('input', () => {
        const duration = engine.duration();
        if (duration) engine.seek((Number(els.seek.value) / 1000) * duration);
    });

    engine.addEventListener('statechange', (event) => {
        if (!els.state) return;
        const state = event.detail?.state;
        if (state === 'playing') els.state.textContent = i18n.playing;
        else if (state === 'paused') els.state.textContent = i18n.paused;
        else if (state === 'ready') els.state.textContent = i18n.ready;
        else if (state === 'loading') els.state.textContent = root.dataset.i18nLoading || 'Loading…';
    });
    engine.addEventListener('ended', () => {
        if (els.state) els.state.textContent = i18n.finished;
    });
    engine.addEventListener('trackstate', (event) => {
        const track = tracks.get(event.detail?.key);
        if (!track) return;
        const state = event.detail?.state;
        const busy = state === 'loading' || state === 'buffering';
        if (track.loader) track.loader.hidden = !busy;
        if (track.status) {
            track.status.textContent =
                state === 'loading' ? 'chargement' :
                state === 'buffering' ? 'buffering' :
                state === 'error' ? 'erreur' :
                state === 'playing' ? 'lecture' :
                state === 'ready' ? 'prêt' : '';
        }
        track.row.classList.toggle('is-loading', busy);
        track.row.classList.toggle('is-error', state === 'error');
    });
    engine.addEventListener('timeupdate', (event) => {
        const time = Number(event.detail?.time || 0);
        const duration = Number(event.detail?.duration || 0);
        if (els.time) els.time.textContent = `${fmt(time)} / ${fmt(duration)}`;
        if (els.seek && duration > 0) {
            els.seek.value = String(Math.round((time / duration) * 1000));
        }
        root.dispatchEvent(new CustomEvent('ezscore:audio-timeupdate', {
            detail: {time, duration},
        }));
    });

    const dispose = () => {
        if (disposed) return;
        disposed = true;
        window.clearTimeout(saveTimer);
        engine.dispose();
    };
    window.addEventListener('pagehide', dispose, {once: true});
    window.addEventListener('beforeunload', dispose, {once: true});

    if (els.state) els.state.textContent = i18n.ready;
})();
