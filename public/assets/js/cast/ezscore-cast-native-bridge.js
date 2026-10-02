(() => {
    'use strict';

    const cast = window.EZScoreCast;
    const bridge = window.EZScoreNativeCast;

    if (!cast || !bridge || typeof bridge !== 'object') {
        return;
    }

    const call = async (method, ...args) => {
        if (typeof bridge[method] !== 'function') {
            throw new Error(`Native cast bridge missing ${method}()`);
        }

        const value = await bridge[method](...args);
        if (typeof value === 'string') {
            try {
                return JSON.parse(value);
            } catch (_) {
                return value;
            }
        }
        return value;
    };

    cast.registerProvider({
        id: 'native',
        priority: 100,

        async available() {
            if (typeof bridge.available !== 'function') return true;
            return Boolean(await call('available'));
        },

        async capabilities() {
            if (typeof bridge.capabilities !== 'function') {
                return {
                    audio: true,
                    video: true,
                    transports: [],
                };
            }
            return await call('capabilities');
        },

        async scan(options) {
            const devices = await call('scan', options || {});
            return Array.isArray(devices) ? devices : [];
        },

        async connect(deviceId, options) {
            return await call('connect', String(deviceId), options || {});
        },

        async disconnect() {
            return await call('disconnect');
        },

        async status() {
            const status = await call('status');
            return status && typeof status === 'object' ? status : {};
        },
    });
})();
