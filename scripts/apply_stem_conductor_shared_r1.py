from __future__ import annotations

import ast
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAYER = ROOT / "ezscore/player/stem_analysis_conductor.py"
UI = ROOT / "ezscore/ui/stem_lab_analysis.py"
HTML = ROOT / "templates/views/lyrics-editor.html"
CHORDS_UI = ROOT / "ezscore/ui/chords_lyrics_editor.py"
EXPECTED_HEAD = "5235963939750c2341a410d04bcdb045c490ab56"


def git_head() -> str:
    p = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return p.stdout.strip()


def backup(paths: list[Path]) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    preferred = Path(r"H:\temp")
    base = preferred if preferred.exists() else Path.home() / "AppData" / "Local" / "Temp"
    out = base / f"EZScore_STEM_CONDUCTOR_SHARED_R1_backup_{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    for path in paths:
        rel = path.relative_to(ROOT)
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
    return out


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: attendu 1 motif, trouvé {count}.")
    return text.replace(old, new, 1)


def replace_region(text: str, start_marker: str, end_marker: str, replacement: str, label: str) -> str:
    start = text.find(start_marker)
    if start < 0:
        raise RuntimeError(f"{label}: début introuvable.")
    end = text.find(end_marker, start)
    if end < 0:
        raise RuntimeError(f"{label}: fin introuvable.")
    return text[:start] + replacement + text[end:]


