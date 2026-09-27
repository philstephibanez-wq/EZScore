#!/usr/bin/env python3
from pathlib import Path
import sys

def die(msg):
    raise SystemExit("R35.5a ABORT: " + msg)

root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
p = root / "templates/layout/song/_workflow_tabs.html.twig"
if not p.is_file():
    die("templates/layout/song/_workflow_tabs.html.twig absent")

content = """{% set current = current|default('') %}
{% set existing_song = song is defined and song and song.id %}
{% set wf = existing_song ? song_workflow(song) : {} %}

<nav class="workflow-tabs song-workflow-tabs" aria-label="Workflow chanson">
{% if not existing_song %}
    <span class="workflow-tab active">1 · IMPORT</span>
    <span class="workflow-tab disabled" aria-disabled="true">2 · TABLEAU DE BORD</span>
    <span class="workflow-tab disabled" aria-disabled="true">3 · ÉDITION</span>
    <span class="workflow-tab disabled" aria-disabled="true">4 · STEMSLAB</span>
    <span class="workflow-tab disabled" aria-disabled="true">5 · CHORDSLAB</span>
    <span class="workflow-tab disabled" aria-disabled="true">6 · LYRICSLAB</span>
    <span class="workflow-tab disabled" aria-disabled="true">7 · PUBLICATION</span>
{% else %}
    <a class="workflow-tab {{ current == 'analysis' ? 'active' : '' }}"
       href="{{ path('app_song_analysis_lab', {'_locale': app.request.locale, id: song.id}) }}">1 · TABLEAU DE BORD</a>

    <span class="workflow-tab {{ wf.imported ? 'completed' : '' }}"
          title="{{ wf.imported ? 'Import terminé' : 'Import requis' }}">2 · IMPORT</span>

    <a class="workflow-tab {{ current == 'edit' ? 'active' : '' }}"
       href="{{ path('app_song_edit', {'_locale': app.request.locale, id: song.id}) }}">3 · ÉDITION</a>

    {% if wf.can_stems %}
        <a class="workflow-tab {{ current == 'stems' ? 'active' : '' }} {{ wf.stems_ready ? 'completed' : '' }}"
           href="{{ path('app_song_stems', {'_locale': app.request.locale, id: song.id}) }}">4 · STEMSLAB</a>
    {% else %}
        <span class="workflow-tab disabled" aria-disabled="true">4 · STEMSLAB</span>
    {% endif %}

    {% if wf.can_chords %}
        <a class="workflow-tab {{ current == 'chords' ? 'active' : '' }} {{ wf.chords_ready ? 'completed' : '' }}"
           href="{{ path('app_song_chordslab', {'_locale': app.request.locale, id: song.id}) }}">5 · CHORDSLAB</a>
    {% else %}
        <span class="workflow-tab disabled" aria-disabled="true" title="Stems requis">5 · CHORDSLAB</span>
    {% endif %}

    {% if wf.can_lyrics %}
        <a class="workflow-tab {{ current == 'lyrics' ? 'active' : '' }} {{ wf.lyrics_ready ? 'completed' : '' }}"
           href="{{ path('app_song_lyricslab', {'_locale': app.request.locale, id: song.id}) }}">6 · LYRICSLAB</a>
    {% else %}
        <span class="workflow-tab disabled" aria-disabled="true" title="Accords requis">6 · LYRICSLAB</span>
    {% endif %}

    {% if wf.can_publish %}
        <a class="workflow-tab {{ current == 'publication' ? 'active' : '' }} {{ wf.published ? 'completed' : '' }}"
           href="{{ path('app_song_publication_lab', {'_locale': app.request.locale, id: song.id}) }}">7 · PUBLICATION</a>
    {% else %}
        <span class="workflow-tab disabled" aria-disabled="true" title="Paroles requises">7 · PUBLICATION</span>
    {% endif %}
{% endif %}
</nav>
"""

p.write_text(content, encoding="utf-8", newline="\n")

# Remove the R35.5 "dashboard-only" CSS rule if present; it is no longer wanted.
css = root / "public/assets/css/r35-5-ux.css"
if css.is_file():
    s = css.read_text(encoding="utf-8-sig")
    s = s.replace(".dashboard-only-tab{display:flex;max-width:260px;margin-bottom:18px}.dashboard-only-tab .workflow-tab{width:100%;justify-content:center}", "")
    css.write_text(s, encoding="utf-8", newline="\n")

readme = root / "readme.md"
if readme.is_file():
    s = readme.read_text(encoding="utf-8-sig")
    if "R35.5a WORKFLOW TABS FIX" not in s:
        s += "\n\n## R35.5a WORKFLOW TABS FIX\nRestaure la navigation complète du workflow. Seul le premier onglet devient `TABLEAU DE BORD`; Import, Édition, StemsLab, ChordsLab, LyricsLab et Publication restent présents et gardent leur verrouillage par prérequis.\n"
    readme.write_text(s, encoding="utf-8", newline="\n")

print("R35_5A_APPLIED_OK")
