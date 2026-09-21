from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st

from ezscore.analysis.stems import STEM_NAMES
from ezscore.guitar import (
    choices as guitar_choices,
    get_voicing,
    load_show_diagrams,
    load_voicings,
    svg as guitar_svg,
)
from ezscore.player.media_url import register_media_url
from ezscore.player import stem_webaudio as base


def _replace_once(source: str, old: str, new: str, label: str) -> str:
    if source.count(old) != 1:
        raise RuntimeError(
            f"Patch STEM conductor ambigu/introuvable: {label} "
            f"(occurrences={source.count(old)})"
        )
    return source.replace(old, new, 1)


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
        raise RuntimeError(f"Début introuvable: {label}")
    end = source.find(end_marker, start)
    if end < 0:
        raise RuntimeError(f"Fin introuvable: {label}")
    return source[:start] + replacement + source[end:]


_PLAYER_HTML = _replace_once(
    base._PLAYER_HTML,
    '''  <div class="lyrics-wrap">
    <div class="lyrics-title">Paroles synchronisées</div>
    <div class="lyrics-strip"><div class="lyrics-track"></div></div>
  </div>
''',
    '''  <div class="conductor-wrap">
    <div class="conductor-head">
      <strong>Conducteur continu</strong>
      <label class="diagram-toggle">
        <input class="diagram-checkbox" type="checkbox">
        Diagrammes guitare
      </label>
    </div>

    <div class="conductor-row chord-row">
      <div class="conductor-label">Accords</div>
      <div class="conductor-strip chord-strip">
        <div class="conductor-track chord-track"></div>
      </div>
    </div>

    <div class="conductor-row lyric-row">
      <div class="conductor-label">Paroles</div>
      <div class="conductor-strip lyrics-strip">
        <div class="conductor-track lyrics-track"></div>
      </div>
    </div>

    <div class="current-diagram"></div>
  </div>
''',
    "HTML conducteur 2 lignes",
)


_PLAYER_CSS = base._PLAYER_CSS + r'''

.lyrics-wrap { display:none !important; }

.conductor-wrap {
  margin-top:14px;
  padding-top:10px;
  border-top:1px solid color-mix(in srgb, var(--st-text-color) 18%, transparent);
}
.conductor-head {
  display:flex;
  justify-content:flex-start;
  align-items:center;
  gap:18px;
  margin-bottom:7px;
  font-size:12px;
}
.diagram-toggle {
  display:flex;
  align-items:center;
  gap:6px;
  font-size:11px;
  font-weight:600;
  white-space:nowrap;
}
.conductor-row {
  display:grid;
  grid-template-columns:72px 1fr;
  align-items:center;
  min-height:48px;
}
.conductor-label {
  font-size:11px;
  font-weight:900;
  opacity:.72;
  padding-right:8px;
}
.conductor-strip {
  position:relative;
  overflow:hidden;
  height:46px;
  border-radius:7px;
  background:color-mix(in srgb, var(--st-text-color) 5%, transparent);
}
.conductor-track {
  position:absolute;
  left:50%;
  top:0;
  height:46px;
  white-space:nowrap;
  transition:transform 70ms linear;
  will-change:transform;
}
.chord-token,
.lyric-word {
  position:absolute;
  top:50%;
  transform:translateY(-50%);
  white-space:nowrap;
}
.chord-token {
  font-size:17px;
  font-weight:850;
  opacity:.82;
  font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
.chord-token.measure-start { font-weight:950; }
.chord-token.current {
  opacity:1;
  text-decoration:underline;
  text-underline-offset:4px;
}
.lyric-word {
  margin:0;
  font-size:18px;
  opacity:.34;
  transition:opacity 70ms linear, font-weight 70ms linear;
}
.lyric-word.past { opacity:.50; }
.lyric-word.current { opacity:1; font-weight:900; }

.current-diagram {
  display:none;
  min-height:0;
  margin-top:8px;
  justify-content:center;
  align-items:center;
}
.current-diagram.visible {
  display:flex;
  min-height:128px;
}
.current-diagram svg {
  max-height:124px;
  width:auto;
}

@media(max-width:700px) {
  .conductor-row { grid-template-columns:58px 1fr; }
  .conductor-label { font-size:10px; }
}
'''


_JS = base._PLAYER_JS

