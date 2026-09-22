from __future__ import annotations
import ast
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "ezscore/player/stem_analysis_conductor.py"


def backup(path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    preferred = Path(r"H:\temp")
    base = preferred if preferred.exists() else Path.home() / "AppData" / "Local" / "Temp"
    out = base / f"EZScore_STEM_USE_PAROLES_LAYOUT_R1_backup_{stamp}"
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, out)
    return out


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: attendu 1 motif, trouvé {count}.")
    return text.replace(old, new, 1)


def patch(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    text = replace_once(
        text,
        ".conductor-track {\n  position:absolute;\n  left:50%;\n",
        ".conductor-track {\n  position:absolute;\n  left:0;\n",
        "origine timeline conducteur",
    )

    start = text.find("  let pixelsPerSecond=96;\n")
    end = text.find("  function findWordIndex(time) {\n", start)
    if start < 0 or end < 0:
        raise RuntimeError("bloc layout conducteur introuvable.")

    new_layout = """  // Same visual layout contract as Analyse > Paroles.
  const pixelsPerSecond=100;
  let lyricVisualXs=[];

  function xForTime(time) {
    return Math.max(0,Number(time || 0))*pixelsPerSecond;
  }

  function ezIsContractionSuffix(text) {
    return /^[\\'’]/.test(String(text || "").trim());
  }

  function ezNodeWidth(node) {
    if (!node) return 0;
    const rectWidth=Number(node.getBoundingClientRect?.().width || 0);
    const offsetWidth=Number(node.offsetWidth || 0);
    const scrollWidth=Number(node.scrollWidth || 0);
    return Math.max(rectWidth,offsetWidth,scrollWidth,0);
  }

  function layoutWordsLikeParoles() {
    const xs=[];
    let previousRight=Number.NEGATIVE_INFINITY;

    lyricNodes.forEach((node,index) => {
      const word=words[index] || {};
      const rawX=xForTime(word.start);
      let visualX=rawX;

      const isSuffix=(
        index>0 &&
        ezIsContractionSuffix(word.text)
      );

      if (index>0) {
        const previous=lyricNodes[index-1];
        const previousLeft=Number.parseFloat(previous?.style.left || "0");
        const previousWidth=ezNodeWidth(previous);

        visualX=isSuffix
          ? previousLeft + Math.max(1,previousWidth) + 1
          : Math.max(rawX,previousRight + 10);
      }

      node.style.left=visualX+"px";
      node.dataset.timelineX=String(rawX);

      const width=ezNodeWidth(node);
      previousRight=visualX + Math.max(1,width);
      xs.push(visualX);
    });

    lyricVisualXs=xs;
    return Number.isFinite(previousRight) ? previousRight : 0;
  }

  function layoutConductor() {
    const lyricRight=layoutWordsLikeParoles();

    chordNodes.forEach((node,index) => {
      node.style.left=xForTime(chordItems[index].time)+"px";
      node.dataset.timelineX=String(xForTime(chordItems[index].time));
    });

    const lastWordEnd=words.length
      ? Math.max(...words.map(w=>Number(w.end || w.start || 0)))
      : 0;
    const lastBeatTime=chordItems.length
      ? Number(chordItems[chordItems.length-1].time || 0)
      : 0;

    const rawRight=xForTime(Math.max(lastWordEnd,lastBeatTime)+2);
    const width=Math.max(rawRight,lyricRight+40,1);

    lyricsTrack.style.width=width+"px";
    chordTrack.style.width=width+"px";
  }

  function scheduleParolesLayout() {
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
    text = text[:start] + new_layout + text[end:]

    old_render = (
        '  function renderConductor(time) {\n'
        '    const t=Math.max(0,Number(time || 0));\n'
        '    const anchor=Math.max(90,lyricsStrip.clientWidth*.35);\n'
        '    const translate=anchor-xForTime(t);\n'
        '\n'
        '    lyricsTrack.style.transform="translate3d("+translate.toFixed(2)+"px,0,0)";\n'
        '    chordTrack.style.transform="translate3d("+translate.toFixed(2)+"px,0,0)";\n'
    )
    new_render = (
        '  function renderConductor(time) {\n'
        '    const t=Math.max(0,Number(time || 0));\n'
        '    const anchor=Math.max(90,lyricsStrip.clientWidth*.35);\n'
        '    const timelineX=xForTime(t);\n'
        '    const translate=anchor-timelineX;\n'
        '\n'
        '    lyricsTrack.style.transform="translate3d("+translate.toFixed(2)+"px,0,0)";\n'
        '    chordTrack.style.transform="translate3d("+translate.toFixed(2)+"px,0,0)";\n'
    )
    text = replace_once(text, old_render, new_render, "défilement timeline Paroles")

    old_tail = (
        '  window.addEventListener("resize",() => {\n'
        '    layoutConductor();\n'
        '    renderConductor(currentTime());\n'
        '  });\n'
        '\n'
        '  requestAnimationFrame(() => {\n'
        '    layoutConductor();\n'
        '    renderConductor(0);\n'
        '  });\n'
        '\n'
    )
    new_tail = (
        '  window.addEventListener("resize",() => {\n'
        '    scheduleParolesLayout();\n'
        '  });\n'
        '\n'
        '  scheduleParolesLayout();\n'
        '\n'
    )
    text = replace_once(text, old_tail, new_tail, "layout visibility-safe")

    path.write_text(text, encoding="utf-8")


def main() -> int:
    if not TARGET.is_file():
        raise FileNotFoundError(TARGET)

    print("Backup:", backup(TARGET))

    with tempfile.TemporaryDirectory(prefix="ezscore_stem_paroles_layout_") as td:
        candidate = Path(td) / TARGET.name
        shutil.copy2(TARGET, candidate)
        patch(candidate)
        ast.parse(candidate.read_text(encoding="utf-8"), filename=str(candidate))
        shutil.copy2(candidate, TARGET)

    print("PATCH OK")
    print(" - conducteur STEM utilise l'échelle Paroles : 100 px/s")
    print(" - collision des mots identique à Paroles (10 px, contractions 1 px)")
    print(" - origine de piste corrigée : x=0")
    print(" - relayout après fonts / resize / montage caché")
    print(" - timeline audio inchangée")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
