#!/usr/bin/env python3
from __future__ import annotations
import re,sys
from pathlib import Path
ROOT=Path(sys.argv[1] if len(sys.argv)>1 else r"H:\EZScore_v1").resolve()
TEMPLATE=ROOT/"templates/song/lyricslab.html.twig"
LAB_JS=ROOT/"public/assets/js/lyricslab-r37.js"
HISTORY_JS=ROOT/"public/assets/js/lyrics-history-r38-15.js"
OVH_CLIENT=ROOT/"src/Service/LyricsOvhClient.php"
SAVE_HISTORY_MARKUP='<div class="lyrics-history-shell" data-lyrics-history\n         data-list-url="{{ path(\'app_song_lyrics_history\', {\'_locale\': app.request.locale, id: song.id}) }}"\n         data-save-url="{{ path(\'app_song_lyrics_history_save\', {\'_locale\': app.request.locale, id: song.id}) }}"\n         data-restore-url-template="{{ path(\'app_song_lyrics_history_restore\', {\'_locale\': app.request.locale, id: song.id, revisionId:999999})|replace({\'999999\':\'__REVISION__\'}) }}"\n         data-delete-url-template="{{ path(\'app_song_lyrics_history_delete\', {\'_locale\': app.request.locale, id: song.id, revisionId:999999})|replace({\'999999\':\'__REVISION__\'}) }}"\n         data-token="{{ csrf_token(\'song_lyrics_history_\' ~ song.id) }}">\n\n        <div class="lyrics-history-savebar">\n            <form class="lyrics-history-editor" data-lyrics-history-save>\n                <label>\n                    Source\n                    <select name="lyrics_history_source_type">\n                        <option value="manual">Manuel</option>\n                        <option value="lyrics_ovh">Lyrics.ovh</option>\n                        <option value="whisper">Whisper</option>\n                        <option value="other">Autre</option>\n                    </select>\n                </label>\n                <label>\n                    Commentaire personnel\n                    <input type="text"\n                           name="lyrics_history_comment"\n                           maxlength="1000"\n                           placeholder="Ex. : paroles cherchées avec OVH">\n                </label>\n                <button type="submit">Sauvegarder cette version</button>\n            </form>\n            <div class="lyrics-manual-state" data-lyrics-manual-state>Sauvegardé</div>\n            <div class="lyrics-history-feedback" data-lyrics-history-feedback></div>\n        </div>\n\n        <details class="lyrics-history">\n            <summary>Historique des paroles (<span data-lyrics-history-count>0</span>)</summary>\n            <div class="lyrics-history-list" data-lyrics-history-list>\n                <p class="page-note">Chargement de l’historique…</p>\n            </div>\n        </details>\n    </div>'

def main():
    for p in (TEMPLATE,LAB_JS,HISTORY_JS):
        if not p.is_file(): raise RuntimeError(f"Missing prerequisite: {p}")
    template=TEMPLATE.read_text(encoding="utf-8")
    lab_js=LAB_JS.read_text(encoding="utf-8")
    history_js=HISTORY_JS.read_text(encoding="utf-8")

    if OVH_CLIENT.is_file():
        ovh=OVH_CLIENT.read_text(encoding="utf-8").replace(r'\\Throwable',r'\Throwable')
        OVH_CLIENT.write_text(ovh,encoding="utf-8",newline="\n")

    marker="const source=document.querySelector('[data-lyrics-source]'),state=document.querySelector('[data-lyrics-save-state]');let timer=null;"
    if marker in lab_js:
        start=lab_js.index(marker)
        listener=lab_js.find("source?.addEventListener('input'",start)
        if listener<0: raise RuntimeError("Autosave listener start not found")
        end=lab_js.find("});",listener)
        if end<0: raise RuntimeError("Autosave listener end not found")
        lab_js=lab_js[:start]+lab_js[end+3:]
    if "timer=setTimeout(save,450)" in lab_js: raise RuntimeError("Legacy autosave remains")

    template=re.sub(r'\n\s*data-save-url="[^"]*"','',template,count=1)
    template=re.sub(r'\n\s*data-save-token="[^"]*"','',template,count=1)
    template=re.sub(r'\s*<span class="chordslab-settings-save-state"\s+data-lyrics-save-state>.*?</span>\s*','\n',template,count=1,flags=re.S)

    for pattern in [
        r'\s*<div class="lyrics-history-shell"[^>]*>.*?</details>\s*</div>\s*',
        r'\s*<div class="lyrics-manual-savebar"[^>]*>.*?</details>\s*</div>\s*',
        r'\s*<details class="lyrics-history"[^>]*>.*?</details>\s*',
    ]:
        template=re.sub(pattern,'\n',template,count=1,flags=re.S)

    textarea_end=template.find('</textarea>')
    if textarea_end<0: raise RuntimeError("Lyrics textarea not found")
    textarea_end+=len('</textarea>')
    template=template[:textarea_end]+"\n\n    "+SAVE_HISTORY_MARKUP+template[textarea_end:]

    if "ezscore:lyrics-history-saved" not in history_js:
        anchor="    setFeedback('Version sauvegardée.');\n"
        if anchor not in history_js: raise RuntimeError("History save success anchor not found")
        history_js=history_js.replace(anchor,anchor+"    document.dispatchEvent(new CustomEvent('ezscore:lyrics-history-saved'));\n",1)

    if "ezscore:lyrics-history-restored" not in history_js:
        anchor="      setFeedback('Version restaurée.');\n"
        if anchor not in history_js: raise RuntimeError("History restore success anchor not found")
        history_js=history_js.replace(anchor,anchor+"      document.dispatchEvent(new CustomEvent('ezscore:lyrics-history-restored'));\n",1)

    if "lyrics-dirty-guard-r38-16j.css" not in template:
        block=template.find("{% block stylesheets %}"); end=template.find("{% endblock %}",block)
        if block<0 or end<0: raise RuntimeError("Stylesheets block not found")
        template=template[:end]+'<link rel="stylesheet" href="/assets/css/lyrics-dirty-guard-r38-16j.css?v=20260929r38_16j">\n'+template[end:]

    if "lyrics-dirty-guard-r38-16j.js" not in template:
        block=template.find("{% block javascripts %}"); end=template.find("{% endblock %}",block)
        if block<0 or end<0: raise RuntimeError("Javascripts block not found")
        template=template[:end]+'<script src="/assets/js/lyrics-dirty-guard-r38-16j.js?v=20260929r38_16j"></script>\n'+template[end:]

    template=re.sub(r'(/assets/js/lyrics-history-r38-15\.js\?v=)[^"]+',r'\g<1>20260929r38_16j',template,count=1)

    TEMPLATE.write_text(template,encoding="utf-8",newline="\n")
    LAB_JS.write_text(lab_js,encoding="utf-8",newline="\n")
    HISTORY_JS.write_text(history_js,encoding="utf-8",newline="\n")
    print("R38_16J_MANUAL_SAVE_DIRTY_GUARD_INSTALL_OK")
    return 0
if __name__=="__main__": raise SystemExit(main())
