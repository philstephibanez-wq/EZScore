#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else r"H:\EZScore_v1").resolve()

TWIG = ROOT / "templates/song/lyricslab.html.twig"
JS = ROOT / "public/assets/js/lyricslab-timeline-r39.js"
CSS = ROOT / "public/assets/css/lyricslab-r37.css"
CATALOG = ROOT / "src/Controller/CatalogController.php"
DIAG_JS = ROOT / "public/assets/js/components/ezscore-chord-diagram.js"
DIAG_CSS = ROOT / "public/assets/css/components/ezscore-chord-diagram.css"

BASE_COMMIT = "93d117e60af0e05b078e6c845e9482f8deccef92"

def rd(p):
    return p.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")

def wr(p, text):
    tmp = p.with_suffix(p.suffix + ".r39_5_full_tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    tmp.replace(p)

def once(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise RuntimeError(f"{label}: expected 1 anchor, found {n}. STOP.")
    return text.replace(old, new, 1)

def main():
    for p in (TWIG, JS, CSS, CATALOG, DIAG_JS, DIAG_CSS):
        if not p.is_file():
            raise RuntimeError(f"Missing prerequisite: {p}. STOP.")

    twig = rd(TWIG)
    js = rd(JS)
    css = rd(CSS)
    catalog = rd(CATALOG)

    backups = {
        TWIG: TWIG.read_bytes(),
        JS: JS.read_bytes(),
        CSS: CSS.read_bytes(),
        CATALOG: CATALOG.read_bytes(),
    }

    # Strict current GitHub master baseline: R39.4.
    checks = [
        ("lyrics css baseline", "/assets/css/lyricslab-r37.css?v=20260929r39_2" in twig),
        ("lyrics js baseline", "/assets/js/lyricslab-timeline-r39.js?v=20260929r39_0_1" in twig),
        ("diagram not yet loaded css", "ezscore-chord-diagram.css" not in twig),
        ("diagram not yet loaded js", "ezscore-chord-diagram.js" not in twig),
        ("inner stage baseline", "host.innerHTML='<div class=\"lyrics-ribbon-stage r39-shared-timeline\" data-stage><div class=\"lyrics-reading-zone\"" in js),
        ("canonical render baseline", "const x=focusX(),metric=timeline.timeToX(lastTime*1000);" in js),
        ("lyrics stage 330", ".lyrics-ribbon-stage{position:relative;height:330px" in css),
        ("lyrics reading top 112", ".lyrics-reading-zone{position:absolute;top:112px" in css),
        ("catalog undefined-status baseline", "$this->applyStatus($song, $requestedStatus);" in catalog),
        ("catalog request status missing", "$requestedStatus = SongStatus::tryFrom" not in catalog),
    ]
    bad = [name for name, ok in checks if not ok]
    if bad:
        raise RuntimeError("Unexpected clean R39.4 baseline: " + ", ".join(bad) + ". STOP.")

    try:
        # ------------------------------------------------------------
        # 1) Lyrics template: load the SAME shared Chords diagram assets.
        # ------------------------------------------------------------
        twig = once(
            twig,
            '<link rel="stylesheet" href="/assets/css/components/ezscore-live-visual-settings.css?v=20260930r39_2d">',
            '<link rel="stylesheet" href="/assets/css/components/ezscore-live-visual-settings.css?v=20260930r39_2d">\n'
            '<link rel="stylesheet" href="/assets/css/components/ezscore-chord-diagram.css?v=20260930r39_3">',
            "Lyrics shared diagram CSS asset",
        )
        twig = once(
            twig,
            '<script src="/assets/js/components/ezscore-live-visual-settings.js?v=20260930r39_2d"></script>',
            '<script src="/assets/js/components/ezscore-live-visual-settings.js?v=20260930r39_2d"></script>\n'
            '<script src="/assets/js/components/ezscore-chord-diagram.js?v=20260930r39_3"></script>',
            "Lyrics shared diagram JS asset",
        )
        twig = once(
            twig,
            "/assets/css/lyricslab-r37.css?v=20260929r39_2",
            "/assets/css/lyricslab-r37.css?v=20260930r39_5full",
            "Lyrics CSS cache bust",
        )
        twig = once(
            twig,
            "/assets/js/lyricslab-timeline-r39.js?v=20260929r39_0_1",
            "/assets/js/lyricslab-timeline-r39.js?v=20260930r39_5full",
            "Lyrics JS cache bust",
        )

        # Keep show_diagram=false intentionally.
        # The correct diagram host belongs INSIDE lyrics-ribbon-stage, not in the outer chordslab-stage.
        if "show_diagram: false" not in twig:
            raise RuntimeError("Expected outer diagram disabled in clean Lyrics template. STOP.")

        # ------------------------------------------------------------
        # 2) Lyrics timeline JS: create diagram in the REAL ribbon stage.
        # ------------------------------------------------------------
        old_html = (
            " host.innerHTML='<div class=\"lyrics-ribbon-stage r39-shared-timeline\" data-stage>"
            "<div class=\"lyrics-reading-zone\" data-reading-zone></div>"
            "<div class=\"lyrics-ribbon-track\" data-track>"
            "<div class=\"lyrics-ribbon-chords\" data-chords-lane></div>"
            "<div class=\"lyrics-ribbon-syllables\" data-syllables-lane></div>"
            "</div></div>';"
        )
        new_html = (
            " host.innerHTML='<div class=\"lyrics-ribbon-stage r39-shared-timeline\" data-stage>"
            "<div class=\"lyrics-stage-diagram ez-chord-diagram\" data-lyrics-stage-diagram hidden></div>"
            "<div class=\"lyrics-reading-zone\" data-reading-zone></div>"
            "<div class=\"lyrics-ribbon-track\" data-track>"
            "<div class=\"lyrics-ribbon-chords\" data-chords-lane></div>"
            "<div class=\"lyrics-ribbon-syllables\" data-syllables-lane></div>"
            "</div></div>';"
        )
        js = once(js, old_html, new_html, "Lyrics inner stage diagram host")

        old_bind = (
            " const stage=host.querySelector('[data-stage]'),zone=host.querySelector('[data-reading-zone]'),"
            "track=host.querySelector('[data-track]'),chordLane=host.querySelector('[data-chords-lane]'),"
            "syllableLane=host.querySelector('[data-syllables-lane]');"
        )
        new_bind = (
            " const stage=host.querySelector('[data-stage]'),diagram=host.querySelector('[data-lyrics-stage-diagram]'),"
            "zone=host.querySelector('[data-reading-zone]'),track=host.querySelector('[data-track]'),"
            "chordLane=host.querySelector('[data-chords-lane]'),syllableLane=host.querySelector('[data-syllables-lane]');\n"
            " const diagramToggle=document.querySelector('[data-chordslab-diagram]');"
        )
        js = once(js, old_bind, new_bind, "Lyrics diagram bindings")

        old_render = """ function renderAt(sec,force=false){
  lastTime=Math.max(0,Number(sec)||0);const x=focusX(),metric=timeline.timeToX(lastTime*1000);zone.style.left=x+'px';track.style.transform=`translate3d(${x-metric}px,0,0)`;
  const bi=timeline.beatIndexAtMs(lastTime*1000);if(force||bi!==lastBeat){lastBeat=bi;chordLane.querySelectorAll('.current').forEach(e=>e.classList.remove('current'));chordLane.querySelector(`.lyrics-ribbon-beat[data-beat-seq="${bi}"]`)?.classList.add('current')}
  const si=activeSyllable(lastTime*1000);if(force||si!==lastSyllable){lastSyllable=si;syllableNodes.forEach((e,i)=>{e.classList.toggle('past',si>=0&&i<si);e.classList.toggle('current',i===si)})}
 }"""

        new_render = """ function renderAt(sec,force=false){
  lastTime=Math.max(0,Number(sec)||0);const ms=lastTime*1000,x=focusX(),metric=timeline.timeToX(ms);zone.style.left=x+'px';track.style.transform=`translate3d(${x-metric}px,0,0)`;
  const bi=timeline.beatIndexAtMs(ms);if(force||bi!==lastBeat){lastBeat=bi;chordLane.querySelectorAll('.current').forEach(e=>e.classList.remove('current'));chordLane.querySelector(`.lyrics-ribbon-beat[data-beat-seq="${bi}"]`)?.classList.add('current')}
  if(diagram){
   diagram.style.left=x+'px';
   const active=timeline.activeEventAt(chords,ms);
   const label=shown(active?.effective||active?.original||'.');
   if(diagramToggle?.checked&&label&&label!=='.'){diagram.hidden=false;window.EZScoreChordDiagram?.render(diagram,label)}
   else{diagram.hidden=true;diagram.innerHTML=''}
  }
  const si=activeSyllable(ms);if(force||si!==lastSyllable){lastSyllable=si;syllableNodes.forEach((e,i)=>{e.classList.toggle('past',si>=0&&i<si);e.classList.toggle('current',i===si)})}
 }"""
        js = once(js, old_render, new_render, "Lyrics canonical render + shared diagram")

        audio_anchor = (
            " document.querySelector('[data-stem-mixer]')?.addEventListener("
            "'ezscore:audio-timeupdate',e=>renderAt(Number(e.detail?.time||0)));\n"
        )
        js = once(
            js,
            audio_anchor,
            audio_anchor + " diagramToggle?.addEventListener('change',()=>renderAt(lastTime,true));\n",
            "Lyrics diagram toggle",
        )

        # ------------------------------------------------------------
        # 3) Lyrics CSS: reserve one explicit top band INSIDE ribbon stage.
        #    Same diagram size as Chords: no size override.
        # ------------------------------------------------------------
        marker = "/* R39.5 FULL — shared Chords diagram lives inside the Lyrics ribbon stage. */"
        if marker in css:
            raise RuntimeError("R39.5 FULL already installed. STOP.")

        css += r"""

/* R39.5 FULL — shared Chords diagram lives inside the Lyrics ribbon stage.
   The upper band is explicit layout space, not an overlay outside the stage. */
[data-lyricslab] .r39-shared-timeline{
    height:392px!important;
}
[data-lyricslab] .r39-shared-timeline .lyrics-stage-diagram{
    position:absolute!important;
    top:6px!important;
    transform:translateX(-50%)!important;
    z-index:45!important;
}
[data-lyricslab] .r39-shared-timeline .lyrics-stage-diagram[hidden]{
    display:none!important;
}
[data-lyricslab] .r39-shared-timeline .lyrics-reading-zone{
    top:174px!important;
}
[data-lyricslab] .r39-shared-timeline .lyrics-ribbon-chords{
    top:174px!important;
}
[data-lyricslab] .r39-shared-timeline .lyrics-ribbon-syllables{
    top:284px!important;
}
"""

        # ------------------------------------------------------------
        # 4) Catalog regression: define requestedStatus before applyStatus().
        # ------------------------------------------------------------
        catalog = once(
            catalog,
            """        // R35.5: propriétaire immuable; délégations via SongCollaborator.

        $wasPublished = $song->isPublished();
        $this->applyStatus($song, $requestedStatus);
""",
            """        // R35.5: propriétaire immuable; délégations via SongCollaborator.

        $requestedStatus = SongStatus::tryFrom((string) $request->request->get('status', ''))
            ?? $song->getStatus();

        $wasPublished = $song->isPublished();
        $this->applyStatus($song, $requestedStatus);
""",
            "Catalog requestedStatus initialization",
        )

        # ------------------------------------------------------------
        # Final invariants before any write.
        # ------------------------------------------------------------
        for token in (
            "data-lyrics-stage-diagram",
            "window.EZScoreChordDiagram?.render(diagram,label)",
            "timeline.activeEventAt(chords,ms)",
            "diagramToggle?.addEventListener('change',()=>renderAt(lastTime,true))",
        ):
            if token not in js:
                raise RuntimeError(f"Generated Lyrics JS missing {token}. STOP.")

        if "const SHAPES" in js:
            raise RuntimeError("Lyrics must not duplicate guitar shapes. STOP.")

        for token in (
            "height:392px!important",
            "top:174px!important",
            "top:284px!important",
        ):
            if token not in css:
                raise RuntimeError(f"Generated Lyrics CSS missing {token}. STOP.")

        if "$requestedStatus = SongStatus::tryFrom" not in catalog:
            raise RuntimeError("Catalog requestedStatus fix missing. STOP.")

        # Write only after all validations passed.
        wr(TWIG, twig)
        wr(JS, js)
        wr(CSS, css)
        wr(CATALOG, catalog)

        print("R39_5_FULL_LYRICS_DIAGRAM_AND_CATALOG_FIX_INSTALL_OK")

    except Exception:
        for p, data in backups.items():
            p.write_bytes(data)
        raise

if __name__ == "__main__":
    main()
