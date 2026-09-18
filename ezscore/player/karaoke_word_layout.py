from __future__ import annotations

import streamlit as st

_PATCHED_COMPONENT_NAME = "ezscore_karaoke_stem_player_r12c_word_layout"


def _patch_js(js: str) -> str:
    old = r'''  let leadNodes=[];
  let backingNodes=[];

  function createLane(track, sourceWords) {
    track.innerHTML="";
    track.style.width=sharedTimelineWidth()+"px";
    return sourceWords.map(w => {
      const span=document.createElement("span");
      span.className="lyric-token";
      span.textContent=w.text;
      span.style.left=timelineVisualXForTime(w.start)+"px";
      track.appendChild(span);
      return span;
    });
  }

  function rebuildLyricGeometry() {
    leadNodes=createLane(leadTrack,leadWords);
    backingNodes=createLane(backingTrack,backingWords);
    backingRow.style.display = backingWords.length ? "grid" : "none";
  }

  function activeWordIndex(sourceWords,time) {
    if (!sourceWords.length) return -1;
    let low=0,high=sourceWords.length-1,answer=-1;
    while (low<=high) {
      const mid=(low+high)>>1;
      if (sourceWords[mid].start<=time) {
        answer=mid;
        low=mid+1;
      } else {
        high=mid-1;
      }
    }
    if (answer<0) return -1;
    const w=sourceWords[answer];
    return time<=Math.max(w.end,w.start+.06) ? answer : -1;
  }

  function translateLyricTimeline(track,viewport,time) {
    if (!track || !viewport) return;
    const anchor=viewport.clientWidth*anchorRatio;
    track.style.transform=
      "translate3d(" +
      (anchor-timelineVisualXForTime(time)).toFixed(2) +
      "px,0,0)";
  }

  rebuildLyricGeometry();
'''

    new = r'''  let leadNodes=[];
  let backingNodes=[];
  const lyricGeometryByTrack=new WeakMap();

  function createLane(track, sourceWords) {
    track.innerHTML="";

    const nodes=[];
    const visualXs=[];
    let previousRight=Number.NEGATIVE_INFINITY;

    sourceWords.forEach(w => {
      const span=document.createElement("span");
      span.className="lyric-token";
      span.textContent=w.text;

      const rawX=timelineVisualXForTime(w.start);
      span.style.left=rawX+"px";
      track.appendChild(span);

      const width=Math.max(12,span.getBoundingClientRect().width);
      const visualX=Math.max(rawX,previousRight+10);
      span.style.left=visualX+"px";
      span.dataset.timelineX=String(rawX);

      previousRight=visualX+width;
      visualXs.push(visualX);
      nodes.push(span);
    });

    const visualWidth=Math.max(
      sharedTimelineWidth(),
      Number.isFinite(previousRight) ? previousRight+320 : 1
    );
    track.style.width=visualWidth+"px";

    lyricGeometryByTrack.set(track,{
      words:sourceWords,
      xs:visualXs,
      width:visualWidth,
    });

    return nodes;
  }

  function rebuildLyricGeometry() {
    leadNodes=createLane(leadTrack,leadWords);
    backingNodes=createLane(backingTrack,backingWords);
    backingRow.style.display = backingWords.length ? "grid" : "none";
  }

  function activeWordIndex(sourceWords,time) {
    if (!sourceWords.length) return -1;
    let low=0,high=sourceWords.length-1,answer=-1;
    while (low<=high) {
      const mid=(low+high)>>1;
      if (sourceWords[mid].start<=time) {
        answer=mid;
        low=mid+1;
      } else {
        high=mid-1;
      }
    }
    if (answer<0) return -1;
    const w=sourceWords[answer];
    return time<=Math.max(w.end,w.start+.06) ? answer : -1;
  }

  function lyricVisualXForTime(track,time) {
    const geometry=lyricGeometryByTrack.get(track);
    if (
      !geometry ||
      !geometry.words.length ||
      geometry.words.length!==geometry.xs.length
    ) {
      return timelineVisualXForTime(time);
    }

    const words=geometry.words;
    const xs=geometry.xs;
    const t=Number(time || 0);

    if (words.length===1) return xs[0];

    if (t<=words[0].start) {
      const firstTime=Math.max(.001,Number(words[0].start || 0));
      const progress=Math.max(0,Math.min(1,t/firstTime));
      return Math.max(0,xs[0]*progress);
    }

    let low=0,high=words.length-1,left=0;
    while (low<=high) {
      const mid=(low+high)>>1;
      if (words[mid].start<=t) {
        left=mid;
        low=mid+1;
      } else {
        high=mid-1;
      }
    }

    if (left>=words.length-1) {
      const last=words.length-1;
      return xs[last]+Math.max(0,t-words[last].start)*28;
    }

    const ta=Number(words[left].start || 0);
    const tb=Math.max(ta+.04,Number(words[left+1].start || ta+.04));
    const progress=Math.max(0,Math.min(1,(t-ta)/(tb-ta)));

    return xs[left]+(xs[left+1]-xs[left])*progress;
  }

  function translateLyricTimeline(track,viewport,time) {
    if (!track || !viewport) return;
    const anchor=viewport.clientWidth*anchorRatio;
    track.style.transform=
      "translate3d(" +
      (anchor-lyricVisualXForTime(track,time)).toFixed(2) +
      "px,0,0)";
  }

  rebuildLyricGeometry();
'''

    count = js.count(old)
    if count != 1:
        raise RuntimeError(
            f"Bloc géométrie R12c inattendu : {count} occurrence(s), attendu 1."
        )
    js = js.replace(old, new, 1)

    # The transport slider must work before the first Play click. Loading
    # metadata from the original preview is sufficient; no AudioContext and
    # no playback are started.
    state_marker = """  let duration = 0;
  let raf = null;
"""
    state_replacement = """  let duration = 0;
  let raf = null;
  let metadataMedia = null;
"""
    if js.count(state_marker) != 1:
        raise RuntimeError("État duration R12c introuvable.")
    js = js.replace(state_marker, state_replacement, 1)

    fmt_marker = """  function fmt(seconds) {
    const t = Math.max(0, Number(seconds) || 0);
    const m = Math.floor(t / 60);
    return m + ":" + String(Math.floor(t % 60)).padStart(2,"0");
  }
"""
    fmt_replacement = fmt_marker + r"""
  function primeSeekMetadata() {
    const original = defs.find(item => item.name === "original") || defs[0];
    const url = String(original?.url || "");
    if (!url) return;

    metadataMedia = new Audio();
    metadataMedia.preload = "metadata";
    metadataMedia.src = url;

    const accept = () => {
      const value = Number(metadataMedia?.duration || 0);
      if (!Number.isFinite(value) || value <= 0) return;

      duration = value;
      seek.max = String(Math.max(.001, duration));
      seek.value = String(Math.max(0, Math.min(duration, position)));
      timeLabel.textContent = fmt(position) + " / " + fmt(duration);
    };

    metadataMedia.addEventListener("loadedmetadata", accept, {once:true});
    metadataMedia.addEventListener("durationchange", accept);
    try { metadataMedia.load(); } catch (_) {}
  }

  primeSeekMetadata();
"""
    if js.count(fmt_marker) != 1:
        raise RuntimeError("Fonction fmt R12c introuvable.")
    js = js.replace(fmt_marker, fmt_replacement, 1)

    return js


