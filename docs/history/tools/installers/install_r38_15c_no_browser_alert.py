#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else r"H:\\EZScore_v1").resolve()
JS = ROOT / "public/assets/js/lyrics-history-r38-15.js"
CSS = ROOT / "public/assets/css/lyrics-history-r38-15.css"

MODAL_CODE = r'''
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
'''

CSS_CODE = r'''
.ez-modal-backdrop {
    position: fixed;
    inset: 0;
    z-index: 10000;
    display: grid;
    place-items: center;
    padding: 24px;
    background: rgba(0, 0, 0, .62);
}
.ez-modal {
    width: min(480px, 100%);
    border: 1px solid rgba(255,255,255,.14);
    border-radius: 14px;
    padding: 20px;
    background: #151a20;
    box-shadow: 0 24px 80px rgba(0,0,0,.5);
}
.ez-modal p { margin: 0 0 18px; line-height: 1.45; }
.ez-modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
}
'''

def main() -> int:
    if not JS.is_file() or not CSS.is_file():
        raise RuntimeError("R38.15 history assets missing")

    js = JS.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")

    if "function ezConfirm(" not in js:
        anchor = '''function setFeedback(text, error = false) {
  if (!feedback) return;
  feedback.textContent = text || '';
  feedback.classList.toggle('is-error', !!error);
}
'''
        if anchor not in js:
            raise RuntimeError("JS anchor not found")
        js = js.replace(anchor, anchor + MODAL_CODE, 1)

    old_restore = "    if (!id || !confirm('Restaurer cette version complète des paroles ?')) return;\n"
    new_restore = "    if (!id || !(await ezConfirm('Restaurer cette version complète des paroles ?', 'Restaurer'))) return;\n"
    if old_restore in js:
        js = js.replace(old_restore, new_restore, 1)

    old_delete = "    if (!id || deleteButton.disabled || !confirm('Jeter définitivement cette sauvegarde ?')) return;\n"
    new_delete = "    if (!id || deleteButton.disabled || !(await ezConfirm('Jeter définitivement cette sauvegarde ?', 'Jeter'))) return;\n"
    if old_delete in js:
        js = js.replace(old_delete, new_delete, 1)

    if "confirm(" in js or "alert(" in js or "prompt(" in js:
        raise RuntimeError("A native browser dialog remains in lyrics-history-r38-15.js")

    if ".ez-modal-backdrop" not in css:
        css += "\n" + CSS_CODE

    JS.write_text(js, encoding="utf-8", newline="\n")
    CSS.write_text(css, encoding="utf-8", newline="\n")
    print("R38_15C_NO_BROWSER_ALERT_INSTALL_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
