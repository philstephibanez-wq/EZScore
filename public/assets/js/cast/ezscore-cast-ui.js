(() => {
    'use strict';

    const cast = window.EZScoreCast;
    if (!cast) return;

    const BUTTON_ID = 'ezscore-cast-button';
    const MENU_ID = 'ezscore-cast-menu';

    const text = (fr, en) => (document.documentElement.lang || '').toLowerCase().startsWith('fr') ? fr : en;

    const createUi = () => {
        if (document.getElementById(BUTTON_ID)) return;

        const host = document.querySelector('.ez-topbar-right');
        if (!host) return;

        const wrap = document.createElement('div');
        wrap.className = 'ez-cast-control';
        wrap.dataset.ezCastControl = '';

        const button = document.createElement('button');
        button.type = 'button';
        button.id = BUTTON_ID;
        button.className = 'ez-cast-button';
        button.textContent = text('Caster', 'Cast');
        button.setAttribute('aria-haspopup', 'dialog');
        button.setAttribute('aria-expanded', 'false');

        const menu = document.createElement('div');
        menu.id = MENU_ID;
        menu.className = 'ez-cast-menu';
        menu.hidden = true;
        menu.setAttribute('role', 'dialog');
        menu.setAttribute('aria-label', text('Projection', 'Cast'));

        const status = document.createElement('p');
        status.className = 'ez-cast-status';
        status.textContent = text('Prêt', 'Ready');

        const devices = document.createElement('div');
        devices.className = 'ez-cast-devices';

        const stop = document.createElement('button');
        stop.type = 'button';
        stop.className = 'ez-cast-stop';
        stop.textContent = text('Arrêter la projection', 'Stop casting');
        stop.hidden = true;

        menu.append(status, devices, stop);
        wrap.append(button, menu);
        host.prepend(wrap);

        const close = () => {
            menu.hidden = true;
            button.setAttribute('aria-expanded', 'false');
        };

        const open = async () => {
            menu.hidden = false;
            button.setAttribute('aria-expanded', 'true');
            devices.replaceChildren();

            const current = await cast.status();
            if (current.state === cast.STATES.CONNECTED) {
                status.textContent = `${text('Connecté à', 'Connected to')} ${current.device?.name || ''}`.trim();
                stop.hidden = false;
                return;
            }

            stop.hidden = true;
            status.textContent = text('Recherche des écrans…', 'Searching for displays…');

            try {
                const found = await cast.scan();
                if (!found.length) {
                    status.textContent = text('Aucun récepteur disponible', 'No receiver available');
                    return;
                }

                status.textContent = text('Choisir un écran', 'Choose a display');
                found.forEach((device) => {
                    const item = document.createElement('button');
                    item.type = 'button';
                    item.className = 'ez-cast-device';
                    item.textContent = `${device.name}${device.transport && device.transport !== 'unknown' ? ` · ${device.transport}` : ''}`;
                    item.addEventListener('click', async () => {
                        item.disabled = true;
                        status.textContent = text('Connexion…', 'Connecting…');
                        try {
                            await cast.connect(device);
                        } catch (error) {
                            status.textContent = `${text('Échec', 'Failed')}: ${error.message || error}`;
                            item.disabled = false;
                        }
                    });
                    devices.appendChild(item);
                });
            } catch (error) {
                status.textContent = `${text('Échec', 'Failed')}: ${error.message || error}`;
            }
        };

        button.addEventListener('click', () => menu.hidden ? open() : close());

        stop.addEventListener('click', async () => {
            stop.disabled = true;
            try {
                await cast.disconnect();
                close();
            } finally {
                stop.disabled = false;
            }
        });

        document.addEventListener('click', (event) => {
            if (!wrap.contains(event.target)) close();
        });

        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') close();
        });

        cast.subscribe((current) => {
            const connected = current.state === cast.STATES.CONNECTED;
            button.classList.toggle('is-connected', connected);
            button.textContent = connected
                ? `${text('Caster', 'Cast')} · ${current.device?.name || text('connecté', 'connected')}`
                : text('Caster', 'Cast');

            if (!menu.hidden) {
                if (connected) {
                    status.textContent = `${text('Connecté à', 'Connected to')} ${current.device?.name || ''}`.trim();
                    stop.hidden = false;
                    devices.replaceChildren();
                } else if (current.state === cast.STATES.ERROR) {
                    status.textContent = `${text('Échec', 'Failed')}: ${current.error || ''}`;
                }
            }
        });
    };

    const boot = async () => {
        try {
            if (await cast.available()) createUi();
        } catch (error) {
            console.warn('[EZScoreCast] UI disabled', error);
        }
    };

    boot();
})();
