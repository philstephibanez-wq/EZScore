(() => {
'use strict';

const root = document.querySelector('[data-lyrics-history]');
const source = document.querySelector('[data-lyrics-source]');
if (!root || !source) return;

const listUrl = root.dataset.listUrl || '';
const saveUrl = root.dataset.saveUrl || '';
const restoreTemplate = root.dataset.restoreUrlTemplate || '';
const deleteTemplate = root.dataset.deleteUrlTemplate || '';
const token = root.dataset.token || '';
const form = root.querySelector('[data-lyrics-history-save]');
const list = root.querySelector('[data-lyrics-history-list]');
const count = root.querySelector('[data-lyrics-history-count]');
const feedback = root.querySelector('[data-lyrics-history-feedback]');
const sourceType = root.querySelector('[name="lyrics_history_source_type"]');
const comment = root.querySelector('[name="lyrics_history_comment"]');

const sourceLabels = {
  manual: 'Manuel',
  lyrics_ovh: 'Lyrics.ovh',
  whisper: 'Whisper',
  other: 'Autre',
  restore: 'Restauration',
  legacy: 'Version initiale'
};

function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, c => ({
    '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#039;'
  }[c]));
}

function endpoint(template, id) {
  return template.replace('__REVISION__', String(id));
}

function setFeedback(text, error = false) {
  if (!feedback) return;
  feedback.textContent = text || '';
  feedback.classList.toggle('is-error', !!error);
}

function ezConfirm(message, confirmLabel = 'Confirmer') {
  return new Promise(resolve => {
    const backdrop = document.createElement('div');
    backdrop.className = 'ez-modal-backdrop';
    backdrop.innerHTML = `
      <div class="ez-modal" role="dialog" aria-modal="true" aria-label="Confirmation">
        <p>${esc(message)}</p>
        <div class="ez-modal-actions">
          <button type="button" class="ez-modal-cancel">Annuler</button>
          <button type="button" class="primary ez-modal-confirm">${esc(confirmLabel)}</button>
        </div>
      </div>`;

    const close = result => {
      document.removeEventListener('keydown', onKey);
      backdrop.remove();
      resolve(result);
    };
    const onKey = event => {
      if (event.key === 'Escape') close(false);
    };

    backdrop.querySelector('.ez-modal-cancel')?.addEventListener('click', () => close(false));
    backdrop.querySelector('.ez-modal-confirm')?.addEventListener('click', () => close(true));
    backdrop.addEventListener('click', event => {
      if (event.target === backdrop) close(false);
    });
    document.addEventListener('keydown', onKey);

    document.body.appendChild(backdrop);
    backdrop.querySelector('.ez-modal-confirm')?.focus();
  });
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

function render(revisions) {
  if (count) count.textContent = String(revisions.length);
  if (!list) return;

  if (!revisions.length) {
    list.innerHTML = '<p class="page-note">Aucune sauvegarde pour le moment.</p>';
    return;
  }

  list.innerHTML = revisions.map(revision => {
    const when = new Date(revision.created_at);
    const date = Number.isNaN(when.getTime())
      ? revision.created_at
      : when.toLocaleString('fr-FR', {dateStyle:'short', timeStyle:'short'});
    const sourceName = sourceLabels[revision.source_type] || revision.source_type || 'Autre';
    const author = revision.created_by ? ` · ${esc(revision.created_by)}` : '';
    const current = revision.is_current
      ? '<span class="lyrics-history-current">Actuelle</span>'
      : '';
    const commentText = revision.comment
      ? `<div class="lyrics-history-comment">${esc(revision.comment)}</div>`
      : '';
    const deleteDisabled = revision.is_current ? 'disabled title="La version courante ne peut pas être jetée."' : '';

    return `
      <article class="lyrics-history-row" data-revision-id="${Number(revision.id)}">
        <div class="lyrics-history-meta">
          <strong>${esc(sourceName)}</strong>
          ${current}
          <span>${esc(date)}${author}</span>
          ${commentText}
        </div>
        <div class="lyrics-history-row-actions">
          <button type="button" data-restore="${Number(revision.id)}">Restaurer</button>
          <button type="button" class="lyrics-history-trash" data-delete="${Number(revision.id)}" ${deleteDisabled} aria-label="Jeter cette sauvegarde">🗑</button>
        </div>
      </article>`;
  }).join('');
}

async function load() {
  if (!listUrl) return;
  try {
    const response = await fetch(listUrl, {
      credentials:'same-origin',
      headers:{Accept:'application/json'},
      cache:'no-store'
    });
    if (!response.ok) throw new Error(`http_${response.status}`);
    const data = await response.json();
    render(Array.isArray(data.revisions) ? data.revisions : []);
  } catch (error) {
    console.error('Lyrics history load failed', error);
    setFeedback('Impossible de charger l’historique.', true);
  }
}

form?.addEventListener('submit', async event => {
  event.preventDefault();
  setFeedback('Sauvegarde…');
  try {
    await post(saveUrl, {
      _token: token,
      text: source.value,
      source_type: sourceType?.value || 'manual',
      comment: comment?.value || ''
    });
    if (comment) comment.value = '';
    setFeedback('Version sauvegardée.');
    document.dispatchEvent(new CustomEvent('ezscore:lyrics-history-saved'));
    await load();
  } catch (error) {
    console.error('Lyrics history save failed', error);
    setFeedback('Échec de la sauvegarde de version.', true);
  }
});

list?.addEventListener('click', async event => {
  const restoreButton = event.target.closest('[data-restore]');
  if (restoreButton) {
    const id = Number(restoreButton.dataset.restore);
    if (!id || !(await ezConfirm('Restaurer cette version complète des paroles ?', 'Restaurer'))) return;
    restoreButton.disabled = true;
    try {
      const data = await post(endpoint(restoreTemplate, id), {_token: token});
      source.value = String(data.text ?? '');
      source.dispatchEvent(new Event('input', {bubbles:true}));
      setFeedback('Version restaurée.');
      document.dispatchEvent(new CustomEvent('ezscore:lyrics-history-restored'));
      await load();
    } catch (error) {
      console.error('Lyrics history restore failed', error);
      setFeedback('Échec de la restauration.', true);
    } finally {
      restoreButton.disabled = false;
    }
    return;
  }

  const deleteButton = event.target.closest('[data-delete]');
  if (deleteButton) {
    const id = Number(deleteButton.dataset.delete);
    if (!id || deleteButton.disabled || !(await ezConfirm('Jeter définitivement cette sauvegarde ?', 'Jeter'))) return;
    deleteButton.disabled = true;
    try {
      await post(endpoint(deleteTemplate, id), {_token: token});
      setFeedback('Sauvegarde supprimée.');
      await load();
    } catch (error) {
      console.error('Lyrics history delete failed', error);
      if (error.code === 'current_revision') {
        setFeedback('La version courante ne peut pas être jetée.', true);
      } else {
        setFeedback('Échec de la suppression.', true);
      }
    } finally {
      deleteButton.disabled = false;
    }
  }
});

load();
})();
