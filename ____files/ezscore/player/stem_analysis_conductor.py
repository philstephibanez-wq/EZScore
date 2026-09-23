from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import streamlit as st

from ezscore.analysis.forced_lyrics import load_alignment
from ezscore.analysis.stems import STEM_NAMES
from ezscore.guitar import (
    choices as guitar_choices,
    get_voicing,
    load_show_diagrams,
    load_voicings,
    svg as guitar_svg,
)
from ezscore.notation import accord_forme_capo
from ezscore.persistence import load_structure_blocks
from ezscore.player import stem_webaudio as base
from ezscore.player.media_url import register_media_url
from ezscore.ui.editorial_timeline import (
    empty_payload,
    load as load_editorial,
    normalize_beats,
    normalize_words,
)


_TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "templates" / "views"

# Analyse > Paroles and STEM load the SAME validated visual assets.
_LYRICS_EDITOR_CSS = (_TEMPLATE_DIR / "lyrics-editor.css").read_text(
    encoding="utf-8"
)
_LYRICS_LAYOUT_JS = (_TEMPLATE_DIR / "lyrics-layout.js").read_text(
    encoding="utf-8"
)


def _replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(
            f"Patch STEM partagé ambigu/introuvable: {label} "
            f"(occurrences={count})"
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
    '''  <div class="stem-conductor-wrap">
    <div class="stem-conductor-head">
      <label class="diagram-toggle">
        <input class="diagram-checkbox" type="checkbox" tabindex="0"
               aria-label="Afficher le diagramme de l'accord courant">
        Diagramme accord courant
      </label>
      <div class="current-diagram" aria-live="off"></div>
    </div>

    <div class="ez-editor-shell stem-shared-conductor">
      <div class="ez-editor-window">
        <div class="ez-fixed-playhead"
             title="Position de lecture"></div>

        <div class="ez-editor-viewport" tabindex="0"
             aria-label="Conducteur Structure, Accords et Chant">
          <div class="ez-editor-canvas">
            <div class="ez-row">
              <div class="ez-row-label">Structure</div>
              <div class="ez-track ez-sections"></div>
            </div>

            <div class="ez-row">
              <div class="ez-row-label">Accords</div>
              <div class="ez-track ez-chords"></div>
            </div>

            <div class="ez-row">
              <div class="ez-row-label">Chant</div>
              <div class="ez-track ez-lead"></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
''',
    "HTML conducteur partagé",
)

_PLAYER_HTML = _replace_once(
    _PLAYER_HTML,
    """  <div class="transport">
    <button class="play" type="button">▶ Lecture</button>
    <button class="pause" type="button">⏸ Pause</button>
    <button class="stop" type="button">⏹ Stop</button>
    <span class="time">0:00 / 0:00</span>
  </div>

  <input class="seek" type="range" min="0" max="1" step="0.001" value="0">

""",
    "",
    "transport haut retiré",
)

_PLAYER_HTML = _replace_once(
    _PLAYER_HTML,
    """  </div>

  <div class="hint">
""",
    """  </div>

  <div class="transport conductor-transport">
    <button class="play" type="button" tabindex="0"
            aria-label="Lecture">▶ Lecture</button>
    <button class="pause" type="button" tabindex="0"
            aria-label="Pause">⏸ Pause</button>
    <button class="stop" type="button" tabindex="0"
            aria-label="Stop">⏹ Stop</button>
    <span class="time">0:00 / 0:00</span>
  </div>
  <input class="seek conductor-seek" type="range"
         min="0" max="1" step="0.001" value="0"
         tabindex="0" aria-label="Position de lecture">

  <div class="hint">
""",
    "transport sous conducteur",
)


