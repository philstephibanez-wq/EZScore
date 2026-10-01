(() => {
    'use strict';

    class EZScoreAudioEngine extends EventTarget {
        constructor(options = {}) {
            super();

            const AudioContextCtor = window.AudioContext || window.webkitAudioContext;
            if (!AudioContextCtor) {
                throw new Error('WEB_AUDIO_UNAVAILABLE');
            }

            this.context = new AudioContextCtor({latencyHint: 'interactive'});
            // R29 MASTER FX CHAIN
            this.masterInput = this.context.createGain();
            this.masterLow = this.context.createBiquadFilter();
            this.masterLow.type = 'lowshelf';
            this.masterLow.frequency.value = 110;
            this.masterMid = this.context.createBiquadFilter();
            this.masterMid.type = 'peaking';
            this.masterMid.frequency.value = 900;
            this.masterMid.Q.value = 1.0;
            this.masterHigh = this.context.createBiquadFilter();
            this.masterHigh.type = 'highshelf';
            this.masterHigh.frequency.value = 3600;
            this.masterCompressor = this.context.createDynamicsCompressor();
            this.masterCompressor.threshold.value = 0;
            this.masterCompressor.knee.value = 18;
            this.masterCompressor.ratio.value = 1;
            this.masterCompressor.attack.value = 0.015;
            this.masterCompressor.release.value = 0.18;
            this.masterLimiter = this.context.createDynamicsCompressor();
            this.masterLimiter.threshold.value = -1;
            this.masterLimiter.knee.value = 0;
            this.masterLimiter.ratio.value = 20;
            this.masterLimiter.attack.value = 0.003;
            this.masterLimiter.release.value = 0.08;
            this.masterGain = this.context.createGain();
            this.masterGain.gain.value = 1;
            this.masterInput.connect(this.masterLow);
            this.masterLow.connect(this.masterMid);
            this.masterMid.connect(this.masterHigh);
            this.masterHigh.connect(this.masterCompressor);
            this.masterCompressor.connect(this.masterLimiter);
            this.masterLimiter.connect(this.masterGain);
            this.masterGain.connect(this.context.destination);

            this.tracks = new Map();
            this.position = 0;
            this.playbackRate = 1;
            this.playing = false;
            this.disposed = false;
            this.masterTrackKey = options.masterTrackKey || 'original';
            this.syncThresholdSeconds = Number(options.syncThresholdSeconds || 0.060);
            this.syncIntervalMs = Number(options.syncIntervalMs || 250);

            this._syncTimer = null;
            this._raf = null;
            this._navigationHandler = this._onNavigationClick.bind(this);
            this._pageHideHandler = () => this.dispose();

            document.addEventListener('click', this._navigationHandler, true);
            window.addEventListener('pagehide', this._pageHideHandler, {once: true});
            window.addEventListener('beforeunload', this._pageHideHandler, {once: true});

            this._startTimelineLoop();
        }

        addTrack(config) {
            if (this.disposed) return null;
            if (!config || !config.key || !config.url) {
                throw new Error('INVALID_TRACK_CONFIG');
            }

            const media = document.createElement('audio');
            media.preload = 'auto';
            media.playsInline = true;
            media.controls = false;
            media.loop = false;
            media.crossOrigin = null;

            const source = this.context.createMediaElementSource(media);

            const low = this.context.createBiquadFilter();
            low.type = 'lowshelf';
            low.frequency.value = 180;

            const mid = this.context.createBiquadFilter();
            mid.type = 'peaking';
            mid.frequency.value = 1200;
            mid.Q.value = 0.9;

            const high = this.context.createBiquadFilter();
            high.type = 'highshelf';
            high.frequency.value = 5500;

            const gain = this.context.createGain();

            source.connect(low);
            low.connect(mid);
            mid.connect(high);
            high.connect(gain);
            gain.connect(this.masterInput);

            const track = {
                key: config.key,
                label: config.label || config.key,
                url: config.url,
                media,
                source,
                low,
                mid,
                high,
                gain,
                enabled: Boolean(config.enabled),
                volume: Number.isFinite(Number(config.volume)) ? Number(config.volume) : 1,
                state: 'idle',
                loadPromise: null,
                desiredPosition: 0,
                lastError: null,
            };

            gain.gain.value = track.enabled ? track.volume : 0;
            media.playbackRate = this.playbackRate;

            const onWaiting = () => this._setTrackState(track, 'buffering');
            const onPlaying = () => this._setTrackState(track, 'playing');
            const onCanPlay = () => {
                if (!this.playing) this._setTrackState(track, 'ready');
            };
            const onError = () => {
                const code = media.error?.code || 0;
                const message = `MEDIA_ERROR_${code || 'UNKNOWN'}`;
                track.lastError = message;
                this._setTrackState(track, 'error', message);
            };
            const onEnded = () => {
                if (track.key === this._clockTrack()?.key) {
                    this.stop();
                    this.dispatchEvent(new CustomEvent('ended'));
                }
            };

            media.addEventListener('waiting', onWaiting);
            media.addEventListener('stalled', onWaiting);
            media.addEventListener('playing', onPlaying);
            media.addEventListener('canplay', onCanPlay);
            media.addEventListener('error', onError);
            media.addEventListener('ended', onEnded);

            track.destroyListeners = () => {
                media.removeEventListener('waiting', onWaiting);
                media.removeEventListener('stalled', onWaiting);
                media.removeEventListener('playing', onPlaying);
                media.removeEventListener('canplay', onCanPlay);
                media.removeEventListener('error', onError);
                media.removeEventListener('ended', onEnded);
            };

            this.tracks.set(track.key, track);
            this._setTrackState(track, 'idle');

            // Start network/media warm-up without playback. Browser cache then
            // serves the first Play immediately or nearly immediately.
            queueMicrotask(() => {
                if (!this.disposed) this._ensureTrackReady(track).catch((error) => this._trackFailure(track, error));
            });

            return track;
        }

        warmUp(options = {}) {
            if (this.disposed) return Promise.resolve([]);
            const enabledFirst = options.enabledFirst !== false;
            const tracks = Array.from(this.tracks.values());
            const ordered = enabledFirst
                ? [...tracks.filter((t) => t.enabled), ...tracks.filter((t) => !t.enabled)]
                : tracks;
            this.dispatchEvent(new CustomEvent('statechange', {detail: {state: 'preloading'}}));
            return Promise.allSettled(
                ordered.map((track, index) => new Promise((resolve) => {
                    const delay = track.enabled ? 0 : Math.min(1200, 120 * index);
                    setTimeout(() => {
                        this._ensureTrackReady(track)
                            .then(resolve)
                            .catch((error) => {
                                this._trackFailure(track, error);
                                resolve(track);
                            });
                    }, delay);
                }))
            ).then((result) => {
                if (!this.disposed && !this.playing) {
                    this.dispatchEvent(new CustomEvent('statechange', {detail: {state: 'ready'}}));
                }
                return result;
            });
        }

        setTrackEnabled(key, enabled) {
            const track = this.tracks.get(key);
            if (!track || this.disposed) return;

            track.enabled = Boolean(enabled);
            this._applyTrackGain(track);

            if (!track.enabled) {
                track.media.pause();
                this._setTrackState(track, track.media.src ? 'ready' : 'idle');
                return;
            }

            if (this.playing) {
                const position = this.currentTime();
                this._ensureTrackReady(track)
                    .then(async () => {
                        if (this.disposed || !this.playing || !track.enabled) return;
                        track.media.currentTime = Math.min(position, Math.max(0, (track.media.duration || position) - 0.001));
                        track.media.playbackRate = this.playbackRate;
                        await track.media.play();
                    })
                    .catch((error) => this._trackFailure(track, error));
            }
        }

        setTrackVolume(key, value) {
            const track = this.tracks.get(key);
            if (!track) return;
            track.volume = Math.max(0, Math.min(1.25, Number(value) || 0));
            this._applyTrackGain(track);
        }

        setTrackEq(key, {low, mid, high}) {
            const track = this.tracks.get(key);
            if (!track) return;
            const now = this.context.currentTime;

            if (Number.isFinite(Number(low))) {
                track.low.gain.setTargetAtTime(Number(low), now, 0.01);
            }
            if (Number.isFinite(Number(mid))) {
                track.mid.gain.setTargetAtTime(Number(mid), now, 0.01);
            }
            if (Number.isFinite(Number(high))) {
                track.high.gain.setTargetAtTime(Number(high), now, 0.01);
            }
        }

        setMasterEq({low, mid, high}) {
            const now = this.context.currentTime;
            if (Number.isFinite(Number(low))) this.masterLow.gain.setTargetAtTime(Number(low), now, 0.02);
            if (Number.isFinite(Number(mid))) this.masterMid.gain.setTargetAtTime(Number(mid), now, 0.02);
            if (Number.isFinite(Number(high))) this.masterHigh.gain.setTargetAtTime(Number(high), now, 0.02);
        }

        setMasterCompression(value) {
            const amount = Math.max(0, Math.min(100, Number(value) || 0)) / 100;
            const now = this.context.currentTime;
            this.masterCompressor.threshold.setTargetAtTime(-28 * amount, now, 0.02);
            this.masterCompressor.ratio.setTargetAtTime(1 + 3.5 * amount, now, 0.02);
            this.masterCompressor.knee.setTargetAtTime(18 + 8 * amount, now, 0.02);
        }

        setMasterVolume(value) {
            const target = Math.max(0, Math.min(1.25, Number(value) || 0));
            this.masterGain.gain.setTargetAtTime(target, this.context.currentTime, 0.01);
        }

        async setPlaybackRate(value) {
            const rate = Math.max(0.75, Math.min(1.25, Number(value) || 1));
            this.playbackRate = rate;

            this.tracks.forEach((track) => {
                track.media.playbackRate = rate;
            });

            if (this.playing) {
                this._syncNow(true);
            }
        }

        async play() {
            if (this.disposed || this.playing) return;

            if (this.context.state === 'suspended') {
                await this.context.resume();
            }

            const enabled = this._enabledTracks();
            if (enabled.length === 0) {
                throw new Error('NO_ENABLED_TRACK');
            }

            this.dispatchEvent(new CustomEvent('statechange', {detail: {state: 'loading'}}));

            // Loading media elements is streaming-based. We only wait until each
            // selected track has enough data to start, never for the whole file.
            await Promise.all(enabled.map((track) => this._ensureTrackReady(track)));

            if (this.disposed) return;

            const target = this.position;
            enabled.forEach((track) => {
                if (Number.isFinite(track.media.duration)) {
                    track.media.currentTime = Math.min(target, Math.max(0, track.media.duration - 0.001));
                } else {
                    track.media.currentTime = target;
                }
                track.media.playbackRate = this.playbackRate;
            });

            const starts = enabled.map((track) => track.media.play());
            await Promise.all(starts);

            this.playing = true;
            this.dispatchEvent(new CustomEvent('statechange', {detail: {state: 'playing'}}));
            this._startSyncLoop();
        }

        pause() {
            if (this.disposed) return;

            this.position = this.currentTime();
            this.playing = false;

            this.tracks.forEach((track) => track.media.pause());
            this._stopSyncLoop();

            this.dispatchEvent(new CustomEvent('statechange', {detail: {state: 'paused'}}));
        }

        stop() {
            if (this.disposed) return;

            this.playing = false;
            this.position = 0;
            this._stopSyncLoop();

            this.tracks.forEach((track) => {
                track.media.pause();
                try {
                    track.media.currentTime = 0;
                } catch (_) {}
            });

            this.dispatchEvent(new CustomEvent('statechange', {detail: {state: 'ready'}}));
            this.dispatchEvent(new CustomEvent('timeupdate', {detail: {time: 0, duration: this.duration()}}));
        }

        seek(seconds) {
            if (this.disposed) return;

            const value = Math.max(0, Number(seconds) || 0);
            this.position = value;

            this._enabledTracks().forEach((track) => {
                if (!track.media.src) return;
                try {
                    const duration = Number.isFinite(track.media.duration) ? track.media.duration : value;
                    track.media.currentTime = Math.min(value, Math.max(0, duration - 0.001));
                } catch (_) {}
            });

            this._syncNow(true);
        }

        currentTime() {
            const clock = this._clockTrack();

            if (clock && clock.media.src && Number.isFinite(clock.media.currentTime)) {
                return clock.media.currentTime;
            }

            return this.position;
        }

        duration() {
            const clock = this._clockTrack();
            if (clock && Number.isFinite(clock.media.duration)) {
                return clock.media.duration;
            }

            let max = 0;
            this.tracks.forEach((track) => {
                if (Number.isFinite(track.media.duration)) {
                    max = Math.max(max, track.media.duration);
                }
            });

            return max;
        }

        dispose() {
            if (this.disposed) return;
            this.disposed = true;
            this.playing = false;

            this._stopSyncLoop();

            if (this._raf) {
                cancelAnimationFrame(this._raf);
                this._raf = null;
            }

            document.removeEventListener('click', this._navigationHandler, true);

            this.tracks.forEach((track) => {
                try { track.media.pause(); } catch (_) {}

                // This is intentional: removing src + load() aborts an in-flight
                // media download immediately before the next page request starts.
                try {
                    track.media.removeAttribute('src');
                    track.media.load();
                } catch (_) {}

                try { track.destroyListeners?.(); } catch (_) {}
                try { track.source.disconnect(); } catch (_) {}
                try { track.low.disconnect(); } catch (_) {}
                try { track.mid.disconnect(); } catch (_) {}
                try { track.high.disconnect(); } catch (_) {}
                try { track.gain.disconnect(); } catch (_) {}
            });

            this.tracks.clear();

            try { this.masterInput.disconnect(); } catch (_) {}
            try { this.masterLow.disconnect(); } catch (_) {}
            try { this.masterMid.disconnect(); } catch (_) {}
            try { this.masterHigh.disconnect(); } catch (_) {}
            try { this.masterCompressor.disconnect(); } catch (_) {}
            try { this.masterLimiter.disconnect(); } catch (_) {}
            try { this.masterGain.disconnect(); } catch (_) {}
            try { this.context.close(); } catch (_) {}

            this.dispatchEvent(new CustomEvent('disposed'));
        }

        _applyTrackGain(track) {
            const value = track.enabled ? track.volume : 0;
            track.gain.gain.setTargetAtTime(value, this.context.currentTime, 0.01);
        }

        _enabledTracks() {
            return Array.from(this.tracks.values()).filter((track) => track.enabled);
        }

        _clockTrack() {
            const preferred = this.tracks.get(this.masterTrackKey);
            if (preferred?.enabled && preferred.media.src) {
                return preferred;
            }

            return this._enabledTracks().find((track) => track.media.src) || this._enabledTracks()[0] || null;
        }

        _setTrackState(track, state, error = null) {
            track.state = state;
            this.dispatchEvent(new CustomEvent('trackstate', {
                detail: {
                    key: track.key,
                    state,
                    error,
                },
            }));
        }

        _trackFailure(track, error) {
            const message = error instanceof Error ? error.message : String(error);
            track.lastError = message;
            this._setTrackState(track, 'error', message);
            this.dispatchEvent(new CustomEvent('error', {
                detail: {key: track.key, error: message},
            }));
        }

        _ensureTrackReady(track) {
            if (this.disposed) {
                return Promise.reject(new Error('ENGINE_DISPOSED'));
            }

            if (track.media.src && track.media.readyState >= HTMLMediaElement.HAVE_FUTURE_DATA) {
                this._setTrackState(track, 'ready');
                return Promise.resolve(track);
            }

            if (track.loadPromise) {
                return track.loadPromise;
            }

            this._setTrackState(track, 'loading');

            track.loadPromise = new Promise((resolve, reject) => {
                let settled = false;
                const media = track.media;

                const cleanup = () => {
                    media.removeEventListener('canplay', onCanPlay);
                    media.removeEventListener('loadedmetadata', onMetadata);
                    media.removeEventListener('error', onError);
                    clearTimeout(timeout);
                };

                const succeed = () => {
                    if (settled) return;
                    settled = true;
                    cleanup();
                    this._setTrackState(track, 'ready');
                    resolve(track);
                };

                const onCanPlay = () => succeed();

                const onMetadata = () => {
                    // Some browsers report HAVE_CURRENT_DATA before firing
                    // canplay for local MP3/M4A. Allow start as soon as a frame
                    // beyond the current position is available.
                    if (media.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA) {
                        succeed();
                    }
                };

                const onError = () => {
                    if (settled) return;
                    settled = true;
                    cleanup();
                    const code = media.error?.code || 0;
                    reject(new Error(`${track.key}: MEDIA_ERROR_${code || 'UNKNOWN'}`));
                };

                const timeout = window.setTimeout(() => {
                    if (settled) return;
                    settled = true;
                    cleanup();
                    reject(new Error(`${track.key}: LOAD_TIMEOUT`));
                }, 15000);

                media.addEventListener('canplay', onCanPlay);
                media.addEventListener('loadedmetadata', onMetadata);
                media.addEventListener('error', onError);

                if (!media.src) {
                    media.src = track.url;
                    media.preload = 'auto';
                    media.playbackRate = this.playbackRate;
                    media.load();
                } else {
                    media.load();
                }
            }).catch((error) => {
                this._trackFailure(track, error);
                throw error;
            }).finally(() => {
                track.loadPromise = null;
            });

            return track.loadPromise;
        }

        _startSyncLoop() {
            this._stopSyncLoop();
            this._syncTimer = window.setInterval(() => this._syncNow(false), this.syncIntervalMs);
        }

        _stopSyncLoop() {
            if (this._syncTimer) {
                window.clearInterval(this._syncTimer);
                this._syncTimer = null;
            }
        }

        _syncNow(force) {
            if (!this.playing && !force) return;

            const clock = this._clockTrack();
            if (!clock || !clock.media.src) return;

            const clockTime = clock.media.currentTime;

            this._enabledTracks().forEach((track) => {
                if (track === clock || !track.media.src || track.media.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
                    return;
                }

                const drift = track.media.currentTime - clockTime;

                if (force || Math.abs(drift) > this.syncThresholdSeconds) {
                    try {
                        track.media.currentTime = clockTime;
                    } catch (_) {}
                }
            });

            this.position = clockTime;
        }

        _startTimelineLoop() {
            const tick = () => {
                if (this.disposed) return;

                const time = this.currentTime();
                const duration = this.duration();

                this.dispatchEvent(new CustomEvent('timeupdate', {
                    detail: {time, duration},
                }));

                this._raf = requestAnimationFrame(tick);
            };

            this._raf = requestAnimationFrame(tick);
        }

        _onNavigationClick(event) {
            if (this.disposed || event.defaultPrevented || event.button !== 0) return;
            if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;

            const anchor = event.target instanceof Element ? event.target.closest('a[href]') : null;
            if (!anchor) return;
            if (anchor.hasAttribute('data-ez-workflow-ajax')) return;

            const target = anchor.getAttribute('target');
            if (target && target !== '_self') return;

            const href = anchor.getAttribute('href') || '';
            if (href === '' || href.startsWith('#') || href.startsWith('javascript:')) return;

            // Do not block navigation. Abort every media request synchronously,
            // then let the browser follow the link normally.
            this.dispose();
        }
    }

    window.EZScoreAudioEngine = EZScoreAudioEngine;
})();
