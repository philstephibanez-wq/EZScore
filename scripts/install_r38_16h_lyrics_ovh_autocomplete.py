#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else r"H:\EZScore_v1").resolve()
JS = ROOT / "public/assets/js/lyrics-ovh-r38-16.js"
CSS = ROOT / "public/assets/css/lyrics-ovh-r38-16.css"
TEMPLATE = ROOT / "templates/song/lyricslab.html.twig"

AUTOCOMPLETE_JS = 'let autocompleteTimer = null;\nlet autocompleteAbort = null;\nlet autocompleteIndex = -1;\n\nfunction autocompleteBox() {\n  return root.querySelector(\'[data-lyrics-ovh-autocomplete]\');\n}\n\nfunction closeAutocomplete() {\n  const box = autocompleteBox();\n  if (box) {\n    box.innerHTML = \'\';\n    box.hidden = true;\n  }\n  autocompleteIndex = -1;\n}\n\nfunction renderAutocomplete(results) {\n  const box = autocompleteBox();\n  if (!box) return;\n\n  const items = (Array.isArray(results) ? results : [])\n    .filter(item => item.available)\n    .slice(0, 6);\n\n  if (!items.length) {\n    closeAutocomplete();\n    return;\n  }\n\n  box.innerHTML = items.map((item, index) => `\n    <button type="button"\n            class="lyrics-ovh-autocomplete-item"\n            data-lyrics-ovh-autocomplete-item\n            data-index="${index}"\n            data-artist="${esc(item.artist)}"\n            data-title="${esc(item.title)}">\n      <span class="lyrics-ovh-autocomplete-title">${esc(item.title)}</span>\n      <span class="lyrics-ovh-autocomplete-artist">${esc(item.artist)}</span>\n    </button>\n  `).join(\'\');\n\n  box.hidden = false;\n  autocompleteIndex = -1;\n}\n\nasync function autocompleteSearch() {\n  const query = String(input?.value || \'\').trim();\n\n  if (query.length < 2) {\n    closeAutocomplete();\n    return;\n  }\n\n  if (autocompleteAbort) {\n    autocompleteAbort.abort();\n  }\n  autocompleteAbort = new AbortController();\n\n  try {\n    const response = await fetch(searchUrl, {\n      method: \'POST\',\n      credentials: \'same-origin\',\n      headers: {\'Content-Type\':\'application/json\', \'Accept\':\'application/json\'},\n      body: JSON.stringify({_token: token, query}),\n      signal: autocompleteAbort.signal\n    });\n\n    const data = await response.json().catch(() => ({}));\n    if (!response.ok) {\n      throw new Error(data.error || `http_${response.status}`);\n    }\n\n    renderAutocomplete(data.results || []);\n  } catch (error) {\n    if (error.name !== \'AbortError\') {\n      console.error(\'Lyrics.ovh autocomplete failed\', error);\n      closeAutocomplete();\n    }\n  }\n}\n\nfunction scheduleAutocomplete() {\n  clearTimeout(autocompleteTimer);\n  autocompleteTimer = setTimeout(autocompleteSearch, 300);\n}\n\nfunction activateAutocomplete(items, index) {\n  autocompleteIndex = Math.max(0, Math.min(items.length - 1, index));\n  items.forEach((item, itemIndex) => {\n    item.classList.toggle(\'is-active\', itemIndex === autocompleteIndex);\n  });\n  items[autocompleteIndex]?.scrollIntoView({block:\'nearest\'});\n}\n\nfunction chooseAutocomplete(item) {\n  if (!item) return;\n\n  const artist = String(item.dataset.artist || \'\').trim();\n  const title = String(item.dataset.title || \'\').trim();\n\n  input.value = `${artist} ${title}`.trim();\n  closeAutocomplete();\n  search();\n}\n'
CSS_ADD = '\n/* R38.16h - Lyrics.ovh live autocomplete */\n.lyrics-ovh-toolbar {\n    position: relative;\n}\n.lyrics-ovh-autocomplete {\n    position: absolute;\n    z-index: 60;\n    top: calc(100% + 6px);\n    left: 0;\n    width: min(540px, 72vw);\n    max-height: 320px;\n    overflow-y: auto;\n    border: 1px solid rgba(255,255,255,.14);\n    border-radius: 10px;\n    background: #111820;\n    box-shadow: 0 18px 46px rgba(0,0,0,.42);\n}\n.lyrics-ovh-autocomplete[hidden] {\n    display: none;\n}\n.lyrics-ovh-autocomplete-item {\n    display: grid;\n    grid-template-columns: minmax(0, 1fr);\n    gap: 2px;\n    width: 100%;\n    padding: 10px 12px;\n    border: 0;\n    border-bottom: 1px solid rgba(255,255,255,.07);\n    border-radius: 0;\n    text-align: left;\n    background: transparent;\n}\n.lyrics-ovh-autocomplete-item:last-child {\n    border-bottom: 0;\n}\n.lyrics-ovh-autocomplete-item:hover,\n.lyrics-ovh-autocomplete-item.is-active {\n    background: rgba(255,255,255,.08);\n}\n.lyrics-ovh-autocomplete-title {\n    font-weight: 700;\n    overflow: hidden;\n    text-overflow: ellipsis;\n    white-space: nowrap;\n}\n.lyrics-ovh-autocomplete-artist {\n    opacity: .72;\n    font-size: .86rem;\n    overflow: hidden;\n    text-overflow: ellipsis;\n    white-space: nowrap;\n}\n'

