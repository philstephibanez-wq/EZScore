(() => {
  'use strict';

  const openButton = document.querySelector('[data-session-delete-open]');
  const dialog = document.querySelector('[data-session-delete-dialog]');
  const cancelButton = dialog?.querySelector('[data-session-delete-cancel]');

  if (!openButton || !dialog) return;

  openButton.addEventListener('click', () => {
    if (typeof dialog.showModal === 'function') {
      dialog.showModal();
      return;
    }
    dialog.setAttribute('open', '');
  });

  cancelButton?.addEventListener('click', () => {
    if (typeof dialog.close === 'function') {
      dialog.close();
      return;
    }
    dialog.removeAttribute('open');
  });

  dialog.addEventListener('click', (event) => {
    if (event.target !== dialog) return;
    if (typeof dialog.close === 'function') {
      dialog.close();
    } else {
      dialog.removeAttribute('open');
    }
  });
})();
