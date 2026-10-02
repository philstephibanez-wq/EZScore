(() => {
    const root = document.querySelector('[data-display-gate]');
    if (!root) return;

    const waiting = root.querySelector('[data-display-waiting]');
    const session = root.querySelector('[data-display-session]');
    const badge = root.querySelector('[data-display-badge]');
    const title = root.querySelector('[data-display-title]');
    const conductor = root.querySelector('[data-display-conductor]');
    const join = root.querySelector('[data-display-join]');
    const url = root.dataset.statusUrl;

    let busy = false;

    async function refresh() {
        if (busy) return;
        busy = true;

        try {
            const response = await fetch(url, {
                headers: {'Accept': 'application/json'},
                credentials: 'same-origin',
                cache: 'no-store',
            });

            if (!response.ok) return;

            const data = await response.json();

            if (!data.active) {
                waiting.hidden = false;
                session.hidden = true;
                return;
            }

            badge.textContent = data.test ? 'TEST' : 'LIVE';
            title.textContent = data.title;
            conductor.textContent = 'Chef d’orchestre : ' + data.conductor;
            join.href = data.join_url;

            waiting.hidden = true;
            session.hidden = false;
        } catch (_) {
            waiting.hidden = false;
            session.hidden = true;
        } finally {
            busy = false;
        }
    }

    refresh();
    window.setInterval(refresh, 1500);
})();
