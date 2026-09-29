(() => {
'use strict';

const root = document.querySelector('[data-lyrics-ovh]');
const source = document.querySelector('[data-lyrics-source]');
if (!root || !source) return;

const input = root.querySelector('[data-lyrics-ovh-query]');
const button = root.querySelector('[data-lyrics-ovh-search]');
const resultsHost = document.querySelector('[data-lyrics-ovh-results]');
const status = document.querySelector('[data-lyrics-ovh-status]');
const searchUrl = root.dataset.searchUrl || '';
const autocompleteUrl = root.dataset.autocompleteUrl || searchUrl;
const autocompleteCache = new Map();
const importUrl = root.dataset.importUrl || '';
const token = root.dataset.token || '';

function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, c => ({
    '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#039;'
  }[c]));
}

function setStatus(text, error = false) {
  if (!status) return;
  status.textContent = text || '';
  status.classList.toggle('is-error', !!error);
}

async function post(url, payload) {
  const response = await fetch(url, {
    method: 'POST',
    credentials: 'same-origin',
    headers: {'Content-Type':'application/json', 'Accept':'application/json'},
    body: JSON.stringify(payload)
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(data.error || `http_${response.status}`);
    error.code = data.error || '';
    throw error;
  }

  return data;
}

function renderResults(results) {
  if (!resultsHost) return;

  if (!Array.isArray(results) || !results.length) {
    resultsHost.innerHTML = '<p class="page-note">Aucun résultat trouvé.</p>';
    return;
  }

  resultsHost.innerHTML = results.map(item => {
    const cover = item.cover
      ? `<img src="${esc(item.cover)}" alt="" loading="lazy" referrerpolicy="no-referrer">`
      : '';
    const album = item.album ? `<small>${esc(item.album)}</small>` : '';

    const action = item.available
      ? `<button type="button"
                 data-lyrics-ovh-use
                 data-artist="${esc(item.artist)}"
                 data-title="${esc(item.title)}">Utiliser</button>`
      : `<button type="button" disabled class="lyrics-ovh-unavailable"
                 title="Lyrics.ovh ne fournit pas de paroles pour cette piste">Paroles indisponibles</button>`;

    return `
      <article class="lyrics-ovh-result${item.available ? '' : ' is-unavailable'}">
        ${cover}
        <div class="lyrics-ovh-result-main">
          <strong>${esc(item.title)}</strong>
          <span>${esc(item.artist)}</span>
          ${album}
        </div>
        ${action}
      </article>`;
  }).join('');
}

let autocompleteTimer = null;
let autocompleteAbort = null;
let autocompleteIndex = -1;

function autocompleteBox() {
  return root.querySelector('[data-lyrics-ovh-autocomplete]');
}

function closeAutocomplete() {
  const box = autocompleteBox();
  if (box) {
    box.innerHTML = '';
    box.hidden = true;
  }
  autocompleteIndex = -1;
}

function renderAutocomplete(results) {
  const box = autocompleteBox();
  if (!box) return;

  const items = (Array.isArray(results) ? results : [])
    .slice(0, 6);

  if (!items.length) {
    closeAutocomplete();
    return;
  }

  box.innerHTML = items.map((item, index) => `
    <button type="button"
            class="lyrics-ovh-autocomplete-item"
            data-lyrics-ovh-autocomplete-item
            data-index="${index}"
            data-artist="${esc(item.artist)}"
            data-title="${esc(item.title)}">
      <span class="lyrics-ovh-autocomplete-title">${esc(item.title)}</span>
      <span class="lyrics-ovh-autocomplete-artist">${esc(item.artist)}</span>
    </button>
  `).join('');

  box.hidden = false;
  autocompleteIndex = -1;
}

async function autocompleteSearch() {
  const query = String(input?.value || '').trim();
  const cacheKey = query.toLocaleLowerCase();

  if (query.length < 2) {
    closeAutocomplete();
    return;
  }

  if (autocompleteCache.has(cacheKey)) {
    renderAutocomplete(autocompleteCache.get(cacheKey));
    return;
  }

  if (autocompleteAbort) autocompleteAbort.abort();
  autocompleteAbort = new AbortController();

  try {
    const response = await fetch(autocompleteUrl, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {'Content-Type':'application/json', 'Accept':'application/json'},
      body: JSON.stringify({_token: token, query}),
      signal: autocompleteAbort.signal
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || `http_${response.status}`);

    const results = Array.isArray(data.results) ? data.results : [];
    autocompleteCache.set(cacheKey, results);
    if (autocompleteCache.size > 40) {
      const oldest = autocompleteCache.keys().next().value;
      autocompleteCache.delete(oldest);
    }
    renderAutocomplete(results);
  } catch (error) {
    if (error.name !== 'AbortError') {
      console.error('Lyrics.ovh autocomplete failed', error);
      closeAutocomplete();
    }
  }
}

function scheduleAutocomplete() {
  clearTimeout(autocompleteTimer);
  autocompleteTimer = setTimeout(autocompleteSearch, 140);
}

function activateAutocomplete(items, index) {
  autocompleteIndex = Math.max(0, Math.min(items.length - 1, index));
  items.forEach((item, itemIndex) => {
    item.classList.toggle('is-active', itemIndex === autocompleteIndex);
  });
  items[autocompleteIndex]?.scrollIntoView({block:'nearest'});
}

function chooseAutocomplete(item) {
  if (!item) return;

  const artist = String(item.dataset.artist || '').trim();
  const title = String(item.dataset.title || '').trim();

  input.value = `${artist} ${title}`.trim();
  closeAutocomplete();
  search();
}

async function search() {
  const query = String(input?.value || '').trim();
  if (!query) {
    setStatus('Saisissez un titre, un artiste ou les deux.', true);
    return;
  }

  button.disabled = true;
  setStatus('Recherche Lyrics.ovh…');
  if (resultsHost) resultsHost.innerHTML = '';

  try {
    const data = await post(searchUrl, {_token: token, query});
    renderResults(data.results || []);
    setStatus((data.results || []).length ? `${data.results.length} résultat(s).` : 'Aucun résultat.');
  } catch (error) {
    console.error('Lyrics.ovh search failed', error);
    setStatus('Recherche Lyrics.ovh impossible.', true);
  } finally {
    button.disabled = false;
  }
}

button?.addEventListener('click', search);

input?.addEventListener('input', scheduleAutocomplete);

input?.addEventListener('keydown', event => {
  const box = autocompleteBox();
  const items = box ? Array.from(box.querySelectorAll('[data-lyrics-ovh-autocomplete-item]')) : [];

  if (event.key === 'ArrowDown' && items.length) {
    event.preventDefault();
    activateAutocomplete(items, autocompleteIndex + 1);
    return;
  }

  if (event.key === 'ArrowUp' && items.length) {
    event.preventDefault();
    activateAutocomplete(items, autocompleteIndex <= 0 ? 0 : autocompleteIndex - 1);
    return;
  }

  if (event.key === 'Escape') {
    closeAutocomplete();
    return;
  }

  if (event.key === 'Enter') {
    event.preventDefault();
    if (autocompleteIndex >= 0 && items[autocompleteIndex]) {
      chooseAutocomplete(items[autocompleteIndex]);
    } else {
      closeAutocomplete();
      search();
    }
  }
});

autocompleteBox()?.addEventListener('click', event => {
  const item = event.target.closest('[data-lyrics-ovh-autocomplete-item]');
  if (item) chooseAutocomplete(item);
});

document.addEventListener('click', event => {
  if (!root.contains(event.target)) closeAutocomplete();
});

resultsHost?.addEventListener('click', async event => {
  const useButton = event.target.closest('[data-lyrics-ovh-use]');
  if (!useButton) return;

  const artist = String(useButton.dataset.artist || '');
  const title = String(useButton.dataset.title || '');
  useButton.disabled = true;
  setStatus(`Chargement de « ${title} »…`);

  try {
    const data = await post(importUrl, {_token: token, artist, title});
    source.value = String(data.text || '');
    source.dispatchEvent(new Event('input', {bubbles:true}));
    setStatus(`Paroles chargées : ${data.artist} — ${data.title}.`);
    setTimeout(() => location.reload(), 250);
  } catch (error) {
    console.error('Lyrics.ovh import failed', error);
    if (error.code === 'lyrics_not_found') {
      setStatus('Lyrics.ovh ne fournit pas les paroles pour ce résultat.', true);
    } else {
      setStatus('Impossible de charger ces paroles.', true);
    }
  } finally {
    useButton.disabled = false;
  }
});
})();
