from __future__ import annotations

from pathlib import Path

from ezscore.player.choir_vocalises import install_choir_vocalise_patch


install_choir_vocalise_patch()


_TEMPLATE = (
    Path(__file__).resolve().parents[2]
    / "templates"
    / "views"
    / "lyrics-layout.js"
)


def shared_layout_js() -> str:
    if not _TEMPLATE.is_file():
        raise RuntimeError(f"Template EZScore manquant : {_TEMPLATE}")
    return _TEMPLATE.read_text(encoding="utf-8")


def _replace_region(
    source: str,
    *,
    start_marker: str,
    end_marker: str,
    replacement: str,
    label: str,
) -> str:
    start = source.find(start_marker)
    if start < 0:
        raise RuntimeError(f"Début de région introuvable : {label}")
    end = source.find(end_marker, start)
    if end < 0:
        raise RuntimeError(f"Fin de région introuvable : {label}")
    if source.find(start_marker, start + 1) >= 0:
        raise RuntimeError(f"Début de région ambigu : {label}")
    return source[:start] + replacement + source[end:]


def patch_player_js(js: str) -> str:
    replacement = r'''  let leadNodes=[];
  let backingNodes=[];

  function createLane(track, sourceWords) {
    track.innerHTML="";
    const nodes=[];

    sourceWords.forEach(w => {
      const span=document.createElement("span");
      span.className="lyric-token";
      span.textContent=w.text;
      span.style.left=timelineVisualXForTime(w.start)+"px";
      track.appendChild(span);
      nodes.push(span);
    });

    track.style.width=Math.max(sharedTimelineWidth(),1)+"px";
    return nodes;
  }

  function rebuildLyricGeometry() {
    leadNodes=createLane(leadTrack,leadWords);
    backingNodes=createLane(backingTrack,backingWords);
    backingRow.style.display = backingWords.length ? "grid" : "none";
  }

'''
    js = _replace_region(
        js,
        start_marker="  let leadNodes=[];\n",
        end_marker="  function activeWordIndex(sourceWords,time) {\n",
        replacement=replacement,
        label="géométrie createLane",
    )

    marker = "  // -------- One meter-aware geometry for ALL scrolling lanes --------"
    if js.count(marker) != 1:
        raise RuntimeError("Point d'injection layout partagé introuvable")

    return js.replace(marker, shared_layout_js() + "\n\n" + marker, 1)
