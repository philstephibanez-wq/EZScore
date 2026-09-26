#!/usr/bin/env python3
from __future__ import annotations
from datetime import datetime
from pathlib import Path
import re, shutil

ROOT=Path(__file__).resolve().parents[1]
PAYLOAD=ROOT/"scripts"/"_payload"
BACKUP=ROOT/"var"/"backup"/("r34-three-profiles-"+datetime.now().strftime("%Y%m%d-%H%M%S"))

def backup(path):
    path=Path(path)
    if not path.exists():return
    dst=BACKUP/path.relative_to(ROOT);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dst)

def save(path,text,label):
    path=Path(path);old=path.read_text(encoding="utf-8")
    if old==text:
        print(f"[OK] {label}: already applied");return
    backup(path);path.write_text(text,encoding="utf-8",newline="\n");print(f"[OK] {label}")

def install(rel):
    src=PAYLOAD/rel;dst=ROOT/rel;content=src.read_text(encoding="utf-8")
    if dst.exists() and dst.read_text(encoding="utf-8")==content:
        print(f"[OK] {rel}: already applied");return
    backup(dst);dst.parent.mkdir(parents=True,exist_ok=True);dst.write_text(content,encoding="utf-8",newline="\n");print(f"[OK] {rel}")

def snip(name):return (PAYLOAD/"snippets"/name).read_text(encoding="utf-8")

def patch_repo():
    path=ROOT/"src/Domain/Song/SongTimelineEventRepository.php";text=path.read_text(encoding="utf-8")
    if "findChordEventsForProfile" in text:
        print("[OK] repository profile filter already present");return
    anchor="    /** @return list<SongTimelineEvent> */\n    public function findBeatEvents(Song $song): array\n"
    if anchor not in text:raise RuntimeError("repository findBeatEvents anchor not found")
    save(path,text.replace(anchor,snip("repo_method.txt")+anchor,1),"repository profile filter")

def patch_controller():
    path=ROOT/"src/Controller/SongLabController.php";text=path.read_text(encoding="utf-8")

    pattern=re.compile(
        r"""    #\[Route\('/chords', name: 'app_song_chordslab', methods: \['GET'\]\)\].*?(?=\n\n    #\[Route\('/chords/analyze')""",
        re.S,
    )
    if "'chord_profiles' => $profiles" not in text:
        text,n=pattern.subn(snip("controller_chords.txt").rstrip(),text,count=1)
        if n!=1:raise RuntimeError("SongLab chords() block not found")

    if "app_song_chordslab_profile" not in text:
        anchor="    #[Route('/chords/settings', name: 'app_song_chordslab_settings', methods: ['POST'])]\n"
        if anchor not in text:raise RuntimeError("SongLab settings route anchor not found")
        text=text.replace(anchor,snip("profile_endpoint.txt")+anchor,1)

    # Validate/edit current profile only; event id already isolates the row.
    old="$chord = trim((string) ($payload['chord'] ?? ''));"
    new="""$chord = trim((string) ($payload['chord'] ?? ''));
        // Plain major triads use standard compact spelling: C, not redundant Cmaj.
        $chord = preg_replace('/^([A-G](?:#|b)?)maj$/', '$1', $chord) ?? $chord;"""
    if new not in text and old in text:text=text.replace(old,new,1)

    # Reset only active profile.
    old_reset="""        foreach ($timeline->findChordEvents($song) as $event) {
            $event->resetOverride();
        }"""
    new_reset="""        $profile = $song->getChordAnalysisLevel();
        foreach ($timeline->findChordEventsForProfile($song, $profile) as $event) {
            $event->resetOverride();
        }"""
    if old_reset in text:text=text.replace(old_reset,new_reset,1)

    save(path,text,"SongLab three profiles")

def patch_template():
    path=ROOT/"templates/song/chordslab.html.twig";text=path.read_text(encoding="utf-8")

    text=text.replace(
        '<select name="chord_analysis_level">',
        '<select name="chord_analysis_level" data-chordslab-profile>',
        1,
    )

    # R34 datasets: all layers + persisted selected profile.
    anchor='         data-events="{{ chord_events|json_encode|e(\'html_attr\') }}"\n'
    if 'data-profiles="{{ chord_profiles' not in text:
        if anchor not in text:raise RuntimeError("template data-events anchor not found")
        text=text.replace(
            anchor,
            anchor+
            '         data-profiles="{{ chord_profiles|json_encode|e(\'html_attr\') }}"\n'
            '         data-profile="{{ chord_profile }}"\n'
            '         data-profile-url="{{ path(\'app_song_chordslab_profile\', {\'_locale\': app.request.locale, id: song.id}) }}"\n'
            '         data-profile-token="{{ csrf_token(\'song_chordslab_profile_\' ~ song.id) }}"\n',
            1,
        )

    text=text.replace('/assets/css/chordslab.css?v=20260926r33_2aa','/assets/css/chordslab.css?v=20260927r34')
    text=text.replace('/assets/css/chordslab.css?v=20260926r33_2','/assets/css/chordslab.css?v=20260927r34')

    save(path,text,"ChordsLab profile datasets")

def patch_js():
    path=ROOT/"public/assets/js/chordslab.js"
    save(path,snip("chordslab_r34.js"),"ChordsLab three-profile renderer")

def patch_css():
    path=ROOT/"public/assets/css/chordslab.css";text=path.read_text(encoding="utf-8")
    if "R34 — three chord profiles" in text:
        print("[OK] R34 CSS already applied");return
    save(path,text.rstrip()+"\n"+snip("css_add.txt"),"R34 compact UX CSS")

def patch_docs():
    for rel,sname,marker in [
        ("docs/CAHIER_DES_CHARGES.md","cdc_add.txt","## 42. ChordsLab — trois profils harmoniques simultanés"),
        ("recette.md","recette_add.txt","## 33. Recette R34 — profils Débutant / Intermédiaire / Expert"),
    ]:
        path=ROOT/rel
        if not path.is_file():continue
        text=path.read_text(encoding="utf-8")
        if marker in text:
            print(f"[OK] {rel}: already updated");continue
        save(path,text.rstrip()+"\n"+snip(sname),rel)

def main():
    install("analysis/chord_timeline_analysis.py")
    install("src/Service/ChordTimelineResultService.php")
    patch_repo()
    patch_controller()
    patch_template()
    patch_js()
    patch_css()
    patch_docs()
    print(f"[OK] Backup: {BACKUP}")
    print("[OK] R34 three profiles applied.")

if __name__=="__main__":
    main()
