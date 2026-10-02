(() => {
    'use strict';

    if (window.EZScoreCast) {
        return;
    }

    const STATES = Object.freeze({
        UNAVAILABLE: 'unavailable',
        IDLE: 'idle',
        SCANNING: 'scanning',
        CONNECTING: 'connecting',
        CONNECTED: 'connected',
        DISCONNECTING: 'disconnecting',
        ERROR: 'error',
    });

    const providers = new Map();
    const listeners = new Set();

    let state = {
        state: STATES.UNAVAILABLE,
        providerId: null,
        device: null,
        error: null,
    };

    const clone = (value) => {
        if (value === undefined) return undefined;
        return JSON.parse(JSON.stringify(value));
    };

    const emit = (patch = {}) => {
        state = Object.assign({}, state, patch);
        const snapshot = clone(state);
        listeners.forEach((listener) => {
            try {
                listener(snapshot);
            } catch (error) {
                console.error('[EZScoreCast] listener failed', error);
            }
        });
        window.dispatchEvent(new CustomEvent('ezscorecast:status', { detail: snapshot }));
        return snapshot;
    };

    const normalizeDevice = (device, providerId) => {
        if (!device || typeof device !== 'object') {
            throw new TypeError('Invalid cast device');
        }

        const id = String(device.id ?? '').trim();
        const name = String(device.name ?? '').trim();
        if (!id || !name) {
            throw new TypeError('Cast device requires id and name');
        }

        return {
            id,
            name,
            transport: String(device.transport ?? 'unknown'),
            providerId,
            metadata: device.metadata && typeof device.metadata === 'object'
                ? clone(device.metadata)
                : {},
        };
    };

    const providerAvailable = async (provider) => {
        try {
            return Boolean(await provider.available());
        } catch (error) {
            console.warn(`[EZScoreCast] provider ${provider.id} availability failed`, error);
            return false;
        }
    };

    const orderedProviders = () => [...providers.values()]
        .sort((a, b) => (b.priority ?? 0) - (a.priority ?? 0));

    const availableProviders = async () => {
        const result = [];
        for (const provider of orderedProviders()) {
            if (await providerAvailable(provider)) {
                result.push(provider);
            }
        }
        return result;
    };

    const requireProvider = async (providerId = null) => {
        if (providerId) {
            const provider = providers.get(providerId);
            if (!provider || !(await providerAvailable(provider))) {
                throw new Error(`Cast provider unavailable: ${providerId}`);
            }
            return provider;
        }

        const available = await availableProviders();
        if (!available.length) {
            throw new Error('No cast provider available');
        }
        return available[0];
    };

    const validateProvider = (provider) => {
        if (!provider || typeof provider !== 'object') {
            throw new TypeError('Cast provider must be an object');
        }

        const id = String(provider.id ?? '').trim();
        if (!id) {
            throw new TypeError('Cast provider requires an id');
        }

        for (const method of ['available', 'scan', 'connect', 'disconnect', 'status']) {
            if (typeof provider[method] !== 'function') {
                throw new TypeError(`Cast provider ${id} missing ${method}()`);
            }
        }

        return id;
    };

    const api = {
        version: 'R1',
        STATES,

        registerProvider(provider) {
            const id = validateProvider(provider);
            providers.set(id, provider);
            return id;
        },

        unregisterProvider(providerId) {
            return providers.delete(String(providerId));
        },

        async available() {
            return (await availableProviders()).length > 0;
        },

        async capabilities() {
            const result = [];
            for (const provider of await availableProviders()) {
                let capabilities = {};
                if (typeof provider.capabilities === 'function') {
                    try {
                        capabilities = await provider.capabilities() || {};
                    } catch (error) {
                        capabilities = { error: String(error?.message || error) };
                    }
                }
                result.push({
                    providerId: provider.id,
                    priority: provider.priority ?? 0,
                    capabilities: clone(capabilities),
                });
            }
            return result;
        },

        async scan(options = {}) {
            emit({ state: STATES.SCANNING, error: null });
            try {
                const selected = options.providerId
                    ? [await requireProvider(options.providerId)]
                    : await availableProviders();

                const devices = [];
                for (const provider of selected) {
                    const raw = await provider.scan(options) || [];
                    for (const device of raw) {
                        devices.push(normalizeDevice(device, provider.id));
                    }
                }

                emit({
                    state: devices.length ? STATES.IDLE : ((await api.available()) ? STATES.IDLE : STATES.UNAVAILABLE),
                    error: null,
                });
                return devices;
            } catch (error) {
                emit({ state: STATES.ERROR, error: String(error?.message || error) });
                throw error;
            }
        },

        async connect(deviceOrId, options = {}) {
            const device = typeof deviceOrId === 'object' && deviceOrId
                ? deviceOrId
                : { id: String(deviceOrId), providerId: options.providerId };

            const providerId = String(device.providerId || options.providerId || '').trim() || null;
            const provider = await requireProvider(providerId);

            emit({
                state: STATES.CONNECTING,
                providerId: provider.id,
                device: null,
                error: null,
            });

            try {
                const result = await provider.connect(device.id, options);
                const connectedDevice = result?.device
                    ? normalizeDevice(result.device, provider.id)
                    : {
                        id: String(device.id),
                        name: String(device.name || device.id),
                        transport: String(device.transport || result?.transport || 'unknown'),
                        providerId: provider.id,
                        metadata: {},
                    };

                return emit({
                    state: STATES.CONNECTED,
                    providerId: provider.id,
                    device: connectedDevice,
                    error: null,
                });
            } catch (error) {
                emit({
                    state: STATES.ERROR,
                    providerId: provider.id,
                    device: null,
                    error: String(error?.message || error),
                });
                throw error;
            }
        },

        async disconnect() {
            if (!state.providerId) {
                return emit({
                    state: (await api.available()) ? STATES.IDLE : STATES.UNAVAILABLE,
                    providerId: null,
                    device: null,
                    error: null,
                });
            }

            const provider = providers.get(state.providerId);
            if (!provider) {
                return emit({
                    state: STATES.UNAVAILABLE,
                    providerId: null,
                    device: null,
                    error: null,
                });
            }

            emit({ state: STATES.DISCONNECTING, error: null });
            try {
                await provider.disconnect();
                return emit({
                    state: (await api.available()) ? STATES.IDLE : STATES.UNAVAILABLE,
                    providerId: null,
                    device: null,
                    error: null,
                });
            } catch (error) {
                emit({ state: STATES.ERROR, error: String(error?.message || error) });
                throw error;
            }
        },

        async status() {
            if (state.providerId && providers.has(state.providerId)) {
                try {
                    const remote = await providers.get(state.providerId).status();
                    if (remote && typeof remote === 'object') {
                        return emit(Object.assign({}, remote, {
                            providerId: state.providerId,
                        }));
                    }
                } catch (error) {
                    return emit({ state: STATES.ERROR, error: String(error?.message || error) });
                }
            }

            const hasProvider = await api.available();
            if (state.state === STATES.UNAVAILABLE && hasProvider) {
                emit({ state: STATES.IDLE, error: null });
            } else if (!hasProvider && state.state !== STATES.CONNECTED) {
                emit({ state: STATES.UNAVAILABLE, providerId: null, device: null });
            }
            return clone(state);
        },

        subscribe(listener) {
            if (typeof listener !== 'function') {
                throw new TypeError('listener must be a function');
            }
            listeners.add(listener);
            listener(clone(state));
            return () => listeners.delete(listener);
        },

        providers() {
            return orderedProviders().map((provider) => ({
                id: provider.id,
                priority: provider.priority ?? 0,
            }));
        },
    };

    Object.defineProperty(window, 'EZScoreCast', {
        value: Object.freeze(api),
        configurable: false,
        enumerable: true,
        writable: false,
    });
})();
