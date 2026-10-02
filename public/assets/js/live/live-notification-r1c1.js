(() => {
    const banner = document.querySelector('[data-live-notification]');
    if (!banner) return;

    const label = banner.querySelector('[data-live-label]');
    const conductor = banner.querySelector('[data-live-conductor]');
    const join = banner.querySelector('[data-live-join]');
    const url = banner.dataset.liveStatusUrl;

    let busy = false;

    async function poll() {
        if (busy) return;
        busy = true;
        try {
            const response = await fetch(url, {
                headers: {'Accept': 'application/json'},
                credentials: 'same-origin',
                cache: 'no-store'
            });
            if (!response.ok) return;
            const data = await response.json();

            if (!data.active) {
                banner.hidden = true;
                return;
            }

            label.textContent = (data.test ? 'TEST — Session ouverte : ' : 'Session ouverte : ') + data.title;
            conductor.textContent = 'Chef d’orchestre : ' + data.conductor;
            join.href = data.join_url;
            banner.hidden = false;
        } catch (_) {
            // Notification non bloquante : aucune régression du reste de l'application.
        } finally {
            busy = false;
        }
    }

    poll();
    window.setInterval(poll, 2000);
})();
