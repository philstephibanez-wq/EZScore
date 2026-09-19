export default function(component) {
  const root = component.parentElement;
  const data = component.data || {};
  const lead = Array.isArray(data.lead) ? data.lead : [];
  const backing = Array.isArray(data.backing) ? data.backing : [];
  const beats = Array.isArray(data.beats) ? data.beats : [];

  const viewport = root.querySelector(".ez-editor-viewport");
  const canvas = root.querySelector(".ez-editor-canvas");
  const sectionTrack = root.querySelector(".ez-sections");
  const chordTrack = root.querySelector(".ez-chords");
  const leadTrack = root.querySelector(".ez-lead");
  const backingTrack = root.querySelector(".ez-backing");
  const positionLabel = root.querySelector(".ez-position");

  const initial = data.editorial || {};
  const stateSnapshot = String(component.state?.snapshot || "");
  let editorial;

  try {
    editorial = stateSnapshot
      ? JSON.parse(stateSnapshot)
      : JSON.parse(JSON.stringify(initial));
  } catch (_) {
    editorial = JSON.parse(JSON.stringify(initial));
  }

  editorial.lead_overrides ||= {};
  editorial.backing_overrides ||= {};
  editorial.line_break_after_lead ||= [];
  editorial.chord_overrides ||= {};
  editorial.anchors ||= [];

  const allEnds = [
    ...lead.map(item => Number(item.end || 0)),
    ...backing.map(item => Number(item.end || 0)),
    ...beats.map(item => Number(item.end || item.start || 0)),
    ...editorial.anchors.map(item => Number(item.time || 0)),
  ].filter(Number.isFinite);

  const duration = Math.max(8, ...allEnds, 0);
  const pxPerSecond = 100;
  const trackWidth = Math.max(1600, duration * pxPerSecond + 240);

  canvas.style.width = (trackWidth + 78) + "px";
  [sectionTrack, chordTrack, leadTrack, backingTrack].forEach(track => {
    track.style.width = trackWidth + "px";
  });

  function xFor(time) {
    return Math.max(0, Number(time || 0)) * pxPerSecond;
  }

  function timeForX(x) {
    return Math.max(0, Math.min(duration, Number(x || 0) / pxPerSecond));
  }

  function fmt(seconds) {
    const t = Math.max(0, Number(seconds || 0));
    return Math.floor(t / 60) + ":" + String(Math.floor(t % 60)).padStart(2, "0");
  }

  const detectedMeter = String(data.detected_meter || "4/4");
  const analysisMeterStorageKey = String(
    data.analysis_meter_storage_key || ""
  );

  function parseMeter(value) {
    const match = String(value || "").trim().match(
      /^([1-9][0-9]?)\/(1|2|4|8|16|32)$/
    );
    if (!match) return null;

    return {
      text: `${Number(match[1])}/${Number(match[2])}`,
      numerator: Number(match[1]),
      denominator: Number(match[2]),
    };
  }

  function playerAnalyseMeter() {
    if (!analysisMeterStorageKey) return null;

    try {
      const saved = JSON.parse(
        localStorage.getItem(analysisMeterStorageKey) || "null"
      );
      return parseMeter(saved?.signature);
    } catch (_) {
      return null;
    }
  }

  function currentMeter() {
    return (
      playerAnalyseMeter()
      || parseMeter(detectedMeter)
      || { text: "4/4", numerator: 4, denominator: 4 }
    );
  }


  function emit() {
    component.setStateValue("snapshot", JSON.stringify(editorial));
  }

  function installGrid(track) {
    for (let sec = 0; sec <= duration; sec += 5) {
      const line = document.createElement("span");
      line.className = "ez-gridline";
      line.style.left = xFor(sec) + "px";
      track.appendChild(line);

      if (track === sectionTrack) {
        const label = document.createElement("span");
        label.className = "ez-grid-label";
        label.style.left = xFor(sec) + "px";
        label.textContent = fmt(sec);
        track.appendChild(label);
      }
    }
  }

  [sectionTrack, chordTrack, leadTrack, backingTrack].forEach(installGrid);

  function updatePositionLabel() {
    const visibleWidth = Math.max(0, viewport.clientWidth - 78);
    const playheadX = viewport.scrollLeft + visibleWidth * 0.38;
    positionLabel.textContent = fmt(timeForX(playheadX));
  }

  viewport.addEventListener("scroll", updatePositionLabel, { passive: true });
  updatePositionLabel();

  let dragActive = false;
  let dragOriginX = 0;
  let dragOriginScroll = 0;

  viewport.addEventListener("pointerdown", event => {
    if (
      event.target.closest(".ez-word") ||
      event.target.closest(".ez-beat-token") ||
      event.target.closest(".ez-measure") ||
      event.target.closest(".ez-anchor") ||
      event.target.closest(".ez-linebreak") ||
      event.target.closest(".ez-sections")
    ) {
      return;
    }

    dragActive = true;
    dragOriginX = event.clientX;
    dragOriginScroll = viewport.scrollLeft;
    viewport.classList.add("dragging");
    viewport.setPointerCapture(event.pointerId);
  });

  viewport.addEventListener("pointermove", event => {
    if (!dragActive) return;
    viewport.scrollLeft = dragOriginScroll - (event.clientX - dragOriginX);
  });

  function stopDrag(event) {
    if (!dragActive) return;
    dragActive = false;
    viewport.classList.remove("dragging");
    try {
      viewport.releasePointerCapture(event.pointerId);
    } catch (_) {}
  }

  viewport.addEventListener("pointerup", stopDrag);
  viewport.addEventListener("pointercancel", stopDrag);

  function startInlineEdit(node, getValue, setValue) {
    node.addEventListener("dblclick", event => {
      event.stopPropagation();
      node.contentEditable = "true";
      node.focus();

      const range = document.createRange();
      range.selectNodeContents(node);

      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
    });

    node.addEventListener("keydown", event => {
      if (event.key === "Enter") {
        event.preventDefault();
        node.blur();
      } else if (event.key === "Escape") {
        event.preventDefault();
        node.textContent = getValue();
        node.contentEditable = "false";
      }
    });

    node.addEventListener("blur", () => {
      if (node.contentEditable !== "true") return;

      const text = String(node.textContent || "").trim();
      if (text) {
        setValue(text);
        node.textContent = text;
        emit();
      } else {
        node.textContent = getValue();
      }
      node.contentEditable = "false";
    });
  }

  function rawBeatValue(index) {
    const key = String(index);
    if (Object.prototype.hasOwnProperty.call(editorial.chord_overrides, key)) {
      return String(editorial.chord_overrides[key] || ".").trim() || ".";
    }
    return String(beats[index]?.chord || ".").trim() || ".";
  }

  function detectedBeatValue(index) {
    return String(beats[index]?.chord || ".").trim() || ".";
  }

  function baselineBeatToken(index, numerator) {
    const current = detectedBeatValue(index);
    const position = index % numerator;

    if (current === "." || current.toLowerCase() === "n") {
      return ".";
    }

    if (position === 0 || index === 0) {
      return current;
    }

    const previous = detectedBeatValue(index - 1);
    if (previous === current) {
      return "-";
    }

    return current;
  }

  function displayBeatToken(index, numerator) {
    const key = String(index);
    if (Object.prototype.hasOwnProperty.call(editorial.chord_overrides, key)) {
      return String(editorial.chord_overrides[key] || ".").trim() || ".";
    }
    return baselineBeatToken(index, numerator);
  }

  function setBeatToken(index, text, numerator) {
    const key = String(index);
    const clean = String(text || "").trim() || ".";
    const baseline = baselineBeatToken(index, numerator);

    if (clean === baseline) {
      delete editorial.chord_overrides[key];
    } else {
      editorial.chord_overrides[key] = clean;
    }
  }

  function renderChordMeasures() {
    chordTrack.querySelectorAll(".ez-measure").forEach(node => node.remove());

    const meter = currentMeter();
    const numerator = meter.numerator;

    for (let measureStart = 0; measureStart < beats.length; measureStart += numerator) {
      const measureEnd = Math.min(beats.length, measureStart + numerator);
      const firstBeat = beats[measureStart];
      if (!firstBeat) continue;

      const measure = document.createElement("span");
      measure.className = "ez-measure";
      measure.dataset.measureStart = String(measureStart);
      measure.style.left = xFor(firstBeat.start) + "px";
      measure.title = `${meter.text} · beats ${measureStart + 1}-${measureEnd}`;

      for (let index = measureStart; index < measureEnd; index += 1) {
        const token = document.createElement("span");
        token.className = "ez-beat-token";
        token.dataset.beatIndex = String(index);

        const current = () => displayBeatToken(index, numerator);
        token.textContent = current();
        token.title = `Beat ${index - measureStart + 1}/${numerator} · double-clic = modifier`;

        startInlineEdit(token, current, text => {
          setBeatToken(index, text, numerator);
        });

        measure.appendChild(token);
      }

      chordTrack.appendChild(measure);
    }
  }

  renderChordMeasures();

  // Le player Analyse et Paroles restent montés simultanément dans les onglets.
  // La signature du player peut donc changer sans rerender automatique ici.
  // On relit sa valeur et on recalcule uniquement la représentation des accords.
  let effectiveMeterText = currentMeter().text;

  if (root.__ezscoreMeterPoll) {
    clearInterval(root.__ezscoreMeterPoll);
  }

  root.__ezscoreMeterPoll = setInterval(() => {
    if (!root.isConnected) {
      clearInterval(root.__ezscoreMeterPoll);
      root.__ezscoreMeterPoll = null;
      return;
    }

    const nextMeterText = currentMeter().text;
    if (nextMeterText === effectiveMeterText) return;

    effectiveMeterText = nextMeterText;
    renderChordMeasures();
  }, 250);

  const breakSet = new Set(
    (editorial.line_break_after_lead || []).map(Number)
  );

  const leadNodes = [];

  lead.forEach((word, index) => {
    const key = String(index);
    const node = document.createElement("span");
    node.className = "ez-word";
    node.style.left = xFor(word.start) + "px";

    const current = () => String(
      editorial.lead_overrides[key] ?? word.text ?? ""
    );

    node.textContent = current();

    startInlineEdit(node, current, text => {
      if (text === String(word.text || "")) {
        delete editorial.lead_overrides[key];
      } else {
        editorial.lead_overrides[key] = text;
      }
    });

    const LONG_PRESS_MS = 475;
    const LONG_PRESS_MOVE_PX = 4;
    let longPressTimer = null;
    let longPressPointerId = null;
    let longPressStartX = 0;
    let longPressStartY = 0;
    let longPressTriggered = false;

    function cancelLongPress() {
      if (longPressTimer !== null) {
        clearTimeout(longPressTimer);
        longPressTimer = null;
      }
    }

    node.addEventListener("pointerdown", event => {
      if (event.button !== 0 || node.contentEditable === "true") return;

      longPressTriggered = false;
      longPressPointerId = event.pointerId;
      longPressStartX = event.clientX;
      longPressStartY = event.clientY;

      cancelLongPress();
      longPressTimer = setTimeout(() => {
        longPressTimer = null;

        if (node.contentEditable === "true") return;
        if (index >= lead.length - 1) return;
        if (breakSet.has(index)) return;

        breakSet.add(index);
        syncBreakSet();
        makeLineBreakNode(index);
        emit();

        longPressTriggered = true;
        node.classList.add("longpress-feedback");
        setTimeout(() => node.classList.remove("longpress-feedback"), 220);
      }, LONG_PRESS_MS);
    });

    node.addEventListener("pointermove", event => {
      if (event.pointerId !== longPressPointerId) return;

      const moved = Math.hypot(
        event.clientX - longPressStartX,
        event.clientY - longPressStartY,
      );

      if (moved > LONG_PRESS_MOVE_PX) {
        cancelLongPress();
      }
    });

    node.addEventListener("pointerup", event => {
      if (event.pointerId !== longPressPointerId) return;
      cancelLongPress();

      if (longPressTriggered) {
        event.preventDefault();
        event.stopPropagation();
      }

      longPressPointerId = null;
    });

    node.addEventListener("pointercancel", () => {
      cancelLongPress();
      longPressPointerId = null;
    });

    leadTrack.appendChild(node);
    leadNodes.push(node);
  });

  ezLayoutLaneNodes({
    nodes: leadNodes,
    words: lead.map((word, index) => ({
      ...word,
      text: String(
        editorial.lead_overrides[String(index)] ?? word.text ?? ""
      ),
    })),
    rawXForWord: (word) => xFor(word.start),
    minGap: 10,
    contractionGap: 1,
    breakAfter: (index) => breakSet.has(index),
  });

  function wordRenderedEndX(index) {
    const word = lead[index];
    const node = leadNodes[index];
    if (!word || !node) return 0;

    return (
      Number.parseFloat(node.style.left || String(xFor(word.start)))
      + node.getBoundingClientRect().width
      + 6
    );
  }

  function nearestLeadWordByX(rawX) {
    if (!lead.length) return -1;

    let bestIndex = 0;
    let bestDistance = Infinity;

    lead.forEach((word, index) => {
      if (index >= lead.length - 1) return;

      const targetX = wordRenderedEndX(index);
      const distance = Math.abs(targetX - rawX);

      if (distance < bestDistance) {
        bestDistance = distance;
        bestIndex = index;
      }
    });

    return bestIndex;
  }

  function syncBreakSet() {
    editorial.line_break_after_lead = [...breakSet].sort((a, b) => a - b);
  }

  function makeLineBreakNode(index) {
    if (
      index < 0
      || index >= lead.length - 1
      || leadTrack.querySelector(`[data-linebreak-index="${index}"]`)
    ) {
      return;
    }

    const marker = document.createElement("button");
    marker.type = "button";
    marker.className = "ez-linebreak";
    marker.textContent = "↵";
    marker.title = (
      "Saut de ligne visuel · clic gauche maintenu + glisser = déplacer · "
      + "Suppr = supprimer"
    );
    marker.dataset.linebreakIndex = String(index);
    marker.style.left = wordRenderedEndX(index) + "px";
    marker.tabIndex = 0;

    marker.addEventListener("click", event => {
      event.stopPropagation();
      marker.focus();
    });

    marker.addEventListener("keydown", event => {
      if (event.key !== "Delete") return;

      event.preventDefault();
      event.stopPropagation();

      const currentIndex = Number(marker.dataset.linebreakIndex);
      breakSet.delete(currentIndex);
      syncBreakSet();
      marker.remove();
      emit();
    });

    const BREAK_DRAG_THRESHOLD_PX = 5;
    let breakDrag = null;

    marker.addEventListener("pointerdown", event => {
      if (event.button !== 0) return;

      event.stopPropagation();

      breakDrag = {
        pointerId: event.pointerId,
        startClientX: event.clientX,
        originalIndex: Number(marker.dataset.linebreakIndex),
        candidateIndex: Number(marker.dataset.linebreakIndex),
        moved: false,
        label: null,
      };

      marker.setPointerCapture(event.pointerId);
    });

    marker.addEventListener("pointermove", event => {
      if (!breakDrag || event.pointerId !== breakDrag.pointerId) return;

      const delta = event.clientX - breakDrag.startClientX;

      if (!breakDrag.moved && Math.abs(delta) < BREAK_DRAG_THRESHOLD_PX) {
        return;
      }

      event.preventDefault();
      event.stopPropagation();

      if (!breakDrag.moved) {
        breakDrag.moved = true;
        marker.classList.add("dragging");

        const dragLabel = document.createElement("span");
        dragLabel.className = "ez-linebreak-drag-label";
        dragLabel.textContent = `↵ après ${lead[breakDrag.originalIndex].text}`;
        marker.appendChild(dragLabel);
        breakDrag.label = dragLabel;
      }

      const rect = leadTrack.getBoundingClientRect();
      const rawX = Math.max(
        0,
        Math.min(trackWidth, event.clientX - rect.left)
      );
      const candidateIndex = nearestLeadWordByX(rawX);

      if (candidateIndex < 0) return;

      breakDrag.candidateIndex = candidateIndex;
      marker.style.left = wordRenderedEndX(candidateIndex) + "px";
      breakDrag.label.textContent = `↵ après ${lead[candidateIndex].text}`;
    });

    function finishBreakDrag(event) {
      if (!breakDrag || event.pointerId !== breakDrag.pointerId) return;

      const wasMoved = breakDrag.moved;
      const originalIndex = breakDrag.originalIndex;
      const candidateIndex = breakDrag.candidateIndex;

      if (wasMoved) {
        event.preventDefault();
        event.stopPropagation();

        if (candidateIndex !== originalIndex) {
          if (breakSet.has(candidateIndex)) {
            marker.style.left = wordRenderedEndX(originalIndex) + "px";
          } else {
            breakSet.delete(originalIndex);
            breakSet.add(candidateIndex);
            marker.dataset.linebreakIndex = String(candidateIndex);
            marker.style.left = wordRenderedEndX(candidateIndex) + "px";
            syncBreakSet();
            emit();
          }
        } else {
          marker.style.left = wordRenderedEndX(originalIndex) + "px";
        }
      }

      try {
        marker.releasePointerCapture(event.pointerId);
      } catch (_) {}

      breakDrag.label?.remove();
      marker.classList.remove("dragging");
      breakDrag = null;
    }

    marker.addEventListener("pointerup", finishBreakDrag);
    marker.addEventListener("pointercancel", finishBreakDrag);

    leadTrack.appendChild(marker);
  }

  breakSet.forEach(makeLineBreakNode);


  backing.forEach((word, index) => {
    const key = String(index);
    const node = document.createElement("span");
    node.className = "ez-word";
    node.style.left = xFor(word.start) + "px";

    const current = () => String(
      editorial.backing_overrides[key] ?? word.text ?? ""
    );

    node.textContent = current();

    startInlineEdit(node, current, text => {
      if (text === String(word.text || "")) {
        delete editorial.backing_overrides[key];
      } else {
        editorial.backing_overrides[key] = text;
      }
    });

    backingTrack.appendChild(node);
  });

  const backingNodes = [
    ...backingTrack.querySelectorAll(".ez-word")
  ];

  ezLayoutLaneNodes({
    nodes: backingNodes,
    words: backing.map((word, index) => ({
      ...word,
      text: String(
        editorial.backing_overrides[String(index)] ?? word.text ?? ""
      ),
    })),
    rawXForWord: (word) => xFor(word.start),
    minGap: 10,
    contractionGap: 1,
  });

  function nearestSnap(time) {
    let best = null;

    beats.forEach((beat, index) => {
      const snapTime = Number(beat.start || 0);
      const distance = Math.abs(snapTime - time);

      if (best === null || distance < best.distance) {
        best = {
          distance,
          snap: "beat",
          snap_index: index,
          time: snapTime,
        };
      }
    });

    for (let index = 1; index < lead.length; index += 1) {
      const boundaryTime = (
        Number(lead[index - 1].end || 0)
        + Number(lead[index].start || 0)
      ) / 2;

      const distance = Math.abs(boundaryTime - time);

      if (best === null || distance < best.distance) {
        best = {
          distance,
          snap: "word_boundary",
          snap_index: index,
          time: boundaryTime,
        };
      }
    }

    return best;
  }

  function updateAnchorFromSnap(anchor, snap) {
    anchor.time = snap.time;
    anchor.snap = snap.snap;
    anchor.snap_index = snap.snap_index;
  }

  function makeAnchorNode(anchor) {
    const node = document.createElement("span");
    node.className = "ez-anchor";
    node.style.left = xFor(anchor.time) + "px";
    node.textContent = String(anchor.label || "Section");
    node.title = "Double-clic = renommer · clic gauche maintenu + glisser = déplacer · Suppr = supprimer";

    startInlineEdit(
      node,
      () => String(anchor.label || ""),
      text => {
        anchor.label = text;
      },
    );

    const DRAG_THRESHOLD_PX = 5;
    let anchorDrag = null;

    node.addEventListener("pointerdown", event => {
      if (event.button !== 0 || node.contentEditable === "true") return;

      event.stopPropagation();

      anchorDrag = {
        pointerId: event.pointerId,
        startClientX: event.clientX,
        initialLeft: parseFloat(node.style.left) || xFor(anchor.time),
        moved: false,
        snap: null,
        label: null,
      };

      node.setPointerCapture(event.pointerId);
    });

    node.addEventListener("pointermove", event => {
      if (!anchorDrag || event.pointerId !== anchorDrag.pointerId) return;

      const delta = event.clientX - anchorDrag.startClientX;

      if (!anchorDrag.moved && Math.abs(delta) < DRAG_THRESHOLD_PX) {
        return;
      }

      event.preventDefault();
      event.stopPropagation();

      if (!anchorDrag.moved) {
        anchorDrag.moved = true;
        node.classList.add("dragging");

        const dragLabel = document.createElement("span");
        dragLabel.className = "ez-anchor-drag-label";
        dragLabel.textContent = `${anchor.label} · ${fmt(anchor.time)}`;
        node.appendChild(dragLabel);
        anchorDrag.label = dragLabel;
      }

      const rawX = Math.max(
        0,
        Math.min(trackWidth, anchorDrag.initialLeft + delta)
      );
      const rawTime = timeForX(rawX);
      const snap = nearestSnap(rawTime);
      if (!snap) return;

      node.style.left = xFor(snap.time) + "px";
      anchorDrag.snap = snap;
      anchorDrag.label.textContent =
        `${anchor.label} · ${fmt(snap.time)} · ${
          snap.snap === "beat" ? "beat" : "mots"
        }`;
    });

    function finishAnchorDrag(event) {
      if (!anchorDrag || event.pointerId !== anchorDrag.pointerId) return;

      const wasMoved = anchorDrag.moved;

      if (wasMoved) {
        event.preventDefault();
        event.stopPropagation();

        if (anchorDrag.snap) {
          updateAnchorFromSnap(anchor, anchorDrag.snap);
          node.style.left = xFor(anchor.time) + "px";
          editorial.anchors.sort(
            (a, b) => Number(a.time || 0) - Number(b.time || 0)
          );
          emit();
        } else {
          node.style.left = xFor(anchor.time) + "px";
        }
      }

      try {
        node.releasePointerCapture(event.pointerId);
      } catch (_) {}

      anchorDrag.label?.remove();
      node.classList.remove("dragging");
      anchorDrag = null;
    }

    node.addEventListener("pointerup", finishAnchorDrag);
    node.addEventListener("pointercancel", finishAnchorDrag);

    node.addEventListener("keydown", event => {
      if (event.key === "Delete" && node.contentEditable !== "true") {
        event.preventDefault();
        editorial.anchors = editorial.anchors.filter(
          item => item.id !== anchor.id
        );
        node.remove();
        emit();
      }
    });

    node.tabIndex = 0;
    sectionTrack.appendChild(node);
  }

  editorial.anchors.forEach(makeAnchorNode);

  let pendingInput = null;

  sectionTrack.addEventListener("click", event => {
    if (
      event.target.closest(".ez-anchor") ||
      event.target.closest(".ez-pending-anchor")
    ) {
      return;
    }

    if (pendingInput) {
      pendingInput.remove();
      pendingInput = null;
    }

    const rect = sectionTrack.getBoundingClientRect();
    const canvasX = event.clientX - rect.left;
    const requestedTime = timeForX(canvasX);
    const snap = nearestSnap(requestedTime);

    if (!snap) return;

    const input = document.createElement("input");
    input.className = "ez-pending-anchor";
    input.placeholder = "Intro / Couplet 1…";
    input.style.left = xFor(snap.time) + "px";
    input.style.transform = "translateX(-50%)";
    sectionTrack.appendChild(input);
    pendingInput = input;
    input.focus();

    function cancel() {
      if (pendingInput === input) {
        pendingInput = null;
      }
      input.remove();
    }

    function commit() {
      const label = String(input.value || "").trim();
      if (!label) {
        cancel();
        return;
      }

      const anchor = {
        id: (
          globalThis.crypto?.randomUUID?.()
          || String(Date.now()) + "-" + Math.random().toString(16).slice(2)
        ),
        label,
        time: snap.time,
        snap: snap.snap,
        snap_index: snap.snap_index,
      };

      editorial.anchors.push(anchor);
      editorial.anchors.sort(
        (a, b) => Number(a.time || 0) - Number(b.time || 0)
      );

      cancel();
      makeAnchorNode(anchor);
      emit();
    }

    input.addEventListener("keydown", keyEvent => {
      if (keyEvent.key === "Enter") {
        keyEvent.preventDefault();
        commit();
      } else if (keyEvent.key === "Escape") {
        keyEvent.preventDefault();
        cancel();
      }
    });

    input.addEventListener("blur", () => {
      if (pendingInput === input) {
        commit();
      }
    });
  });

  emit();
}