_JS = _replace_once(
    _JS,
    '''  const lyricsWrap = root.querySelector(".lyrics-wrap");
  const lyricsStrip = root.querySelector(".lyrics-strip");
  const lyricsTrack = root.querySelector(".lyrics-track");

  const defs = Array.isArray(data.tracks) ? data.tracks : [];
  const words = Array.isArray(data.words) ? data.words : [];
''',
    '''  const conductorWrap = root.querySelector(".conductor-wrap");
  const chordStrip = root.querySelector(".chord-strip");
  const chordTrack = root.querySelector(".chord-track");
  const lyricsStrip = root.querySelector(".lyrics-strip");
  const lyricsTrack = root.querySelector(".lyrics-track");
  const diagramCheckbox = root.querySelector(".diagram-checkbox");
  const currentDiagram = root.querySelector(".current-diagram");

  const defs = Array.isArray(data.tracks) ? data.tracks : [];
  const rawWords = Array.isArray(data.words) ? data.words : [];
  const beats = Array.isArray(data.beats) ? data.beats : [];
  const beatsPerMeasure = Math.max(1, Number(data.beats_per_measure || 4));
  const chordDiagrams = data.chord_diagrams || {};
  const diagramStorageKey = String(data.diagram_storage_key || "ezscore-stem-diagrams");
  let showDiagrams = Boolean(data.show_diagrams);
''',
    "sélecteurs/data conducteur",
)

_JS = _JS.replace("renderLyrics(0);", "renderConductor(0);")
_JS = _JS.replace("renderLyrics(t);", "renderConductor(t);")