_PLAYER_CSS = (
    base._PLAYER_CSS
    + "\n\n"
    + _LYRICS_EDITOR_CSS
    + r'''

.lyrics-wrap { display:none !important; }

.stem-conductor-wrap {
  margin-top:14px;
  padding-top:10px;
  border-top:1px solid color-mix(in srgb,var(--st-text-color) 18%,transparent);
}

.stem-conductor-head {
  min-height:132px;
  display:flex;
  justify-content:flex-end;
  align-items:flex-end;
  gap:12px;
  margin:0 4px 8px 4px;
}

.diagram-toggle {
  align-self:flex-start;
  display:flex;
  align-items:center;
  gap:6px;
  font-size:11px;
  font-weight:650;
  white-space:nowrap;
}

.current-diagram {
  display:none;
  width:112px;
  min-height:126px;
  align-items:center;
  justify-content:center;
}
.current-diagram.visible { display:flex; }
.current-diagram svg {
  width:auto;
  max-width:108px;
  max-height:124px;
}

.stem-shared-conductor .ez-editor-viewport { cursor:default; }
.stem-shared-conductor .ez-word { cursor:default; }
.stem-shared-conductor .ez-anchor { cursor:default; }
.stem-shared-conductor .ez-beat-token { cursor:default; }
.stem-shared-conductor .ez-word.past { opacity:.52; }
.stem-shared-conductor .ez-word.current {
  color:#fff;
  opacity:1;
  font-weight:900;
  background:color-mix(in srgb,#4da3ff 15%,transparent);
}
.stem-shared-conductor .ez-beat-token.current {
  color:#fff;
  background:color-mix(in srgb,#4da3ff 22%,transparent);
  box-shadow:inset 0 0 0 1px color-mix(in srgb,#4da3ff 48%,transparent);
}
.stem-shared-conductor .ez-anchor.current {
  border-color:#fff;
  box-shadow:0 0 0 2px color-mix(in srgb,#4da3ff 42%,transparent);
}

.conductor-transport { margin-top:10px; }
.conductor-seek { width:100%; margin:8px 0 2px; }

.diagram-checkbox:focus-visible,
.conductor-transport button:focus-visible,
.conductor-seek:focus-visible,
.stem-shared-conductor .ez-editor-viewport:focus-visible {
  outline:3px solid currentColor;
  outline-offset:3px;
}
'''
)


_JS = _LYRICS_LAYOUT_JS + "\n\n" + base._PLAYER_JS

_JS = _replace_once(
    _JS,
    '  let duration = 0;\n',
    '  let duration = Number(data.duration_hint || 0);\n',
    "duration hint",
)

_JS = _replace_once(
    _JS,
    '''  const lyricsWrap = root.querySelector(".lyrics-wrap");
  const lyricsStrip = root.querySelector(".lyrics-strip");
  const lyricsTrack = root.querySelector(".lyrics-track");

  const defs = Array.isArray(data.tracks) ? data.tracks : [];
  const words = Array.isArray(data.words) ? data.words : [];
''',
    '''  const conductorWrap = root.querySelector(".stem-conductor-wrap");
  const viewport = root.querySelector(".ez-editor-viewport");
  const canvas = root.querySelector(".ez-editor-canvas");
  const sectionTrack = root.querySelector(".ez-sections");
  const chordTrack = root.querySelector(".ez-chords");
  const leadTrack = root.querySelector(".ez-lead");
  const diagramCheckbox = root.querySelector(".diagram-checkbox");
  const currentDiagram = root.querySelector(".current-diagram");

  const defs = Array.isArray(data.tracks) ? data.tracks : [];
  const words = Array.isArray(data.words) ? data.words : [];
  const beats = Array.isArray(data.beats) ? data.beats : [];
  const sections = Array.isArray(data.sections) ? data.sections : [];
  const beatsPerMeasure = Math.max(1,Number(data.beats_per_measure || 4));
  const chordDiagrams = data.chord_diagrams || {};
  const diagramStorageKey = String(data.diagram_storage_key || "ezscore-stem-diagrams");
  let showDiagrams = Boolean(data.show_diagrams);
''',
    "sélecteurs conducteur partagé",
)

