from __future__ import annotations

from pathlib import Path

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
  const lyricGeometryByTrack=new WeakMap();

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

    const geometry=ezLayoutLaneNodes({
      nodes,
      words:sourceWords,
      rawXForWord:(word) => timelineVisualXForTime(word.start),
      minGap:10,
      contractionGap:1,
    });

    const visualWidth=Math.max(
      sharedTimelineWidth(),
      Number(geometry.right || 0)+320
    );
    track.style.width=visualWidth+"px";

    lyricGeometryByTrack.set(track,{
      words:sourceWords,
      xs:geometry.xs,
      width:visualWidth,
    });

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

    old_translate = r'''  function translateLyricTimeline(track,viewport,time) {
    if (!track || !viewport) return;
    const anchor=viewport.clientWidth*anchorRatio;
    track.style.transform=
      "translate3d(" +
      (anchor-timelineVisualXForTime(time)).toFixed(2) +
      "px,0,0)";
  }
'''
    new_translate = r'''  function lyricVisualXForTime(track,time) {
    const geometry=lyricGeometryByTrack.get(track);
    if (!geometry) return timelineVisualXForTime(time);

    return ezVisualXForTime(
      geometry.words,
      geometry.xs,
      time,
      timelineVisualXForTime,
    );
  }

  function translateLyricTimeline(track,viewport,time) {
    if (!track || !viewport) return;
    const anchor=viewport.clientWidth*anchorRatio;
    track.style.transform=
      "translate3d(" +
      (anchor-lyricVisualXForTime(track,time)).toFixed(2) +
      "px,0,0)";
  }
'''
    if js.count(old_translate) != 1:
        raise RuntimeError(
            "Fonction translateLyricTimeline R12c introuvable ou ambiguë"
        )
    js = js.replace(old_translate, new_translate, 1)

    marker = "  // -------- One meter-aware geometry for ALL scrolling lanes --------"
    if js.count(marker) != 1:
        raise RuntimeError("Point d'injection layout partagé introuvable")

    return js.replace(marker, shared_layout_js() + "\n\n" + marker, 1)
