#!/usr/bin/env python3
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else r"H:\EZScore_v1").resolve()
HISTORY_MARKUP = '<details class="lyrics-history"\n             data-lyrics-history\n             data-list-url="{{ path(\'app_song_lyrics_history\', {\'_locale\': app.request.locale, id: song.id}) }}"\n             data-save-url="{{ path(\'app_song_lyrics_history_save\', {\'_locale\': app.request.locale, id: song.id}) }}"\n             data-restore-url-template="{{ path(\'app_song_lyrics_history_restore\', {\'_locale\': app.request.locale, id: song.id, revisionId:999999})|replace({\'999999\':\'__REVISION__\'}) }}"\n             data-delete-url-template="{{ path(\'app_song_lyrics_history_delete\', {\'_locale\': app.request.locale, id: song.id, revisionId:999999})|replace({\'999999\':\'__REVISION__\'}) }}"\n             data-token="{{ csrf_token(\'song_lyrics_history_\' ~ song.id) }}">\n        <summary>Historique des paroles (<span data-lyrics-history-count>0</span>)</summary>\n\n        <form class="lyrics-history-editor" data-lyrics-history-save>\n            <label>\n                Source\n                <select name="lyrics_history_source_type">\n                    <option value="manual">Manuel</option>\n                    <option value="lyrics_ovh">Lyrics.ovh</option>\n                    <option value="whisper">Whisper</option>\n                    <option value="other">Autre</option>\n                </select>\n            </label>\n\n            <label>\n                Commentaire personnel\n                <input type="text"\n                       name="lyrics_history_comment"\n                       maxlength="1000"\n                       placeholder="Ex. : paroles cherchées avec OVH">\n            </label>\n\n            <button type="submit">Sauvegarder cette version</button>\n        </form>\n\n        <div class="lyrics-history-feedback" data-lyrics-history-feedback></div>\n        <div class="lyrics-history-list" data-lyrics-history-list>\n            <p class="page-note">Chargement de l’historique…</p>\n        </div>\n    </details>\n\n    '

def read(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"Missing prerequisite: {path}")
    return path.read_text(encoding="utf-8")

def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")

def patch_controller(text: str) -> str:
    method_start = text.find("public function extractLyrics(")
    if method_start < 0:
        raise RuntimeError("SongLabController: extractLyrics() method not found")

    signature_end = text.find("): Response", method_start)
    if signature_end < 0:
        raise RuntimeError("SongLabController: end of extractLyrics() signature not found")

    signature = text[method_start:signature_end]

    if "LyricsSourceHistoryService $lyricsHistory" not in signature:
        stripped = signature.rstrip()
        trailing = signature[len(stripped):]
        if not stripped.endswith(","):
            stripped += ","
        signature_new = (
            stripped
            + "\n    \\App\\Service\\LyricsSourceHistoryService $lyricsHistory,"
            + trailing
        )
        text = text[:method_start] + signature_new + text[signature_end:]
        method_start = text.find("public function extractLyrics(")
        signature_end = text.find("): Response", method_start)

    marker = "Sauvegarde automatique avant extraction Whisper."
    if marker not in text:
        next_route = text.find("#[Route(", signature_end + len("): Response"))
        method_end = next_route if next_route >= 0 else len(text)
        block = text[method_start:method_end]

        queue_pattern = re.compile(
            r"(?m)^(?P<indent>[ \t]*)\$jobs->queue\(\s*\$song\s*,\s*\$user\s*,\s*['\"]extract['\"]\s*\)\s*;\s*$"
        )
        match = queue_pattern.search(block)
        if not match:
            raise RuntimeError("SongLabController: extract queue call not found in extractLyrics()")

        indent = match.group("indent")
        injection = (
            f"{indent}$lyricsHistory->archiveCurrentIfChanged(\n"
            f"{indent}    $song,\n"
            f"{indent}    $user,\n"
            f"{indent}    'manual',\n"
            f"{indent}    'Sauvegarde automatique avant extraction Whisper.',\n"
            f"{indent});\n\n"
            f"{match.group(0)}"
        )
        block = block[:match.start()] + injection + block[match.end():]
        text = text[:method_start] + block + text[method_end:]

    return text

def patch_template(text: str) -> str:
    if "lyrics-history-r38-15.css" not in text:
        anchor = '<link rel="stylesheet" href="/assets/css/lyricslab-r37.css?v=20260928r38_2">'
        if anchor not in text:
            raise RuntimeError("lyricslab.html.twig: stylesheet anchor not found")
        text = text.replace(
            anchor,
            anchor + '\n<link rel="stylesheet" href="/assets/css/lyrics-history-r38-15.css?v=20260929r38_15b">',
            1,
        )

    if "data-lyrics-history" not in text:
        progress_anchor = '<div class="chord-analysis-progress"'
        pos = text.find(progress_anchor)
        if pos < 0:
            raise RuntimeError("lyricslab.html.twig: progress block anchor not found")
        text = text[:pos] + HISTORY_MARKUP + text[pos:]

    if "lyrics-history-r38-15.js" not in text:
        js_block = text.find("{% block javascripts %}")
        if js_block < 0:
            raise RuntimeError("lyricslab.html.twig: javascripts block not found")
        js_end = text.find("{% endblock %}", js_block)
        if js_end < 0:
            raise RuntimeError("lyricslab.html.twig: javascripts endblock not found")
        text = (
            text[:js_end]
            + '<script src="/assets/js/lyrics-history-r38-15.js?v=20260929r38_15b"></script>\n'
            + text[js_end:]
        )

    return text

def patch_routes(text: str) -> str:
    if "LyricsHistoryController.php" in text:
        return text

    anchor = """localized_song_labs:
    resource: ../src/Controller/SongLabController.php
    type: attribute
    prefix:
        fr: /fr
        en: /en
"""
    if anchor not in text:
        raise RuntimeError("config/routes.yaml: localized_song_labs anchor not found")

    addition = anchor + """
localized_lyrics_history:
    resource: ../src/Controller/LyricsHistoryController.php
    type: attribute
    prefix:
        fr: /fr
        en: /en
"""
    return text.replace(anchor, addition, 1)

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
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError("R38.15 payload incomplete:\n" + "\n".join(missing))

    controller_new = patch_controller(controller_text)
    template_new = patch_template(template_text)
    routes_new = patch_routes(routes_text)

    write(controller, controller_new)
    write(template, template_new)
    write(routes, routes_new)

    print("R38_15B_REPAIR_INSTALL_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
