#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else r"H:\EZScore_v1").resolve()


def read(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"Missing prerequisite: {path}")
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def patch_routes(text: str) -> str:
    if "LyricsOvhController.php" in text:
        return text

    history_anchor = """localized_lyrics_history:
    resource: ../src/Controller/LyricsHistoryController.php
    type: attribute
    prefix:
        fr: /fr
        en: /en
"""
    if history_anchor in text:
        addition = history_anchor + """
localized_lyrics_ovh:
    resource: ../src/Controller/LyricsOvhController.php
    type: attribute
    prefix:
        fr: /fr
        en: /en
"""
        return text.replace(history_anchor, addition, 1)

    labs_anchor = """localized_song_labs:
    resource: ../src/Controller/SongLabController.php
    type: attribute
    prefix:
        fr: /fr
        en: /en
"""
    if labs_anchor not in text:
        raise RuntimeError("config/routes.yaml: localized_song_labs anchor not found")

    addition = labs_anchor + """
localized_lyrics_ovh:
    resource: ../src/Controller/LyricsOvhController.php
    type: attribute
    prefix:
        fr: /fr
        en: /en
"""
    return text.replace(labs_anchor, addition, 1)


def patch_template(text: str) -> str:
    if "lyrics-ovh-r38-16.css" not in text:
        anchor = '<link rel="stylesheet" href="/assets/css/lyricslab-r37.css?v=20260928r38_2">'
        if anchor not in text:
            raise RuntimeError("lyricslab.html.twig: stylesheet anchor not found")
        text = text.replace(
            anchor,
            anchor + '\n<link rel="stylesheet" href="/assets/css/lyrics-ovh-r38-16.css?v=20260929r38_16">',
            1,
        )

    if "data-lyrics-ovh" not in text:
        textarea_end = "</textarea>"
        pos = text.find(textarea_end)
        if pos < 0:
            raise RuntimeError("lyricslab.html.twig: lyrics textarea end not found")
        pos += len(textarea_end)

        block = '''

    <section class="lyrics-ovh-search"
             data-lyrics-ovh
             data-search-url="{{ path('app_song_lyrics_ovh_search', {'_locale': app.request.locale, id: song.id}) }}"
             data-import-url="{{ path('app_song_lyrics_ovh_import', {'_locale': app.request.locale, id: song.id}) }}"
             data-token="{{ csrf_token('song_lyrics_ovh_' ~ song.id) }}">
        <div class="lyrics-ovh-search-head">
            <input type="search"
                   data-lyrics-ovh-query
                   value="{{ (song.artist ~ ' ' ~ song.title)|trim }}"
                   maxlength="180"
                   autocomplete="off"
                   placeholder="Titre, artiste ou les deux">
            <button type="button" data-lyrics-ovh-search>Chercher les paroles</button>
        </div>
        <div class="lyrics-ovh-status" data-lyrics-ovh-status></div>
        <div class="lyrics-ovh-results" data-lyrics-ovh-results></div>
    </section>
'''
        text = text[:pos] + block + text[pos:]

    if "lyrics-ovh-r38-16.js" not in text:
        js_block = text.find("{% block javascripts %}")
        if js_block < 0:
            raise RuntimeError("lyricslab.html.twig: javascript block not found")
        js_end = text.find("{% endblock %}", js_block)
        if js_end < 0:
            raise RuntimeError("lyricslab.html.twig: javascript endblock not found")
        text = text[:js_end] + '<script src="/assets/js/lyrics-ovh-r38-16.js?v=20260929r38_16"></script>\n' + text[js_end:]

    return text


def main() -> int:
    routes = ROOT / "config/routes.yaml"
    template = ROOT / "templates/song/lyricslab.html.twig"

    required = [
        ROOT / "src/Service/LyricsOvhClient.php",
        ROOT / "src/Controller/LyricsOvhController.php",
        ROOT / "public/assets/js/lyrics-ovh-r38-16.js",
        ROOT / "public/assets/css/lyrics-ovh-r38-16.css",
        ROOT / "src/Service/LyricsSourceHistoryService.php",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError("R38.16 payload incomplete:\n" + "\n".join(missing))

    routes_new = patch_routes(read(routes))
    template_new = patch_template(read(template))

    write(routes, routes_new)
    write(template, template_new)

    print("R38_16_LYRICS_OVH_INSTALL_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