def main() -> int:
    for path in (JS, CSS, TEMPLATE):
        if not path.is_file():
            raise RuntimeError(f"Missing prerequisite: {path}")

    js = JS.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")
    template = TEMPLATE.read_text(encoding="utf-8")

    if 'data-lyrics-ovh-autocomplete' not in template:
        anchor = '                       placeholder="Titre ou artiste">'
        if anchor not in template:
            raise RuntimeError("Lyrics.ovh input anchor not found")
        template = template.replace(
            anchor,
            anchor + '\n                <div class="lyrics-ovh-autocomplete" data-lyrics-ovh-autocomplete hidden></div>',
            1,
        )

    if "function autocompleteSearch()" not in js:
        anchor = "async function search() {\n"
        if anchor not in js:
            raise RuntimeError("Lyrics.ovh search() anchor not found")
        js = js.replace(anchor, AUTOCOMPLETE_JS + "\n" + anchor, 1)

    old_handler = """button?.addEventListener('click', search);
input?.addEventListener('keydown', event => {
  if (event.key === 'Enter') {
    event.preventDefault();
    search();
  }
});
"""
    new_handler = """button?.addEventListener('click', search);

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
"""
    if old_handler in js:
        js = js.replace(old_handler, new_handler, 1)
    elif "input?.addEventListener('input', scheduleAutocomplete);" not in js:
        raise RuntimeError("Lyrics.ovh keyboard handler anchor not found")

    if '.lyrics-ovh-autocomplete' not in css:
        css += "\n" + CSS_ADD

    template, js_count = re.subn(
        r'(/assets/js/lyrics-ovh-r38-16\.js\?v=)[^"]+',
        r'\g<1>20260929r38_16h',
        template,
        count=1,
    )
    template, css_count = re.subn(
        r'(/assets/css/lyrics-ovh-r38-16\.css\?v=)[^"]+',
        r'\g<1>20260929r38_16h',
        template,
        count=1,
    )

    if js_count != 1 or css_count != 1:
        raise RuntimeError("Lyrics.ovh asset reference missing")

    JS.write_text(js, encoding="utf-8", newline="\n")
    CSS.write_text(css, encoding="utf-8", newline="\n")
    TEMPLATE.write_text(template, encoding="utf-8", newline="\n")

    print("R38_16H_LYRICS_OVH_AUTOCOMPLETE_INSTALL_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