def patch_player(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    import_anchor = "from ezscore.analysis.forced_lyrics import load_alignment\n"
    if "_LYRICS_LAYOUT_JS =" not in text:
        text = replace_once(
            text,
            import_anchor,
            import_anchor
            + "\n"
            + "_TEMPLATE_DIR = Path(__file__).resolve().parents[2] / \"templates\" / \"views\"\n"
            + "_LYRICS_LAYOUT_JS = (_TEMPLATE_DIR / \"lyrics-layout.js\").read_text(encoding=\"utf-8\")\n",
            "chargement lyrics-layout.js",
        )

    text = replace_once(
        text,
        "_JS = base._PLAYER_JS\n",
        "_JS = _LYRICS_LAYOUT_JS + \"\\n\\n\" + base._PLAYER_JS\n",
        "composition JS commune",
    )

    start_marker = "  // Same visual layout contract as Analyse > Paroles.\n"
    end_marker = "  function findWordIndex(time) {\n"

    replacement = """  // Exact shared layout engine from Analyse > Paroles.
  const pixelsPerSecond=100;
  const rawXForTime=(time) =>
    Math.max(0,Number(time || 0))*pixelsPerSecond;

  let lyricLayout={xs:[],right:0,measurable:false};

  function visualXForTime(time) {
    return ezVisualXForTime(
      words,
      lyricLayout.xs,
      time,
      rawXForTime
    );
  }

  function layoutConductor() {
    lyricLayout=ezLayoutLaneNodes({
      nodes:lyricNodes,
      words,
      rawXForWord:(word) => rawXForTime(word.start),
      minGap:10,
      contractionGap:1,
    });

    chordNodes.forEach((node,index) => {
      const x=visualXForTime(chordItems[index].time);
      node.style.left=x+"px";
      node.dataset.timelineX=String(
        rawXForTime(chordItems[index].time)
      );
    });

    const lastWordEnd=words.length
      ? Math.max(...words.map(w=>Number(w.end || w.start || 0)))
      : 0;
    const lastBeatTime=chordItems.length
      ? Number(chordItems[chordItems.length-1].time || 0)
      : 0;

    const width=Math.max(
      1,
      visualXForTime(Math.max(lastWordEnd,lastBeatTime)+2)+80,
      Number(lyricLayout.right || 0)+80
    );

    lyricsTrack.style.width=width+"px";
    chordTrack.style.width=width+"px";
  }

"""

    text = replace_region(
        text,
        start_marker,
        end_marker,
        replacement,
        "moteur layout partagé",
    )

    old_render_head = """  function renderConductor(time) {
    const t=Math.max(0,Number(time || 0));
    const anchor=Math.max(90,lyricsStrip.clientWidth*.35);
    const timelineX=xForTime(t);
    const translate=anchor-timelineX;
"""
    new_render_head = """  function renderConductor(time) {
    const t=Math.max(0,Number(time || 0));
    const anchor=Math.max(90,lyricsStrip.clientWidth*.35);
    const conductorX=visualXForTime(t);
    const translate=anchor-conductorX;
"""
    text = replace_once(
        text,
        old_render_head,
        new_render_head,
        "défilement commun accords/paroles",
    )

    old_scheduler = """  function scheduleParolesLayout() {
    const relayout=() => {
      if (!lyricsTrack.isConnected || !chordTrack.isConnected) return;
      layoutConductor();
      renderConductor(currentTime());
    };

    requestAnimationFrame(relayout);
    setTimeout(relayout,80);
    setTimeout(relayout,280);

    if (document.fonts?.ready) {
      document.fonts.ready.then(() => {
        if (!lyricsTrack.isConnected) return;
        requestAnimationFrame(relayout);
      }).catch(() => {});
    }

    const observer=new ResizeObserver(() => {
      if (!lyricsStrip.isConnected) {
        try { observer.disconnect(); } catch (_) {}
        return;
      }
      if (lyricsStrip.getBoundingClientRect().width>0) {
        requestAnimationFrame(relayout);
      }
    });
    observer.observe(lyricsStrip);
  }

"""
    if old_scheduler in text:
        text = text.replace(old_scheduler, "", 1)

    old_tail = """  window.addEventListener("resize",() => {
    scheduleParolesLayout();
  });

  scheduleParolesLayout();

"""
    new_tail = """  function relayoutSharedConductor() {
    if (!lyricsTrack.isConnected || !chordTrack.isConnected) return;
    layoutConductor();
    renderConductor(currentTime());
  }

  window.addEventListener("resize",() => {
    requestAnimationFrame(relayoutSharedConductor);
  });

  requestAnimationFrame(relayoutSharedConductor);
  setTimeout(relayoutSharedConductor,80);
  setTimeout(relayoutSharedConductor,280);

  if (document.fonts?.ready) {
    document.fonts.ready.then(() => {
      if (!lyricsTrack.isConnected) return;
      requestAnimationFrame(relayoutSharedConductor);
    }).catch(() => {});
  }

"""
    text = replace_once(
        text,
        old_tail,
        new_tail,
        "relayout conducteur partagé",
    )

    text = text.replace(
        ".conductor-track {\n  position:absolute;\n  left:50%;\n",
        ".conductor-track {\n  position:absolute;\n  left:0;\n",
    )

    path.write_text(text, encoding="utf-8")


def patch_ui(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    start_marker = """                player_open = bool(
                    st.session_state.get(stem_player_open_key, False)
                )
"""
    start = text.find(start_marker)
    if start < 0:
        raise RuntimeError("bloc player lazy introuvable.")

    render_marker = """                    _render_stem_player(
                        source, all_stems,
                        preview_dir=_work_dir(audio_hash) / "browser_preview",
                        key=f"ezstem_player_{short_hash}_{len(words)}",
                        words=words,
                    )
"""
    render_at = text.find(render_marker, start)
    if render_at < 0:
        raise RuntimeError("appel _render_stem_player introuvable.")
    end = render_at + len(render_marker)

    direct = """                _render_stem_player(
                    source, all_stems,
                    preview_dir=_work_dir(audio_hash) / "browser_preview",
                    key=f"ezstem_player_{short_hash}_{len(words)}",
                    words=words,
                )
"""
    text = text[:start] + direct + text[end:]
    path.write_text(text, encoding="utf-8")


def patch_paroles_html(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    old = """        <div class="ez-row">
          <div class="ez-row-label">Chœurs</div>
          <div class="ez-track ez-backing"></div>
        </div>
"""
    new = """        <div class="ez-row ez-backing-row" style="display:none">
          <div class="ez-row-label">Chœurs</div>
          <div class="ez-track ez-backing"></div>
        </div>
"""
    text = replace_once(text, old, new, "masquage ligne textuelle Chœurs")
    path.write_text(text, encoding="utf-8")


def patch_chords_caption(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        '"Éditeur visuel R5.10 restauré : Sections / Accords / Chant / Chœurs · "',
        '"Éditeur visuel R5.10 : Sections / Accords / Chant · "',
        "caption Paroles sans Chœurs",
    )
    path.write_text(text, encoding="utf-8")


def main() -> int:
    head = git_head()
    if head != EXPECTED_HEAD:
        raise RuntimeError(
            f"HEAD inattendu: {head}\n"
            f"Attendu: {EXPECTED_HEAD}\n"
            "Ne rien appliquer : le patch est construit pour le master courant."
        )

    paths = [PLAYER, UI, HTML, CHORDS_UI]
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)

    print("Backup:", backup(paths))

    with tempfile.TemporaryDirectory(prefix="ezscore_shared_conductor_r1_") as td:
        td = Path(td)
        copies = {}
        for source in paths:
            dest = td / source.name
            shutil.copy2(source, dest)
            copies[source] = dest

        patch_player(copies[PLAYER])
        patch_ui(copies[UI])
        patch_paroles_html(copies[HTML])
        patch_chords_caption(copies[CHORDS_UI])

        ast.parse(copies[PLAYER].read_text(encoding="utf-8"), filename=str(copies[PLAYER]))
        ast.parse(copies[UI].read_text(encoding="utf-8"), filename=str(copies[UI]))
        ast.parse(copies[CHORDS_UI].read_text(encoding="utf-8"), filename=str(copies[CHORDS_UI]))

        for source, candidate in copies.items():
            shutil.copy2(candidate, source)

    print("PATCH OK")
    print(" - STEM ouvre directement le player")
    print(" - TOUS les mots du payload sont créés dans le conducteur")
    print(" - TOUS les beats/accords sont créés dans le conducteur")
    print(" - accords + paroles utilisent le même lyrics-layout.js que Paroles")
    print(" - ligne textuelle Chœurs masquée dans Paroles")
    print(" - backing_vocals audio inchangé dans le mixer STEM")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