conductor_js = r'''  // Continuous STEM conductor: one chord row + one lyric row.

  function normalizedWords(input) {
    const sorted=(Array.isArray(input) ? input : [])
      .map(w => ({
        text:String(w.text || "").trim(),
        start:Number(w.start || 0),
        end:Number(w.end ?? w.start ?? 0),
      }))
      .filter(w =>
        w.text &&
        Number.isFinite(w.start) &&
        Number.isFinite(w.end) &&
        w.end >= w.start
      )
      .sort((a,b)=>a.start-b.start || a.end-b.end);

    const merged=[];
    sorted.forEach(w => {
      const previous=merged.length ? merged[merged.length-1] : null;
      if (previous && Math.abs(w.start-previous.start) <= .005) {
        previous.text=(previous.text+" "+w.text).trim();
        previous.end=Math.max(previous.end,w.end);
      } else {
        merged.push({...w});
      }
    });
    return merged;
  }

  const words=normalizedWords(rawWords);

  function vocalDisplayText(word) {
    const text=String(word.text || "").trim();
    const duration=Math.max(0,Number(word.end || 0)-Number(word.start || 0));
    const letters=Math.max(1,(text.match(/[A-Za-zÀ-ÖØ-öø-ÿĀ-ž]/g) || []).length);
    const expected=Math.min(.72,.24 + letters*.055);
    const excess=Math.max(0,duration-expected);
    const count=excess >= .24
      ? Math.min(8,Math.max(1,Math.round(excess/.22)))
      : 0;
    return text + "_".repeat(count);
  }

  const lyricNodes=words.map(word => {
    const span=document.createElement("span");
    span.className="lyric-word";
    span.textContent=vocalDisplayText(word);
    lyricsTrack.appendChild(span);
    return span;
  });

  function chordAt(index) {
    return String(beats[index]?.chord || ".").trim() || ".";
  }

  const chordItems=beats.map((beat,index) => {
    const localBeat=index % beatsPerMeasure;
    const chord=chordAt(index);
    const previous=index>0 ? chordAt(index-1) : ".";
    const token=localBeat===0
      ? chord
      : (chord===previous && chord!=="." ? "-" : chord);

    return {
      index,
      time:Number(beat.time ?? beat.start ?? 0),
      chord,
      token,
      measureStart:localBeat===0,
    };
  }).filter(item => Number.isFinite(item.time));

  const chordNodes=[];
  chordItems.forEach(item => {
    const span=document.createElement("span");
    span.className="chord-token" + (item.measureStart ? " measure-start" : "");
    span.textContent=item.token;
    chordTrack.appendChild(span);
    chordNodes.push(span);
  });

  let pixelsPerSecond=96;

  function computeGlobalScale() {
    let required=96;
    for (let i=0;i<words.length-1;i++) {
      const dt=Number(words[i+1].start)-Number(words[i].start);
      if (!(dt > .005)) continue;

      const width=Math.max(
        1,
        Number(
          lyricNodes[i]?.getBoundingClientRect?.().width ||
          lyricNodes[i]?.offsetWidth ||
          1
        )
      );
      required=Math.max(required,(width+16)/dt);
    }
    pixelsPerSecond=Math.max(96,required);
  }

  function xForTime(time) {
    return Math.max(0,Number(time || 0))*pixelsPerSecond;
  }

  function layoutConductor() {
    computeGlobalScale();

    lyricNodes.forEach((node,index) => {
      node.style.left=xForTime(words[index].start)+"px";
    });

    chordNodes.forEach((node,index) => {
      node.style.left=xForTime(chordItems[index].time)+"px";
    });

    const lastWordEnd=words.length
      ? Math.max(...words.map(w=>Number(w.end || w.start || 0)))
      : 0;
    const lastBeatTime=chordItems.length
      ? Number(chordItems[chordItems.length-1].time || 0)
      : 0;
    const width=xForTime(Math.max(lastWordEnd,lastBeatTime)+4);

    lyricsTrack.style.width=Math.max(1,width)+"px";
    chordTrack.style.width=Math.max(1,width)+"px";
  }

  function findWordIndex(time) {
    if (!words.length) return -1;
    let low=0,high=words.length-1,answer=-1;
    while (low<=high) {
      const middle=(low+high)>>1;
      if (words[middle].start<=time) {
        answer=middle;
        low=middle+1;
      } else {
        high=middle-1;
      }
    }
    return answer;
  }

  function findBeatIndex(time) {
    if (!chordItems.length) return -1;
    let low=0,high=chordItems.length-1,answer=-1;
    while (low<=high) {
      const middle=(low+high)>>1;
      if (chordItems[middle].time<=time) {
        answer=middle;
        low=middle+1;
      } else {
        high=middle-1;
      }
    }
    return answer;
  }

  function updateDiagram(beatIndex) {
    if (!currentDiagram) return;
    if (!showDiagrams || beatIndex<0 || !chordItems[beatIndex]) {
      currentDiagram.classList.remove("visible");
      currentDiagram.innerHTML="";
      return;
    }

    const chord=String(chordItems[beatIndex].chord || ".");
    const svg=String(chordDiagrams[chord] || "");
    if (!svg) {
      currentDiagram.classList.remove("visible");
      currentDiagram.innerHTML="";
      return;
    }

    currentDiagram.innerHTML=svg;
    currentDiagram.classList.add("visible");
  }

  function renderConductor(time) {
    const t=Math.max(0,Number(time || 0));
    const anchor=Math.max(90,lyricsStrip.clientWidth*.35);
    const translate=anchor-xForTime(t);

    lyricsTrack.style.transform="translate3d("+translate.toFixed(2)+"px,0,0)";
    chordTrack.style.transform="translate3d("+translate.toFixed(2)+"px,0,0)";

    const wordIndex=findWordIndex(t);
    if (wordIndex!==activeWordIndex) {
      activeWordIndex=wordIndex;
      lyricNodes.forEach((node,index) => {
        node.classList.toggle("past",index<wordIndex);
        node.classList.toggle("current",index===wordIndex);
      });
    }

    const beatIndex=findBeatIndex(t);
    chordNodes.forEach((node,index) => {
      node.classList.toggle("current",index===beatIndex);
    });
    updateDiagram(beatIndex);
  }

  if (!words.length && !chordItems.length) {
    conductorWrap.style.display="none";
  } else {
    layoutConductor();
  }

  try {
    const saved=localStorage.getItem(diagramStorageKey);
    if (saved==="1" || saved==="0") {
      showDiagrams=saved==="1";
    }
  } catch (_) {}

  diagramCheckbox.checked=showDiagrams;
  diagramCheckbox.addEventListener("change",() => {
    showDiagrams=Boolean(diagramCheckbox.checked);
    try {
      localStorage.setItem(diagramStorageKey,showDiagrams ? "1" : "0");
    } catch (_) {}
    renderConductor(currentTime());
  });

  window.addEventListener("resize",() => {
    layoutConductor();
    renderConductor(currentTime());
  });

  renderConductor(0);

'''

_JS = _replace_region(
    _JS,
    start_marker="  const lyricNodes = words.map((word) => {\n",
    end_marker="  function tick() {\n",
    replacement=conductor_js,
    label="moteur conducteur continu",
)

_JS = _JS.replace("    renderLyrics(t);", "    renderConductor(t);")


_STEM_CONDUCTOR = st.components.v2.component(
    "ezscore_stem_analysis_conductor_r1",
    html=_PLAYER_HTML,
    css=_PLAYER_CSS,
    js=_JS,
    isolate_styles=True,
)


