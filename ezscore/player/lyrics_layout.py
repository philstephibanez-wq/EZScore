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
    normalized = r"""  function normalizedWords(input) {
    const ordered=(Array.isArray(input) ? input : [])
      .map(w => ({
        text:String(w.text || "").trim(),
        start:Number(w.start || 0),
        end:Number(w.end || w.start || 0),
      }))
      .filter(w => w.text && Number.isFinite(w.start) && Number.isFinite(w.end))
      .sort((a,b)=>a.start-b.start || a.end-b.end);

    const merged=[];
    ordered.forEach(w => {
      const previous=merged.length ? merged[merged.length-1] : null;
      const contraction=Boolean(
        previous && (
          /['’]$/.test(previous.text) ||
          /^['’]/.test(w.text)
        )
      );

      if (contraction) {
        previous.text=previous.text+w.text;
        previous.start=Math.min(previous.start,w.start);
        previous.end=Math.max(previous.end,w.end);
      } else {
        merged.push({...w});
      }
    });
    return merged;
  }

"""
    js = _replace_region(
        js,
        start_marker="  function normalizedWords(input) {\n",
        end_marker="  const leadWords = normalizedWords(leadInput);\n",
        replacement=normalized,
        label="normalisation paroles",
    )

    replacement = r"""  let leadNodes=[];
  let backingNodes=[];
  let leadVisualXs=[];
  let backingVisualXs=[];

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

    const layout=ezLayoutLaneNodes({
      nodes,
      words:sourceWords,
      rawXForWord:(word)=>timelineVisualXForTime(word.start),
      minGap:12,
      contractionGap:1,
    });

    track.style.width=
      Math.max(sharedTimelineWidth(),layout.right+260,1)+"px";

    return {nodes,xs:layout.xs};
  }

  function rebuildLyricGeometry() {
    const leadLayout=createLane(leadTrack,leadWords);
    leadNodes=leadLayout.nodes;
    leadVisualXs=leadLayout.xs;

    const backingLayout=createLane(backingTrack,backingWords);
    backingNodes=backingLayout.nodes;
    backingVisualXs=backingLayout.xs;

    backingRow.style.display = backingWords.length ? "grid" : "none";
  }

"""
    js = _replace_region(
        js,
        start_marker="  let leadNodes=[];\n",
        end_marker="  function activeWordIndex(sourceWords,time) {\n",
        replacement=replacement,
        label="géométrie paroles sans chevauchement",
    )

    translate = r"""  function translateLyricTimeline(
    track,
    viewport,
    time,
    sourceWords,
    visualXs
  ) {
    if (!track || !viewport) return;
    const anchor=viewport.clientWidth*anchorRatio;
    const visualX=ezVisualXForTime(
      sourceWords,
      visualXs,
      time,
      timelineVisualXForTime
    );
    track.style.transform=
      "translate3d("+(anchor-visualX).toFixed(2)+"px,0,0)";
  }

"""
    js = _replace_region(
        js,
        start_marker="  function translateLyricTimeline(track,viewport,time) {\n",
        end_marker="  rebuildLyricGeometry();\n",
        replacement=translate,
        label="défilement paroles sans chevauchement",
    )

    js = js.replace(
        "translateLyricTimeline(leadTrack,leadViewport,time);",
        "translateLyricTimeline(leadTrack,leadViewport,time,leadWords,leadVisualXs);",
    )
    js = js.replace(
        "translateLyricTimeline(backingTrack,backingViewport,time);",
        "translateLyricTimeline(backingTrack,backingViewport,time,backingWords,backingVisualXs);",
    )

    marker = "  // -------- One meter-aware geometry for ALL scrolling lanes --------"
    if js.count(marker) != 1:
        raise RuntimeError("Point d'injection layout partagé introuvable")

    return js.replace(marker, shared_layout_js() + "\n\n" + marker, 1)