conductor_js = r'''  // Shared Analyse > Paroles visual conductor.
  // Same CSS/classes, same 100px/s raw scale, same anti-overlap layout.

  const pxPerSecond=100;

  function rawXForTime(time) {
    return Math.max(0,Number(time || 0))*pxPerSecond;
  }

  const allEnds=[
    ...words.map(item=>Number(item.end || item.start || 0)),
    ...beats.map(item=>Number(item.end || item.start || 0)),
    ...sections.map(item=>Number(item.end || item.start || 0)),
    Number(data.duration_hint || 0),
  ].filter(Number.isFinite);

  duration=Math.max(8,duration,...allEnds,0);
  let trackWidth=Math.max(1600,duration*pxPerSecond+240);

  function setTrackWidth(width) {
    trackWidth=Math.max(1600,Number(width || 0));
    canvas.style.width=(trackWidth+78)+"px";
    [sectionTrack,chordTrack,leadTrack].forEach(track=>{
      track.style.width=trackWidth+"px";
    });
  }
  setTrackWidth(trackWidth);

  const gridNodes=[];
  function installGrid() {
    [sectionTrack,chordTrack,leadTrack].forEach(track=>{
      for (let sec=0;sec<=duration;sec+=5) {
        const line=document.createElement("span");
        line.className="ez-gridline";
        line.dataset.time=String(sec);
        track.appendChild(line);
        gridNodes.push(line);

        if (track===sectionTrack) {
          const label=document.createElement("span");
          label.className="ez-grid-label";
          label.dataset.time=String(sec);
          label.textContent=Math.floor(sec/60)+":"+String(Math.floor(sec%60)).padStart(2,"0");
          track.appendChild(label);
          gridNodes.push(label);
        }
      }
    });
  }
  installGrid();

  // Contract: 1 MMS_FA word == 1 DOM node. No merge, no slice.
  const leadNodes=words.map((word,index)=>{
    const node=document.createElement("span");
    node.className="ez-word";
    node.dataset.wordIndex=String(index);
    node.textContent=String(word.text || "");
    node.style.left=rawXForTime(word.start)+"px";
    leadTrack.appendChild(node);
    return node;
  });

  let leadLayout={xs:[],right:0,measurable:false};

  function visualXForTime(time) {
    return ezVisualXForTime(words,leadLayout.xs,time,rawXForTime);
  }

  const chordNodes=[];
  const measureNodes=[];

  function baselineBeatToken(index) {
    const beat=beats[index] || {};
    const chord=String(beat.chord || ".").trim() || ".";
    const explicit=Boolean(beat.explicit);
    const tokenOverride=String(beat.token_override || "").trim();

    if (tokenOverride) return tokenOverride;
    if (chord==="." || chord.toLowerCase()==="n") return ".";

    const position=index % beatsPerMeasure;
    if (position===0 || index===0 || explicit) return chord;

    const previous=String(beats[index-1]?.chord || ".").trim() || ".";
    return previous===chord ? "-" : chord;
  }

  function renderChordMeasures() {
    measureNodes.splice(0).forEach(node=>node.remove());
    chordNodes.splice(0);

    for (let measureStart=0;measureStart<beats.length;measureStart+=beatsPerMeasure) {
      const measureEnd=Math.min(beats.length,measureStart+beatsPerMeasure);
      const firstBeat=beats[measureStart];
      if (!firstBeat) continue;

      const measure=document.createElement("span");
      measure.className="ez-measure";
      measure.dataset.measureStart=String(measureStart);
      measure.style.left=visualXForTime(firstBeat.start)+"px";

      for (let index=measureStart;index<measureEnd;index+=1) {
        const token=document.createElement("span");
        token.className="ez-beat-token";
        token.dataset.beatIndex=String(index);
        token.textContent=baselineBeatToken(index);
        token.title="Beat "+(index-measureStart+1)+"/"+beatsPerMeasure;
        measure.appendChild(token);
        chordNodes[index]=token;
      }

      chordTrack.appendChild(measure);
      measureNodes.push(measure);
    }
  }

  const sectionNodes=sections.map((section,index)=>{
    const node=document.createElement("span");
    node.className="ez-anchor";
    node.dataset.sectionIndex=String(index);
    node.textContent=String(section.label || "Structure");
    node.style.left=rawXForTime(section.start)+"px";
    sectionTrack.appendChild(node);
    return node;
  });

  function relayoutSharedConductor() {
    leadLayout=ezLayoutLaneNodes({
      nodes:leadNodes,
      words,
      rawXForWord:(word)=>rawXForTime(word.start),
      minGap:10,
      contractionGap:1,
    });

    const visualEnd=Math.max(
      visualXForTime(duration),
      Number(leadLayout.right || 0)
    );
    setTrackWidth(visualEnd+240);

    gridNodes.forEach(node=>{
      node.style.left=visualXForTime(Number(node.dataset.time || 0))+"px";
    });

    sectionNodes.forEach((node,index)=>{
      node.style.left=visualXForTime(sections[index].start)+"px";
    });

    renderChordMeasures();
    renderConductor(currentTime());
  }

  function findWordIndex(time) {
    if (!words.length) return -1;
    let low=0,high=words.length-1,answer=-1;
    while (low<=high) {
      const middle=(low+high)>>1;
      if (Number(words[middle].start || 0)<=time) {
        answer=middle; low=middle+1;
      } else {
        high=middle-1;
      }
    }
    return answer;
  }

  function findBeatIndex(time) {
    if (!beats.length) return -1;
    let low=0,high=beats.length-1,answer=-1;
    while (low<=high) {
      const middle=(low+high)>>1;
      if (Number(beats[middle].start || 0)<=time) {
        answer=middle; low=middle+1;
      } else {
        high=middle-1;
      }
    }
    return answer;
  }

  function findSectionIndex(time) {
    for (let index=sections.length-1;index>=0;index-=1) {
      const item=sections[index];
      if (Number(item.start || 0)<=time && time<Number(item.end ?? duration)) {
        return index;
      }
    }
    return -1;
  }

  function updateDiagram(beatIndex) {
    if (!currentDiagram) return;
    if (!showDiagrams || beatIndex<0 || !beats[beatIndex]) {
      currentDiagram.classList.remove("visible");
      currentDiagram.innerHTML="";
      return;
    }

    const chord=String(beats[beatIndex].chord || ".");
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
    const visibleWidth=Math.max(0,viewport.clientWidth-78);
    const targetX=visualXForTime(t);
    const requestedScroll=Math.max(0,targetX-visibleWidth*0.38);

    // Audio clock drives the SAME visual viewport as Analyse > Paroles.
    viewport.scrollLeft=requestedScroll;

    const wordIndex=findWordIndex(t);
    if (wordIndex!==activeWordIndex) {
      activeWordIndex=wordIndex;
      leadNodes.forEach((node,index)=>{
        node.classList.toggle("past",index<wordIndex);
        node.classList.toggle("current",index===wordIndex);
      });
    }

    const beatIndex=findBeatIndex(t);
    chordNodes.forEach((node,index)=>{
      if (!node) return;
      node.classList.toggle("current",index===beatIndex);
    });

    const sectionIndex=findSectionIndex(t);
    sectionNodes.forEach((node,index)=>{
      node.classList.toggle("current",index===sectionIndex);
    });

    updateDiagram(beatIndex);
  }

  if (!words.length && !beats.length && !sections.length) {
    conductorWrap.style.display="none";
  }

  try {
    const saved=localStorage.getItem(diagramStorageKey);
    if (saved==="1" || saved==="0") showDiagrams=saved==="1";
  } catch (_) {}

  diagramCheckbox.checked=showDiagrams;
  diagramCheckbox.addEventListener("change",()=>{
    showDiagrams=Boolean(diagramCheckbox.checked);
    try {
      localStorage.setItem(diagramStorageKey,showDiagrams ? "1" : "0");
    } catch (_) {}
    renderConductor(currentTime());
  });

  window.addEventListener("resize",()=>{
    requestAnimationFrame(relayoutSharedConductor);
  });
  requestAnimationFrame(relayoutSharedConductor);
  setTimeout(relayoutSharedConductor,80);
  setTimeout(relayoutSharedConductor,280);

  if (document.fonts?.ready) {
    document.fonts.ready.then(()=>{
      if (!leadTrack.isConnected) return;
      requestAnimationFrame(relayoutSharedConductor);
    }).catch(()=>{});
  }

  renderConductor(0);

'''

