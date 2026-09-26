#!/usr/bin/env python3
from __future__ import annotations
from datetime import datetime
from pathlib import Path
import re, shutil

ROOT=Path(__file__).resolve().parents[1]
PAYLOAD=ROOT/"scripts"/"_payload"
BACKUP=ROOT/"var"/"backup"/("r34-1-profiles-ui-"+datetime.now().strftime("%Y%m%d-%H%M%S"))

def backup(path):
    path=Path(path)
    if not path.exists():return
    dst=BACKUP/path.relative_to(ROOT);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dst)

def save(path,text,label):
    path=Path(path);old=path.read_text(encoding="utf-8")
    if old==text:
        print(f"[OK] {label}: already applied");return
    backup(path);path.write_text(text,encoding="utf-8",newline="\n");print(f"[OK] {label}")

def snip(name):return (PAYLOAD/"snippets"/name).read_text(encoding="utf-8")

def install_js():
    src=PAYLOAD/"public/assets/js/chordslab.js";dst=ROOT/"public/assets/js/chordslab.js"
    content=src.read_text(encoding="utf-8")
    if dst.exists() and dst.read_text(encoding="utf-8")==content:
        print("[OK] chordslab.js already applied");return
    backup(dst);dst.write_text(content,encoding="utf-8",newline="\n");print("[OK] chordslab.js R34.1")

def patch_controller():
    path=ROOT/"src/Controller/SongLabController.php";text=path.read_text(encoding="utf-8")

    if "app_song_chordslab_profile_data" not in text:
        anchor="    #[Route('/chords/profile', name: 'app_song_chordslab_profile', methods: ['POST'])]\n"
        if anchor not in text:raise RuntimeError("R34 profile POST endpoint anchor not found")
        text=text.replace(anchor,snip("profile_data_endpoint.txt")+anchor,1)

    old="""        $em->flush();
        $this->addFlash('success', 'chordslab.settings.saved');"""
    if old in text:
        text=text.replace(old,snip("settings_json.txt").rstrip(),1)
    elif "getPreferredFormat() === 'json'" not in text:
        raise RuntimeError("settings JSON anchor not found")

    save(path,text,"SongLab R34.1 endpoints/autosave")

def patch_template():
    path=ROOT/"templates/song/chordslab.html.twig";text=path.read_text(encoding="utf-8")

    # Mark settings form, remove generic Save, add autosave state.
    if 'data-chord-settings-form' not in text:
        text=text.replace(
            'class="chordslab-settings-grid">',
            'class="chordslab-settings-grid" data-chord-settings-form>',
            1,
        )

    text=re.sub(
        r'\s*<button type="submit" class="primary">\{\{ \'common\.save\'\|trans \}\}</button>',
        '\n        <span class="chordslab-settings-save-state" data-chord-settings-state>Enregistré automatiquement</span>',
        text,
        count=1,
    )

    # Explicit profile data endpoint URL.
    if 'data-profile-data-url-template' not in text:
        anchor='         data-profile-token="{{ csrf_token(\'song_chordslab_profile_\' ~ song.id) }}"\n'
        if anchor not in text:raise RuntimeError("R34 profile token dataset anchor not found")
        addition='         data-profile-data-url-template="{{ path(\'app_song_chordslab_profile_data\', {\'_locale\': app.request.locale, id: song.id, profile:\'__PROFILE__\'}) }}"\n'
        text=text.replace(anchor,anchor+addition,1)

    # Add visible current profile/count beside prompter title.
    if 'data-chord-profile-badge' not in text:
        anchor='            <h2>{{ \'chordslab.timeline\'|trans({}, \'chordslab\') }}</h2>\n        </div>\n'
        if anchor not in text:raise RuntimeError("prompter title anchor not found")
        text=text.replace(anchor,anchor+snip("profile_status.html"),1)

    # Remove old inline submit auto-start and let R34.1 modal guard it.
    text=text.replace(
        """            <form method="post"
                  action="{{ path('app_song_chordslab_analyze', {'_locale': app.request.locale, id: song.id}) }}"
                  onsubmit="const b=this.querySelector('button'); b.disabled=true; b.textContent='{{ 'chordslab.analyze.running'|trans({}, 'chordslab')|e('js') }}';">""",
        """            <form method="post"
                  action="{{ path('app_song_chordslab_analyze', {'_locale': app.request.locale, id: song.id}) }}"
                  data-chord-analyze-form>""",
        1,
    )
    if "data-chord-analyze-form" not in text:
        text=text.replace(
            "action=\"{{ path('app_song_chordslab_analyze', {'_locale': app.request.locale, id: song.id}) }}\"",
            "action=\"{{ path('app_song_chordslab_analyze', {'_locale': app.request.locale, id: song.id}) }}\" data-chord-analyze-form",
            1,
        )
        text=re.sub(r'\s+onsubmit="const b=.*?</form>', lambda m:m.group(0), text, count=0)

    if 'data-chord-analyze-dialog' not in text:
        anchor='<dialog class="ez-modal chord-reset-dialog" data-chord-reset-dialog>'
        pos=text.find(anchor)
        if pos<0:
            end="{% endblock %}"
            pos=text.rfind(end)
            if pos<0:raise RuntimeError("template dialog insertion anchor not found")
            text=text[:pos]+snip("analyze_dialog.html")+"\n"+text[pos:]
        else:
            text=text[:pos]+snip("analyze_dialog.html")+"\n"+text[pos:]

    text=text.replace('/assets/css/chordslab.css?v=20260927r34','/assets/css/chordslab.css?v=20260927r34_1')
    text=text.replace('/assets/js/chordslab.js?v=20260926r33','/assets/js/chordslab.js?v=20260927r34_1')

    save(path,text,"ChordsLab R34.1 template")

def patch_css():
    path=ROOT/"public/assets/css/chordslab.css";text=path.read_text(encoding="utf-8")
    if "R34.1 — immediate settings" in text:
        print("[OK] R34.1 CSS already applied");return
    save(path,text.rstrip()+"\n"+snip("css_add.txt"),"R34.1 CSS")

def patch_docs():
    for rel,sname,marker in [
        ("docs/CAHIER_DES_CHARGES.md","cdc_add.txt","## 43. ChordsLab — ergonomie profils et protection réanalyse"),
        ("recette.md","recette_add.txt","## 34. Recette R34.1 — switch profils / autosave / alerte réanalyse"),
    ]:
        path=ROOT/rel
        if not path.is_file():continue
        text=path.read_text(encoding="utf-8")
        if marker in text:
            print(f"[OK] {rel}: already updated");continue
        save(path,text.rstrip()+"\n"+snip(sname),rel)

def main():
    install_js()
    patch_controller()
    patch_template()
    patch_css()
    patch_docs()
    print(f"[OK] Backup: {BACKUP}")
    print("[OK] R34.1 profile switch / autosave / analyze guard applied.")

if __name__=="__main__":
    main()
