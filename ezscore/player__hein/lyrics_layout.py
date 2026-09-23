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
    """Enforce one immutable X=time projection for chords and lyrics.

    Contract:
      - a word is horizontally anchored at timelineVisualXForTime(word.start);
      - a chord/subdivision is horizontally anchored at its beat/subdivision;
      - visual collision handling may move lyrics vertically only;
      - no collision handler may alter horizontal time coordinates.
    """

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

    # Lyrics: X is immutable time. Collision handling is vertical only.
    geometry = r"""  let leadNodes=[];
  let backingNodes=[];

  function createLane(track, sourceWords) {
    track.innerHTML="";
    const nodes=[];
    const laneRight=[];

    sourceWords.forEach(w => {
      const span=document.createElement("span");
      span.className="lyric-token";
      span.textContent=w.text;

      const rawX=timelineVisualXForTime(w.start);
      span.style.left=rawX+"px";
      span.dataset.timelineX=String(rawX);

      track.appendChild(span);

      const width=Math.max(
        1,
        Number(
          span.getBoundingClientRect?.().width ||
          span.offsetWidth ||
          1
        )
      );

      // Never move X to solve a collision.
      // Pick the first free vertical lane while preserving rawX exactly.
      let lane=0;
      while (
        lane < laneRight.length &&
        rawX < laneRight[lane] + 10
      ) {
        lane += 1;
      }
      if (lane >= laneRight.length) {
        laneRight.push(Number.NEGATIVE_INFINITY);
      }

      span.style.top=(4 + lane*32)+"px";
      laneRight[lane]=rawX+width;
      nodes.push(span);
    });

    const laneCount=Math.max(1,laneRight.length);
    const requiredHeight=Math.max(66,laneCount*32+12);

    track.style.width=Math.max(sharedTimelineWidth(),1)+"px";
    track.style.height=requiredHeight+"px";

    const viewport=track.parentElement;
    if (viewport) {
      viewport.style.height=requiredHeight+"px";
    }

    const row=track.closest(".timeline-row");
    if (row) {
      row.style.minHeight=requiredHeight+"px";
    }

    return nodes;
  }

  function rebuildLyricGeometry() {
    leadNodes=createLane(leadTrack,leadWords);
    backingNodes=createLane(backingTrack,backingWords);
    backingRow.style.display = backingWords.length ? "grid" : "none";
  }

"""
    js = _replace_region(
        js,
        start_marker="  let leadNodes=[];\n",
        end_marker="  function activeWordIndex(sourceWords,time) {\n",
        replacement=geometry,
        label="ancrage horizontal paroles",
    )

    translate = r"""  function translateLyricTimeline(track,viewport,time) {
    if (!track || !viewport) return;
    const anchor=viewport.clientWidth*anchorRatio;

    // Same conductor projection as chords: X = timeline(time), always.
    track.style.transform=
      "translate3d(" +
      (anchor-timelineVisualXForTime(time)).toFixed(2) +
      "px,0,0)";
  }

"""
    js = _replace_region(
        js,
        start_marker="  function translateLyricTimeline(",
        end_marker="  rebuildLyricGeometry();\n",
        replacement=translate,
        label="défilement paroles timeline stricte",
    )

    # Chords: render one visual token per beat/subdivision.
    # G--- = G on beat 1, then three occupied beats.
    chord_geometry = r"""  function measureNotation(measureIndex,m) {
    const startBeat=measureIndex*m.beatsPerMeasure;
    if (startBeat>=beats.length) return null;
    const beatSlice=beats.slice(startBeat,startBeat+m.beatsPerMeasure);
    if (!beatSlice.length) return null;

    const slots=[];
    let prevChord=null;

    beatSlice.forEach((beat,localIndex) => {
      const chord=String(beat.chord || ".").trim() || ".";
      const subdivisionCount=m.grouped
        ? Math.max(1,Number(m.groups[localIndex] || 1))
        : 1;

      if (chord === ".") {
        for (let j=0;j<subdivisionCount;j++) slots.push(".");
      } else if (localIndex===0 || chord!==prevChord) {
        slots.push(chord);
        for (let j=1;j<subdivisionCount;j++) slots.push("-");
      } else {
        for (let j=0;j<subdivisionCount;j++) slots.push("-");
      }

      prevChord=chord;
    });

    const expectedSlots=m.grouped
      ? Math.max(1,Number(m.n || slots.length || 1))
      : Math.max(1,Number(m.beatsPerMeasure || slots.length || 1));

    while (slots.length<expectedSlots) {
      slots.push(prevChord && prevChord!=="." ? "-" : ".");
    }

    return {
      notation:slots.join(""),
      slots,
      start:Number(beatSlice[0].start || 0),
      end:Number(
        beatSlice[beatSlice.length-1].end ||
        beatSlice[beatSlice.length-1].start ||
        0
      ),
    };
  }

  let chordMeasures=[];
  let chordNodes=[];

  function rebuildChordTimeline() {
    const m=meter();
    const key=m.n+"/"+m.d+"|"+m.groups.join("+");
    if (key===renderedMeterKey && chordNodes.length) return;

    renderedMeterKey=key;
    chordTrack.innerHTML="";
    chordMeasures=[];
    chordNodes=[];

    const count=Math.ceil(beats.length/m.beatsPerMeasure);
    for (let i=0;i<count;i++) {
      const item=measureNotation(i,m);
      if (!item) continue;

      item.visualX=i*measureSlotWidth;
      item.visualWidth=measureSlotWidth;
      chordMeasures.push(item);

      const marker=document.createElement("span");
      marker.className="chord-marker";
      marker.style.left=item.visualX+"px";
      marker.style.width=Math.max(36,item.visualWidth-12)+"px";
      marker.style.boxSizing="border-box";
      marker.style.overflow="visible";
      marker.style.padding="0";

      const slotCount=Math.max(1,item.slots.length);
      item.slots.forEach((token,slotIndex) => {
        const slot=document.createElement("span");
        slot.className="chord-beat-token";
        slot.textContent=token;
        slot.style.position="absolute";
        slot.style.left=((slotIndex/slotCount)*100)+"%";
        slot.style.top="3px";
        slot.style.width=(100/slotCount)+"%";
        slot.style.boxSizing="border-box";
        slot.style.font="inherit";
        slot.style.fontWeight="inherit";
        slot.style.whiteSpace="nowrap";
        slot.style.pointerEvents="none";
        marker.appendChild(slot);
      });

      chordTrack.appendChild(marker);
      chordNodes.push(marker);
    }

    chordTrack.style.width=sharedTimelineWidth()+"px";
  }

"""
    js = _replace_region(
        js,
        start_marker="  function measureNotation(measureIndex,m) {\n",
        end_marker="  function chordVisualXForTime(time) {\n",
        replacement=chord_geometry,
        label="accords par temps",
    )

    # Keep the shared helper library available to older presentation paths,
    # but R12c no longer uses its horizontal collision shifting.
    marker = "  // -------- One meter-aware geometry for ALL scrolling lanes --------"
    if js.count(marker) != 1:
        raise RuntimeError("Point d'injection layout partagé introuvable")
    return js.replace(marker, shared_layout_js() + "\n\n" + marker, 1)
