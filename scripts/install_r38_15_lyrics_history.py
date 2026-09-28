#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else r"H:\EZScore_v1").resolve()

def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one anchor, found {count} in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")

def main() -> int:
    controller = ROOT / "src/Controller/SongLabController.php"
    template = ROOT / "templates/song/lyricslab.html.twig"

    for path in (controller, template):
        if not path.is_file():
            raise SystemExit(f"Missing prerequisite: {path}")

    # Validate all anchors before writing anything.
    controller_text = controller.read_text(encoding="utf-8")
    template_text = template.read_text(encoding="utf-8")

    controller_sig = """public function extractLyrics(
    Song $song,
    Request $request,
    \\\\App\\\\Service\\\\SongLyricsJobService $jobs,
): Response {"""
    if controller_sig not in controller_text and "LyricsSourceHistoryService $lyricsHistory" not in controller_text:
        raise RuntimeError("SongLabController extractLyrics signature anchor not found")

    controller_queue = """    $jobs->queue($song, $user, 'extract');
"""
    if controller_queue not in controller_text and "Sauvegarde automatique avant extraction Whisper" not in controller_text:
        raise RuntimeError("SongLabController extraction queue anchor not found")

    style_anchor = '<link rel="stylesheet" href="/assets/css/lyricslab-r37.css?v=20260928r38_2">\n'
    if style_anchor not in template_text and "lyrics-history-r38-15.css" not in template_text:
        raise RuntimeError("LyricsLab stylesheet anchor not found")

    panel_anchor = """    <div class="chord-analysis-progress"
         data-lyrics-progress
"""
    if panel_anchor not in template_text and "data-lyrics-history" not in template_text:
        raise RuntimeError("LyricsLab history UI anchor not found")

    js_anchor = '<script src="/assets/js/lyricslab-r38-6-fix.js?v=20260928r38_6"></script>\n'
    if js_anchor not in template_text and "lyrics-history-r38-15.js" not in template_text:
        raise RuntimeError("LyricsLab javascript anchor not found")

    # Controller: archive the current full source before Whisper replaces it.
    if "LyricsSourceHistoryService $lyricsHistory" not in controller_text:
        controller_text = controller_text.replace(
            controller_sig,
            """public function extractLyrics(
    Song $song,
    Request $request,
    \\\\App\\\\Service\\\\SongLyricsJobService $jobs,
    \\\\App\\\\Service\\\\LyricsSourceHistoryService $lyricsHistory,
): Response {""",
            1,
        )

    if "Sauvegarde automatique avant extraction Whisper" not in controller_text:
        controller_text = controller_text.replace(
            controller_queue,
            """    $lyricsHistory->archiveCurrentIfChanged(
        $song,
        $user,
        'manual',
        'Sauvegarde automatique avant extraction Whisper.',
    );

    $jobs->queue($song, $user, 'extract');
""",
            1,
        )

    # Template: isolated history CSS.
    if "lyrics-history-r38-15.css" not in template_text:
        template_text = template_text.replace(
            style_anchor,
            style_anchor + '<link rel="stylesheet" href="/assets/css/lyrics-history-r38-15.css?v=20260929r38_15">\n',
            1,
        )

    # Template: compact full-block history control.
    if "data-lyrics-history" not in template_text:
        history_markup = """    <details class="lyrics-history"
             data-lyrics-history
             data-list-url="{{ path('app_song_lyrics_history', {'_locale': app.request.locale, id: song.id}) }}"
             data-save-url="{{ path('app_song_lyrics_history_save', {'_locale': app.request.locale, id: song.id}) }}"
             data-restore-url-template="{{ path('app_song_lyrics_history_restore', {'_locale': app.request.locale, id: song.id, revisionId:999999})|replace({'999999':'__REVISION__'}) }}"
             data-delete-url-template="{{ path('app_song_lyrics_history_delete', {'_locale': app.request.locale, id: song.id, revisionId:999999})|replace({'999999':'__REVISION__'}) }}"
             data-token="{{ csrf_token('song_lyrics_history_' ~ song.id) }}">
        <summary>Historique des paroles (<span data-lyrics-history-count>0</span>)</summary>

        <form class="lyrics-history-editor" data-lyrics-history-save>
            <label>
                Source
                <select name="lyrics_history_source_type">
                    <option value="manual">Manuel</option>
                    <option value="lyrics_ovh">Lyrics.ovh</option>
                    <option value="whisper">Whisper</option>
                    <option value="other">Autre</option>
                </select>
            </label>

            <label>
                Commentaire personnel
                <input type="text"
                       name="lyrics_history_comment"
                       maxlength="1000"
                       placeholder="Ex. : paroles cherchées avec OVH">
            </label>

            <button type="submit">Sauvegarder cette version</button>
        </form>

        <div class="lyrics-history-feedback" data-lyrics-history-feedback></div>
        <div class="lyrics-history-list" data-lyrics-history-list>
            <p class="page-note">Chargement de l’historique…</p>
        </div>
    </details>

"""
        template_text = template_text.replace(panel_anchor, history_markup + panel_anchor, 1)

    if "lyrics-history-r38-15.js" not in template_text:
        template_text = template_text.replace(
            js_anchor,
            js_anchor + '<script src="/assets/js/lyrics-history-r38-15.js?v=20260929r38_15"></script>\n',
            1,
        )

    controller.write_text(controller_text, encoding="utf-8")
    template.write_text(template_text, encoding="utf-8")

    print("R38_15_LYRICS_HISTORY_INSTALL_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
