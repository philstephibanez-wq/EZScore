(() => {
    'use strict';
    if (window.EZScoreWorkflowAjax) return;

    const persistentScripts = new Set([
        '/assets/js/app.js',
        '/assets/js/dirty-tracker.js',
        '/assets/js/ez-modal.js',
        '/assets/js/analysis-worker-status.js',
        '/assets/js/audio/ezscore-audio-engine.js',
        '/assets/js/audio/ezscore-audio-session.js',
        '/assets/js/song-workflow-ajax.js'
    ]);

    const stages = new Map();
    let activeKey = null;
    let requestController = null;

    const keyFor = (raw) => {
        const url = new URL(raw, location.href);
        return `${url.pathname}${url.search}`;
    };

    const songIdFor = (raw) => {
        const url = new URL(raw, location.href);
        const match = url.pathname.match(/\/song\/(\d+)(?:\/|$)/);
        return match ? match[1] : '';
    };

    const sameSong = (raw) => {
        const a = songIdFor(location.href);
        const b = songIdFor(raw);
        return Boolean(a && b && a === b);
    };

    const main = () => document.querySelector('#main-content');

    const stashActiveStage = () => {
        const host = main();
        if (!host || !activeKey) return;
        const fragment = document.createDocumentFragment();
        while (host.firstChild) fragment.appendChild(host.firstChild);
        const previous = stages.get(activeKey) || {};
        stages.set(activeKey, {
            ...previous,
            fragment,
            title: document.title,
            scrollY: window.scrollY
        });
    };

    const restoreCachedStage = (key, url, push) => {
        const host = main();
        const cached = stages.get(key);
        if (!host || !cached?.fragment) return false;

        document.dispatchEvent(new CustomEvent('ezscore:workflow-before-swap', {detail: {url}}));
        stashActiveStage();
        host.appendChild(cached.fragment);
        activeKey = key;
        if (cached.title) document.title = cached.title;
        if (push) history.pushState({ezscoreWorkflow: true}, '', url);
        document.dispatchEvent(new CustomEvent('ezscore:workflow-after-swap', {detail: {url, cached: true}}));
        window.scrollTo({top: Number(cached.scrollY || 0), behavior: 'auto'});
        return true;
    };

    const syncStyles = (incoming) => {
        const loaded = new Set(
            [...document.querySelectorAll('link[rel="stylesheet"][href]')]
                .map((link) => new URL(link.href, location.href).href)
        );
        incoming.querySelectorAll('link[rel="stylesheet"][href]').forEach((link) => {
            const href = link.getAttribute('href');
            const absolute = new URL(href, location.href).href;
            if (loaded.has(absolute)) return;
            const clone = document.createElement('link');
            clone.rel = 'stylesheet';
            clone.href = href;
            clone.dataset.ezWorkflowStyle = '1';
            document.head.appendChild(clone);
            loaded.add(absolute);
        });
    };

    const pageScripts = (incoming) => [...incoming.querySelectorAll('script[src]')]
        .map((node) => node.getAttribute('src'))
        .filter(Boolean)
        .filter((src) => {
            const url = new URL(src, location.href);
            return !persistentScripts.has(url.pathname) && !url.hostname.includes('code.jquery.com');
        });

    const runScripts = async (sources) => {
        for (const src of sources) {
            await new Promise((resolve, reject) => {
                const script = document.createElement('script');
                script.src = src;
                script.async = false;
                script.dataset.ezWorkflowPageScript = '1';
                script.onload = resolve;
                script.onerror = () => reject(new Error(`SCRIPT_LOAD_FAILED:${src}`));
                document.body.appendChild(script);
            });
        }
    };

    const fetchStage = async (url) => {
        if (requestController) requestController.abort();
        requestController = new AbortController();
        const response = await fetch(url, {
            method: 'GET',
            credentials: 'same-origin',
            signal: requestController.signal,
            headers: {'Accept': 'text/html', 'X-EZScore-Workflow-Ajax': '1'}
        });
        if (!response.ok) throw new Error(`HTTP_${response.status}`);
        const type = response.headers.get('content-type') || '';
        if (!type.includes('text/html')) throw new Error(`UNEXPECTED_CONTENT_TYPE:${type}`);
        return {html: await response.text(), url: response.url || String(url)};
    };

    const mountFetchedStage = async (html, finalUrl, push) => {
        const host = main();
        const incoming = new DOMParser().parseFromString(html, 'text/html');
        const nextMain = incoming.querySelector('#main-content');

        if (!host || !nextMain || !sameSong(finalUrl)) {
            location.href = finalUrl;
            return false;
        }

        document.dispatchEvent(new CustomEvent('ezscore:workflow-before-swap', {detail: {url: finalUrl}}));
        stashActiveStage();
        syncStyles(incoming);

        const fragment = document.createDocumentFragment();
        [...nextMain.childNodes].forEach((node) => fragment.appendChild(document.importNode(node, true)));
        host.appendChild(fragment);

        activeKey = keyFor(finalUrl);
        document.title = incoming.title || document.title;
        stages.set(activeKey, {fragment: null, title: document.title, scrollY: 0});
        if (push) history.pushState({ezscoreWorkflow: true}, '', finalUrl);

        await runScripts(pageScripts(incoming));

        document.dispatchEvent(new CustomEvent('ezscore:workflow-after-swap', {detail: {url: finalUrl, cached: false}}));
        window.scrollTo({top: 0, behavior: 'auto'});
        return true;
    };

    const navigate = async (rawUrl, {push = true} = {}) => {
        const url = new URL(rawUrl, location.href).href;
        if (!sameSong(url)) {
            location.href = url;
            return false;
        }

        const key = keyFor(url);
        if (key === activeKey) return true;
        if (stages.get(key)?.fragment) return restoreCachedStage(key, url, push);

        try {
            const result = await fetchStage(url);
            return await mountFetchedStage(result.html, result.url, push);
        } catch (error) {
            if (error?.name === 'AbortError') return false;
            console.error('EZScore workflow navigation failed', error);
            location.href = url;
            return false;
        } finally {
            requestController = null;
        }
    };

    activeKey = keyFor(location.href);
    stages.set(activeKey, {fragment: null, title: document.title, scrollY: window.scrollY});

    document.addEventListener('click', (event) => {
        if (event.defaultPrevented || event.button !== 0) return;
        if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
        const anchor = event.target instanceof Element
            ? event.target.closest('a[data-ez-workflow-ajax][href]')
            : null;
        if (!anchor || !sameSong(anchor.href)) return;
        event.preventDefault();
        navigate(anchor.href, {push: true});
    });

    window.addEventListener('popstate', () => {
        if (sameSong(location.href)) navigate(location.href, {push: false});
    });

    window.EZScoreWorkflowAjax = Object.freeze({
        navigate,
        get activeKey() { return activeKey; },
        get cachedStageCount() {
            return [...stages.values()].filter((stage) => stage.fragment).length;
        }
    });
})();