def _load_structure(preview_dir: Path) -> dict[str, Any]:
    path = Path(preview_dir).parent / "structure_analysis.json"
    if not path.is_file():
        return {}
    try:
        return dict(json.loads(path.read_text(encoding="utf-8")) or {})
    except Exception:
        return {}


def _build_chord_diagrams(
    audio_hash: str,
    beats: list[dict[str, Any]],
) -> dict[str, str]:
    saved = load_voicings(audio_hash)
    diagrams: dict[str, str] = {}

    for beat in beats:
        symbol = str(beat.get("chord", "") or "").strip()
        if not symbol or symbol == "." or symbol in diagrams:
            continue

        candidates = [symbol]
        if "/" in symbol:
            base_symbol = symbol.split("/", 1)[0].strip()
            if base_symbol and base_symbol not in candidates:
                candidates.append(base_symbol)

        for candidate in candidates:
            available = guitar_choices(candidate)
            if not available:
                continue

            selected_name = saved.get(symbol) or saved.get(candidate)
            voicing = get_voicing(
                candidate,
                selected_name if selected_name else available[0].name,
            )
            if voicing is None:
                continue

            diagrams[symbol] = guitar_svg(
                symbol,
                voicing,
                width=92,
                height=118,
            )
            break

    return diagrams


def render_player(
    source: Path,
    stems: dict[str, Path],
    *,
    preview_dir: Path,
    key: str,
    words: list[dict[str, Any]] | None = None,
) -> None:
    st.caption(
        "Préparation/chargement du lecteur STEM… "
        "Accords et paroles partagent une timeline continue."
    )

    previews = base.prepare_browser_previews(source, stems, preview_dir)
    tracks: list[dict[str, Any]] = []

    def pack(
        name: str,
        label: str,
        path: Path,
        enabled: bool,
        volume: float,
    ) -> None:
        preview = previews[name]
        media_url = register_media_url(
            preview,
            coordinates=f"{key}:stem:{name}",
            mimetype="audio/mpeg",
        )
        tracks.append(
            {
                "name": name,
                "label": label,
                "mime": "audio/mpeg",
                "url": media_url,
                "enabled": enabled,
                "volume": volume,
                "low": 0.0,
                "mid": 0.0,
                "high": 0.0,
                "source_bytes": int(path.stat().st_size),
                "preview_bytes": int(preview.stat().st_size),
            }
        )

    pack("original", "Original", source, True, 0.75)

    defaults = {
        "vocals": (True, 0.90),
        "drums": (False, 0.75),
        "bass": (False, 0.75),
        "other": (False, 0.75),
    }
    labels = {
        "vocals": "Chant",
        "drums": "Batterie",
        "bass": "Basse",
        "other": "Other",
    }

    for name in STEM_NAMES:
        if name in stems:
            enabled, volume = defaults[name]
            pack(name, labels[name], stems[name], enabled, volume)

    for name, label, enabled, volume in (
        ("lead_vocals", "Chant principal", True, 0.90),
        ("backing_vocals", "Chœurs", False, 0.70),
    ):
        if name in stems and name in previews:
            pack(name, label, stems[name], enabled, volume)

    structure = _load_structure(preview_dir)
    beats = list(structure.get("beat_timeline", []) or [])
    meter = dict(structure.get("meter", {}) or {})
    beats_per_measure = int(
        structure.get("metric_beats_per_measure")
        or structure.get("beats_per_bar")
        or meter.get("timeline_beats_per_measure")
        or 4
    )

    audio_hash = Path(preview_dir).parent.name
    try:
        show_diagrams = bool(load_show_diagrams(audio_hash))
    except Exception:
        show_diagrams = False

    try:
        diagrams = _build_chord_diagrams(audio_hash, beats)
    except Exception:
        diagrams = {}

    player_words = list(words or [])

    st.caption(
        "Conducteur STEM : 1 ligne Accords + 1 ligne Paroles · "
        "notation Am--- · '_' = prolongation vocale · "
        "défilement continu sans retour à la ligne."
    )

    _STEM_CONDUCTOR(
        data={
            "tracks": tracks,
            "words": player_words,
            "beats": beats,
            "beats_per_measure": max(1, beats_per_measure),
            "chord_diagrams": diagrams,
            "show_diagrams": show_diagrams,
            "diagram_storage_key": f"ezscore-stem-diagrams:{audio_hash}",
        },
        key=key,
        width="stretch",
        height=760 if (player_words or beats) else 560,
    )
