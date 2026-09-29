#!/usr/bin/env python3
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else r"H:\EZScore_v1").resolve()
HERE = Path(__file__).resolve().parent.parent
PATCH = HERE / "patches"

CHORD = ROOT / "templates/song/chordslab.html.twig"
LYRIC = ROOT / "templates/song/lyricslab.html.twig"
PARTIAL = ROOT / "templates/song/components/_live_visual_settings.html.twig"
CSS = ROOT / "public/assets/css/components/ezscore-live-visual-settings.css"
JS = ROOT / "public/assets/js/components/ezscore-live-visual-settings.js"

NEW = [
    (PATCH/"templates/song/components/_live_visual_settings.html.twig", PARTIAL),
    (PATCH/"public/assets/css/components/ezscore-live-visual-settings.css", CSS),
    (PATCH/"public/assets/js/components/ezscore-live-visual-settings.js", JS),
]

def rd(p):
    return p.read_text(encoding="utf-8").replace("\r\n","\n").replace("\r","\n")

def wr(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".r39_2d_tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    tmp.replace(p)

def main():
    for p in (CHORD, LYRIC):
        if not p.is_file():
            raise RuntimeError(f"Missing prerequisite: {p}")

    backups = {CHORD: CHORD.read_bytes(), LYRIC: LYRIC.read_bytes()}
    created = []

    try:
        for src, dst in NEW:
            if not src.is_file():
                raise RuntimeError(f"Missing patch file: {src}")
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            created.append(dst)

        chord = rd(CHORD)

        old_start = '<section class="panel chordslab-settings">\n'
        old_end = '</section>\n\n<section class="panel chordslab-prompter"'
        start = chord.find(old_start)
        end = chord.find(old_end, start)

        if start < 0 or end < 0:
            raise RuntimeError("Chords settings block anchors missing")

        shared = (
            "{% include 'song/components/_live_visual_settings.html.twig' with {\n"
            "    song:song,\n"
            "    time_signatures:time_signatures,\n"
            "    context:'chords'\n"
            "} %}\n\n"
        )
        chord = chord[:start] + shared + chord[end + len('</section>\n\n'):]

        css_tag = '<link rel="stylesheet" href="/assets/css/components/ezscore-live-visual-settings.css?v=20260930r39_2d">'
        if css_tag not in chord:
            chord = chord.replace('{% endblock %}\n\n{% block body %}', css_tag + '\n{% endblock %}\n\n{% block body %}', 1)

        js_tag = '<script src="/assets/js/components/ezscore-live-visual-settings.js?v=20260930r39_2d"></script>'
        if js_tag not in chord:
            anchor = '<script src="/assets/js/chordslab.js'
            if anchor not in chord:
                raise RuntimeError("Chords JS anchor missing")
            chord = chord.replace(anchor, js_tag + '\n' + anchor, 1)

        wr(CHORD, chord)

        lyric = rd(LYRIC)

        song_card = "{% include 'song/components/_lab_song_card.html.twig' with {song:song, beat_events:beat_events} %}"
        if song_card not in lyric:
            raise RuntimeError("Lyrics song card anchor missing")

        shared_lyrics = (
            song_card + "\n\n"
            "{% include 'song/components/_live_visual_settings.html.twig' with {\n"
            "    song:song,\n"
            "    context:'lyrics'\n"
            "} %}"
        )
        if "context:'lyrics'" not in lyric:
            lyric = lyric.replace(song_card, shared_lyrics, 1)

        css_tag = '<link rel="stylesheet" href="/assets/css/components/ezscore-live-visual-settings.css?v=20260930r39_2d">'
        if css_tag not in lyric:
            lyric = lyric.replace('{% endblock %}\n\n{% block body %}', css_tag + '\n{% endblock %}\n\n{% block body %}', 1)

        js_tag = '<script src="/assets/js/components/ezscore-live-visual-settings.js?v=20260930r39_2d"></script>'
        if js_tag not in lyric:
            anchor = '<script src="/assets/js/lyricslab-timeline-r39.js'
            if anchor not in lyric:
                raise RuntimeError("Lyrics JS anchor missing")
            lyric = lyric.replace(anchor, js_tag + '\n' + anchor, 1)

        wr(LYRIC, lyric)

        print("R39_2D_SHARED_VISUAL_SETTINGS_INSTALL_OK")

    except Exception:
        for p, data in backups.items():
            p.write_bytes(data)
        for p in created:
            if p.exists():
                try:
                    p.unlink()
                except OSError:
                    pass
        raise

if __name__ == "__main__":
    main()
