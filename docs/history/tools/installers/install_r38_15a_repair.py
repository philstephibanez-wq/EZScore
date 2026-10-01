#!/usr/bin/env python3
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else r"H:\\EZScore_v1").resolve()

def read(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"Missing prerequisite: {path}")
    return path.read_text(encoding="utf-8")

def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")

def patch_controller(text: str) -> str:
    if "LyricsSourceHistoryService $lyricsHistory" not in text:
        pattern = re.compile(
            r"(public\s+function\s+extractLyrics\s*\(\s*"
            r"Song\s+\$song\s*,\s*"
            r"Request\s+\$request\s*,\s*"
            r"\\\\App\\\\Service\\\\SongLyricsJobService\s+\$jobs\s*,?)"
            r"(\s*\)\s*:\s*Response\s*\{)",
            re.S,
        )
        match = pattern.search(text)
        if not match:
            raise RuntimeError("SongLabController: extractLyrics() signature not found")
        prefix = match.group(1).rstrip()
        if not prefix.endswith(","):
            prefix += ","
        replacement = prefix + "\n    \\App\\Service\\LyricsSourceHistoryService $lyricsHistory," + match.group(2)
        text = text[:match.start()] + replacement + text[match.end():]

    marker = "Sauvegarde automatique avant extraction Whisper."
    if marker not in text:
        method_start = text.find("public function extractLyrics")
        if method_start < 0:
            raise RuntimeError("SongLabController: extractLyrics() method not found")
        next_method = text.find("#[Route(", method_start + 10)
        method_end = next_method if next_method >= 0 else len(text)
        block = text[method_start:method_end]
        queue_pattern = re.compile(
            r"(?m)^(?P<indent>[ \t]*)\$jobs->queue\(\$song\s*,\s*\$user\s*,\s*['\"]extract['\"]\s*\)\s*;\s*$"
        )
        match = queue_pattern.search(block)
        if not match:
            raise RuntimeError("SongLabController: Whisper extract queue call not found inside extractLyrics()")
        indent = match.group("indent")
        inject = (
            f"{indent}$lyricsHistory->archiveCurrentIfChanged(\n"
            f"{indent}    $song,\n"
            f"{indent}    $user,\n"
            f"{indent}    'manual',\n"
            f"{indent}    'Sauvegarde automatique avant extraction Whisper.',\n"
            f"{indent});\n\n"
            f"{match.group(0)}"
        )
        block = block[:match.start()] + inject + block[match.end():]
        text = text[:method_start] + block + text[method_end:]
    return text

def patch_template(text: str) -> str:
    if "lyrics-history-r38-15.css" not in text:
        anchor = '<link rel="stylesheet" href="/assets/css/lyricslab-r37.css?v=20260928r38_2">'
        if anchor not in text:
            raise RuntimeError("lyricslab.html.twig: stylesheet anchor not found")
        text = text.replace(anchor, anchor + '\n<link rel="stylesheet" href="/assets/css/lyrics-history-r38-15.css?v=20260929r38_15a">', 1)

    if "data-lyrics-history" not in text:
        progress_anchor = '<div class="chord-analysis-progress"'
        pos = text.find(progress_anchor)
        if pos < 0:
            raise RuntimeError("lyricslab.html.twig: analysis progress anchor not found")
        history = '''<details class="lyrics-history"
             data-lyrics-history
             data-list-url="{{ path('app_song_lyrics_history', {'_locale': app.request.locale, id: song.id}) }}"
             data-save-url="{{ path('app_song_lyrics_history_save', {'_locale': app.request.locale, id: song.id}) }}"
             data-restore-url-template="{{ path('app_song_lyrics_history_restore', {'_locale': app.request.locale, id: song.id, revisionId:999999})|replace({'999999':'__REVISION__'}) }}"
             data-delete-url-template="{{ path('app_song_lyrics_history_delete', {'_locale': app.request.locale, id: song.id, revisionId:999999})|replace({'999999':'__REVISION__'}) }}"
             data-token="{{ csrf_token('song_lyrics_history_' ~ song.id) }}">
        <summary>Historique des paroles (<span data-lyrics-history-count>0</span>)</summary>
        <form class="lyrics-history-editor" data-lyrics-history-save>
            <label>Source
                <select name="lyrics_history_source_type">
                    <option value="manual">Manuel</option>
                    <option value="lyrics_ovh">Lyrics.ovh</option>
                    <option value="whisper">Whisper</option>
                    <option value="other">Autre</option>
                </select>
            </label>
            <label>Commentaire personnel
                <input type="text" name="lyrics_history_comment" maxlength="1000" placeholder="Ex. : paroles cherchées avec OVH">
            </label>
            <button type="submit">Sauvegarder cette version</button>
        </form>
        <div class="lyrics-history-feedback" data-lyrics-history-feedback></div>
        <div class="lyrics-history-list" data-lyrics-history-list>
            <p class="page-note">Chargement de l’historique…</p>
        </div>
    </details>

    '''
        text = text[:pos] + history + text[pos:]

    if "lyrics-history-r38-15.js" not in text:
        js_block = text.find("{% block javascripts %}")
        if js_block < 0:
            raise RuntimeError("lyricslab.html.twig: javascripts block not found")
        end = text.find("{% endblock %}", js_block)
        if end < 0:
            raise RuntimeError("lyricslab.html.twig: javascripts endblock not found")
        text = text[:end] + '<script src="/assets/js/lyrics-history-r38-15.js?v=20260929r38_15a"></script>\n' + text[end:]
    return text

def patch_routes(text: str) -> str:
    if "LyricsHistoryController.php" in text:
        return text
    anchor = '''localized_song_labs:
    resource: ../src/Controller/SongLabController.php
    type: attribute
    prefix:
        fr: /fr
        en: /en
'''
    if anchor not in text:
        raise RuntimeError("config/routes.yaml: localized_song_labs anchor not found")
    block = anchor + '''
localized_lyrics_history:
    resource: ../src/Controller/LyricsHistoryController.php
    type: attribute
    prefix:
        fr: /fr
        en: /en
'''
    return text.replace(anchor, block, 1)

def main() -> int:
    controller = ROOT / "src/Controller/SongLabController.php"
    template = ROOT / "templates/song/lyricslab.html.twig"
    routes = ROOT / "config/routes.yaml"

    controller_text = read(controller)
    template_text = read(template)
    routes_text = read(routes)

    required = [
        ROOT / "src/Controller/LyricsHistoryController.php",
        ROOT / "src/Domain/Song/LyricsSourceRevision.php",
        ROOT / "src/Domain/Song/LyricsSourceRevisionRepository.php",
        ROOT / "src/Service/LyricsSourceHistoryService.php",
        ROOT / "public/assets/js/lyrics-history-r38-15.js",
        ROOT / "public/assets/css/lyrics-history-r38-15.css",
        ROOT / "migrations/Version20260929090000.php",
    ]
    missing = [str(p) for p in required if not p.is_file()]
    if missing:
        raise RuntimeError("R38.15 payload incomplete:\n" + "\n".join(missing))

    controller_new = patch_controller(controller_text)
    template_new = patch_template(template_text)
    routes_new = patch_routes(routes_text)

    write(controller, controller_new)
    write(template, template_new)
    write(routes, routes_new)

    print("R38_15A_REPAIR_INSTALL_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
