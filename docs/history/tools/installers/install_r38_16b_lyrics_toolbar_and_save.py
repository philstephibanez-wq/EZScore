#!/usr/bin/env python3
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else r"H:\EZScore_v1").resolve()
TEMPLATE = ROOT / "templates/song/lyricslab.html.twig"
CSS_OVH = ROOT / "public/assets/css/lyrics-ovh-r38-16.css"
CSS_HISTORY = ROOT / "public/assets/css/lyrics-history-r38-15.css"
SEARCH_TOOLBAR = '            <div class="lyrics-ovh-toolbar"\n                 data-lyrics-ovh\n                 data-search-url="{{ path(\'app_song_lyrics_ovh_search\', {\'_locale\': app.request.locale, id: song.id}) }}"\n                 data-import-url="{{ path(\'app_song_lyrics_ovh_import\', {\'_locale\': app.request.locale, id: song.id}) }}"\n                 data-token="{{ csrf_token(\'song_lyrics_ovh_\' ~ song.id) }}">\n                <input type="search"\n                       data-lyrics-ovh-query\n                       value="{{ (song.artist ~ \' \' ~ song.title)|trim }}"\n                       maxlength="180"\n                       autocomplete="off"\n                       placeholder="Titre ou artiste">\n                <button type="button" data-lyrics-ovh-search>Chercher les paroles</button>\n            </div>\n'
RESULTS_BLOCK = '    <div class="lyrics-ovh-status" data-lyrics-ovh-status></div>\n    <div class="lyrics-ovh-results" data-lyrics-ovh-results></div>\n'

def main() -> int:
    if not TEMPLATE.is_file():
        raise RuntimeError("Missing LyricsLab template")

    text = TEMPLATE.read_text(encoding="utf-8")

    text = re.sub(
        r'\n\s*<section class="lyrics-ovh-search"\b.*?</section>\s*',
        '\n',
        text,
        count=1,
        flags=re.S,
    )

    if 'class="lyrics-ovh-toolbar"' not in text:
        actions_open = '<div class="chordslab-prompter-actions lyricslab-actions">'
        pos = text.find(actions_open)
        if pos < 0:
            raise RuntimeError("LyricsLab actions container not found")
        insert_at = pos + len(actions_open)
        text = text[:insert_at] + "\n" + SEARCH_TOOLBAR + text[insert_at:]

    if 'data-lyrics-ovh-results' not in text:
        textarea_end = text.find('</textarea>')
        if textarea_end < 0:
            raise RuntimeError("Lyrics textarea not found")
        textarea_end += len('</textarea>')
        text = text[:textarea_end] + "\n" + RESULTS_BLOCK + text[textarea_end:]

    details = re.search(
        r'(?P<whole><details class="lyrics-history"(?P<attrs>[^>]*)>(?P<body>.*?)</details>)',
        text,
        flags=re.S,
    )

    if details and 'data-lyrics-history-savebar' not in text:
        body = details.group('body')
        form = re.search(
            r'(?P<form><form class="lyrics-history-editor"[^>]*data-lyrics-history-save[^>]*>.*?</form>)',
            body,
            flags=re.S,
        )
        if not form:
            raise RuntimeError("History save form not found")

        form_html = form.group('form')
        body_without_form = body[:form.start()] + body[form.end():]

        attrs = details.group('attrs')
        attrs_no_root = re.sub(r'\sdata-lyrics-history(?=\s|$)', '', attrs, count=1)

        data_attrs = {}
        for attr in ['data-list-url','data-save-url','data-restore-url-template','data-delete-url-template','data-token']:
            m = re.search(rf'\s{attr}="([^"]*)"', attrs_no_root)
            if not m:
                raise RuntimeError(f"Missing {attr} on history details")
            data_attrs[attr] = m.group(1)
            attrs_no_root = re.sub(rf'\s{attr}="[^"]*"', '', attrs_no_root, count=1)

        lines = ['<div class="lyrics-history-shell" data-lyrics-history']
        for key, value in data_attrs.items():
            lines.append(f'     {key}="{value}"')
        lines[-1] += '>'
        lines += [
            '    <div class="lyrics-history-savebar" data-lyrics-history-savebar>',
            form_html,
            '    </div>',
            f'    <details class="lyrics-history"{attrs_no_root}>',
            body_without_form,
            '    </details>',
            '</div>',
        ]
        replacement = "\n".join(lines)
        text = text[:details.start()] + replacement + text[details.end():]

        shell_start = text.find('<div class="lyrics-history-shell"')
        details_end = text.find('</details>', shell_start)
        shell_end = text.find('</div>', details_end)
        if shell_start < 0 or details_end < 0 or shell_end < 0:
            raise RuntimeError("Generated history shell not found")
        shell_end += len('</div>')
        shell_html = text[shell_start:shell_end]
        text = text[:shell_start] + text[shell_end:]

        results_pos = text.find('data-lyrics-ovh-results')
        if results_pos >= 0:
            anchor_end = text.find('</div>', results_pos)
            if anchor_end < 0:
                raise RuntimeError("Results block end not found")
            anchor_end += len('</div>')
        else:
            anchor_end = text.find('</textarea>') + len('</textarea>')

        text = text[:anchor_end] + "\n\n" + shell_html + text[anchor_end:]

    text = re.sub(r'(/assets/js/lyrics-ovh-r38-16\.js\?v=)[^"]+', r'\g<1>20260929r38_16b', text, count=1)
    text = re.sub(r'(/assets/css/lyrics-ovh-r38-16\.css\?v=)[^"]+', r'\g<1>20260929r38_16b', text, count=1)
    text = re.sub(r'(/assets/css/lyrics-history-r38-15\.css\?v=)[^"]+', r'\g<1>20260929r38_16b', text, count=1)

    TEMPLATE.write_text(text, encoding="utf-8", newline="\n")

    if CSS_OVH.is_file():
        css = CSS_OVH.read_text(encoding="utf-8")
        if '.lyrics-ovh-toolbar' not in css:
            css += """
.lyrics-ovh-toolbar {
    display: flex;
    gap: 8px;
    align-items: center;
}
.lyrics-ovh-toolbar input {
    width: min(320px, 32vw);
    min-height: 42px;
}
@media (max-width: 980px) {
    .chordslab-prompter-actions.lyricslab-actions {
        flex-wrap: wrap;
    }
    .lyrics-ovh-toolbar {
        order: 2;
        width: 100%;
    }
    .lyrics-ovh-toolbar input {
        flex: 1 1 auto;
        width: auto;
        min-width: 180px;
    }
}
"""
            CSS_OVH.write_text(css, encoding="utf-8", newline="\n")

    if CSS_HISTORY.is_file():
        css = CSS_HISTORY.read_text(encoding="utf-8")
        if '.lyrics-history-savebar' not in css:
            css += """
.lyrics-history-savebar {
    margin-top: 12px;
}
.lyrics-history-savebar .lyrics-history-editor {
    margin: 0;
}
.lyrics-history-shell > .lyrics-history {
    margin-top: 14px;
}
"""
            CSS_HISTORY.write_text(css, encoding="utf-8", newline="\n")

    print("R38_16B_LYRICS_TOOLBAR_AND_SAVE_INSTALL_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