def install() -> None:
    from ezscore.player import karaoke_stem_webaudio as base
    from ezscore.player import karaoke_stem_webaudio_r12c as r12c

    if getattr(r12c, "_EZ_WORD_LAYOUT_PATCH", False):
        return

    # A second Whisper pass on the isolated vocals can recover words omitted
    # by the mix transcription. That does NOT prove they are backing vocals.
    # Keep those recovered words in the lead lane; true backing-vocal
    # detection must come from an explicit source, not from a transcription gap.
    base._supplement_only_words = lambda original_words, merged_words: []

    patched_js = _patch_js(str(r12c._JS))

    lead_marker = (
        '  const leadInput = Array.isArray(data.lead_words) '
        '? data.lead_words : words;'
    )
    if patched_js.count(lead_marker) != 1:
        raise RuntimeError("Sélection leadInput R12c introuvable.")
    patched_js = patched_js.replace(
        lead_marker,
        '  const leadInput = words.length ? words : '
        '(Array.isArray(data.lead_words) ? data.lead_words : []);',
        1,
    )
    r12c._COMPONENT_R12C = st.components.v2.component(
        _PATCHED_COMPONENT_NAME,
        html=r12c._HTML,
        css=r12c._CSS,
        js=patched_js,
        isolate_styles=True,
    )
    r12c._EZ_WORD_LAYOUT_PATCH = True