_JS = _replace_region(
    _JS,
    start_marker="  const lyricNodes = words.map((word) => {\n",
    end_marker="  function tick() {\n",
    replacement=conductor_js,
    label="moteur conducteur partagé",
)

_JS = _JS.replace("renderLyrics(0);", "renderConductor(0);")
_JS = _JS.replace("renderLyrics(t);", "renderConductor(t);")
_JS = _JS.replace("    renderLyrics(t);", "    renderConductor(t);")


_STEM_CONDUCTOR = st.components.v2.component(
    "ezscore_stem_shared_conductor_r2_full",
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


def _effective_signature(structure: dict[str, Any]) -> str:
    selected = str(st.session_state.get("setting_signature_mode", "Auto") or "Auto").strip()
    if selected and selected != "Auto":
        return selected

    meter = dict(structure.get("meter", {}) or {})
    detected = str(structure.get("signature") or meter.get("signature") or "4/4").strip()
    return detected if re.fullmatch(r"\d+\s*/\s*\d+", detected) else "4/4"


def _beats_per_measure(signature: str) -> int:
    match = re.fullmatch(r"\s*(\d+)\s*/\s*(\d+)\s*", str(signature or ""))
    if not match:
        return 4

    numerator = max(1, int(match.group(1)))
    denominator = max(1, int(match.group(2)))

    # Same tactus convention as stem_lab_analysis._meter_spec().
    if denominator >= 8 and numerator > 3:
        if numerator % 3 == 0:
            return max(1, numerator // 3)
        if numerator == 5:
            return 2
        if numerator == 7:
            return 3
    return numerator


def _safe_editorial(
    work_dir: Path,
    lead: list[dict[str, Any]],
    beats: list[dict[str, Any]],
) -> dict[str, Any]:
    try:
        return load_editorial(work_dir, lead, [], beats)
    except Exception:
        # Read-only player never overwrites a stale editorial overlay.
        return empty_payload(lead, [], beats)


def _apply_lead_editorial(
    lead: list[dict[str, Any]],
    editorial: dict[str, Any],
) -> list[dict[str, Any]]:
    overrides = dict(editorial.get("lead_overrides", {}) or {})
    result = []
    for index, word in enumerate(lead):
        item = dict(word)
        item["text"] = str(overrides.get(str(index), item.get("text", "")) or "")
        result.append(item)
    return result


def _display_beats(
    beats: list[dict[str, Any]],
    editorial: dict[str, Any],
    capo: int,
) -> list[dict[str, Any]]:
    overrides = dict(editorial.get("chord_overrides", {}) or {})
    result: list[dict[str, Any]] = []
    active_real = "."

    for index, beat in enumerate(beats):
        key = str(index)
        raw = str(beat.get("chord", ".") or ".").strip() or "."
        has_override = key in overrides
        requested = (
            (str(overrides.get(key, "") or "").strip() or ".")
            if has_override else raw
        )

        token_override = ""
        explicit = False

        if has_override and requested == "-":
            real_symbol = active_real
            token_override = "-"
        elif requested == "." or requested.lower() == "n":
            real_symbol = "."
            active_real = "."
            if has_override:
                token_override = "."
        else:
            real_symbol = requested
            active_real = requested
            if has_override:
                explicit = True

        display_symbol = (
            accord_forme_capo(real_symbol, capo)
            if real_symbol not in ("", ".", "-", "?", "^")
            else real_symbol
        )

        if has_override and explicit:
            token_override = display_symbol

        result.append({
            "index": index,
            "start": float(beat.get("start", 0.0) or 0.0),
            "end": float(beat.get("end", beat.get("start", 0.0)) or 0.0),
            "chord": display_symbol or ".",
            "explicit": bool(explicit),
            "token_override": token_override,
        })

    return result


def _manual_sections(
    audio_hash: str,
    beats: list[dict[str, Any]],
    beats_per_measure: int,
) -> list[dict[str, Any]]:
    try:
        blocks = load_structure_blocks(audio_hash)
    except Exception:
        blocks = []

    if not blocks or not beats:
        return []

    bpb = max(1, int(beats_per_measure))
    measure_count = (len(beats) + bpb - 1) // bpb
    result: list[dict[str, Any]] = []

    def measure_start_time(number: int) -> float:
        index = max(0, min(len(beats) - 1, (number - 1) * bpb))
        return float(beats[index].get("start", 0.0) or 0.0)

    def measure_end_time(number: int) -> float:
        next_index = number * bpb
        if next_index < len(beats):
            return float(beats[next_index].get("start", 0.0) or 0.0)
        return float(beats[-1].get("end", beats[-1].get("start", 0.0)) or 0.0)

    for index, block in enumerate(blocks):
        m0 = max(1, min(measure_count, int(block.get("measure_start", 1) or 1)))
        m1 = max(m0, min(measure_count, int(block.get("measure_end", m0) or m0)))

        label = str(block.get("custom_label", "") or "").strip()
        if not label:
            label = str(block.get("cluster", "") or "").strip()
        if not label:
            label = f"Bloc {index + 1}"

        result.append({
            "label": label,
            "start": measure_start_time(m0),
            "end": measure_end_time(m1),
            "measure_start": m0,
            "measure_end": m1,
        })

    return result


def _build_chord_diagrams(
    audio_hash: str,
    beats: list[dict[str, Any]],
) -> dict[str, str]:
    saved = load_voicings(audio_hash)
    diagrams: dict[str, str] = {}

    for beat in beats:
        symbol = str(beat.get("chord", "") or "").strip()
        if not symbol or symbol in (".", "-", "?", "^") or symbol in diagrams:
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

            diagrams[symbol] = guitar_svg(symbol, voicing, width=92, height=118)
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
        "Conducteur visuel partagé avec Analyse > Paroles."
    )

    previews = base.prepare_browser_previews(source, stems, preview_dir)
    tracks: list[dict[str, Any]] = []

    def pack(name: str, label: str, path: Path, enabled: bool, volume: float) -> None:
        preview = previews[name]
        media_url = register_media_url(
            preview,
            coordinates=f"{key}:stem:{name}",
            mimetype="audio/mpeg",
        )
        tracks.append({
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
        })

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

    audio_hash = Path(preview_dir).parent.name
    structure = _load_structure(preview_dir)
    raw_beats = list(structure.get("beat_timeline", []) or [])
    beats = normalize_beats(raw_beats)

    player_words = list(words or [])
    if not player_words:
        forced = load_alignment(audio_hash) or {}
        player_words = list(forced.get("words", []) or [])

    lead = normalize_words(player_words)
    editorial = _safe_editorial(Path(preview_dir).parent, lead, beats)
    lead = _apply_lead_editorial(lead, editorial)

    signature = _effective_signature(structure)
    beats_per_measure = _beats_per_measure(signature)
    capo = max(0, min(12, int(st.session_state.get("capo_live", 0) or 0)))

    display_beats = _display_beats(beats, editorial, capo)
    sections = _manual_sections(audio_hash, display_beats, beats_per_measure)

    try:
        show_diagrams = bool(load_show_diagrams(audio_hash))
    except Exception:
        show_diagrams = False

    try:
        diagrams = _build_chord_diagrams(audio_hash, display_beats)
    except Exception:
        diagrams = {}

    last_word_end = max(
        [float(item.get("end", item.get("start", 0.0)) or 0.0) for item in lead]
        or [0.0]
    )
    last_beat_end = max(
        [float(item.get("end", item.get("start", 0.0)) or 0.0) for item in display_beats]
        or [0.0]
    )
    last_section_end = max(
        [float(item.get("end", item.get("start", 0.0)) or 0.0) for item in sections]
        or [0.0]
    )
    duration_hint = max(last_word_end, last_beat_end, last_section_end)

    st.caption(
        "Conducteur commun : Structure / Accords / Chant · "
        f"{signature} · Capo {capo} · "
        f"{len(display_beats)} beats · {len(lead)} mots · "
        f"{len(sections)} bloc(s) manuel(s)."
    )

    _STEM_CONDUCTOR(
        data={
            "tracks": tracks,
            "words": lead,
            "beats": display_beats,
            "sections": sections,
            "beats_per_measure": max(1, beats_per_measure),
            "signature": signature,
            "capo": capo,
            "chord_diagrams": diagrams,
            "show_diagrams": show_diagrams,
            "diagram_storage_key": f"ezscore-stem-diagrams:{audio_hash}",
            "duration_hint": float(duration_hint),
        },
        key=(
            f"{key}_shared_{signature.replace('/', '_')}_capo{capo}_"
            f"{len(lead)}_{len(display_beats)}_{len(sections)}"
        ),
        width="stretch",
        height=930 if (lead or display_beats or sections) else 620,
    )
