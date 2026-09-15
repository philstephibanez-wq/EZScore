
export default function(component) {
  const data = component.data || {};
  const root = component.parentElement;

  const playButton = root.querySelector(".play");
  const pauseButton = root.querySelector(".pause");
  const stopButton = root.querySelector(".stop");
  const seek = root.querySelector(".seek");
  const timeLabel = root.querySelector(".time");
  const tracksNode = root.querySelector(".tracks");
  const masterVolume = root.querySelector(".master-volume");
  const masterValue = root.querySelector(".master-value");
  const lyricsWrap = root.querySelector(".lyrics-wrap");
  const lyricsStrip = root.querySelector(".lyrics-strip");
  const lyricsTrack = root.querySelector(".lyrics-track");

  const defs = Array.isArray(data.tracks) ? data.tracks : [];
  const words = Array.isArray(data.words) ? data.words : [];

  // Authoritative UI state exists before any AudioContext/node creation.
  const trackState = defs.map((track) => ({
    enabled: Boolean(track.enabled),
    volume: Number(track.volume ?? 0.8),
    low: Number(track.low ?? 0),
    mid: Number(track.mid ?? 0),
    high: Number(track.high ?? 0),
  }));
  let masterState = 1.0;

  let context = null;
  let decoded = [];
  let trackNodes = [];
  let masterGain = null;
  let sources = [];
  let ready = false;
  let playing = false;
  let disposed = false;
  let position = 0;
  let startedAtContextTime = 0;
  let duration = 0;
  let raf = null;
  let activeWordIndex = -1;

  function fmt(seconds) {
    seconds = Math.max(0, Number(seconds) || 0);
    const m = Math.floor(seconds / 60);
    const sec = Math.floor(seconds % 60);
    return m + ":" + String(sec).padStart(2, "0");
  }

  function currentTime() {
    if (!playing || !context) return position;
    return Math.max(0, Math.min(duration, position + (context.currentTime - startedAtContextTime)));
  }

  function decodeBase64(base64) {
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
    return bytes.buffer;
  }

  function dbToLinear(db) {
    return Math.pow(10, Number(db || 0) / 20);
  }

  function compensationFor(state) {
    const avg = (
      dbToLinear(state.low) +
      dbToLinear(state.mid) +
      dbToLinear(state.high)
    ) / 3;
    if (!Number.isFinite(avg) || avg <= 0.0001) return 1.0;
    return Math.max(0.72, Math.min(1.25, 1 / avg));
  }

  function applyTrackState(index, smooth = true) {
    if (!ready || !trackNodes[index] || !context) return;
    const state = trackState[index];
    const nodes = trackNodes[index];
    const now = context.currentTime;

    const enabledGain = state.enabled ? state.volume : 0;
    const comp = compensationFor(state);

    const setValue = (param, value) => {
      if (smooth) param.setTargetAtTime(value, now, 0.015);
      else param.value = value;
    };

    setValue(nodes.lowGain.gain, dbToLinear(state.low));
    setValue(nodes.midGain.gain, dbToLinear(state.mid));
    setValue(nodes.highGain.gain, dbToLinear(state.high));
    setValue(nodes.trackGain.gain, enabledGain * comp);
  }

  function applyMasterState(smooth = true) {function applyMasterState(smooth = true) {
    if (!ready || !masterGain || !context) return;
    const now = context.currentTime;
    if (smooth) masterGain.gain.setTargetAtTime(masterState, now, 0.015);
    else masterGain.gain.value = masterState;
  }

  async function ensureReady() {
    if (ready) {
      if (context.state === "suspended") await context.resume();
      return;
    }

    playButton.disabled = true;
    playButton.textContent = "Chargement audio…";

    context = new (window.AudioContext || window.webkitAudioContext)({latencyHint:"interactive"});
    masterGain = context.createGain();
    masterGain.gain.value = masterState;
    masterGain.connect(context.destination);

    decoded = [];
    trackNodes = [];

    for (let i = 0; i < defs.length; i += 1) {
      const buffer = await context.decodeAudioData(decodeBase64(String(defs[i].base64 || "")));
      decoded.push(buffer);

      const lowLP = context.createBiquadFilter();
      lowLP.type = "lowpass";
      lowLP.frequency.value = 250;
      lowLP.Q.value = 0.707;

      const midHP = context.createBiquadFilter();
      midHP.type = "highpass";
      midHP.frequency.value = 250;
      midHP.Q.value = 0.707;

      const midLP = context.createBiquadFilter();
      midLP.type = "lowpass";
      midLP.frequency.value = 4000;
      midLP.Q.value = 0.707;

      const highHP = context.createBiquadFilter();
      highHP.type = "highpass";
      highHP.frequency.value = 4000;
      highHP.Q.value = 0.707;

      const lowGain = context.createGain();
      const midGain = context.createGain();
      const highGain = context.createGain();
      const bandSum = context.createGain();
      const trackGain = context.createGain();

      lowLP.connect(lowGain);
      lowGain.connect(bandSum);

      midHP.connect(midLP);
      midLP.connect(midGain);
      midGain.connect(bandSum);

      highHP.connect(highGain);
      highGain.connect(bandSum);

      bandSum.connect(trackGain);
      trackGain.connect(masterGain);

      trackNodes.push({
        lowLP, midHP, midLP, highHP,
        lowGain, midGain, highGain,
        bandSum, trackGain,
      });
      if (i === 0) duration = Number(buffer.duration || 0);
    }

    seek.max = String(Math.max(0.001, duration));
    ready = true;

    // Re-apply latest UI state after decoding, fixing pre-play mute/volume races.
    trackState.forEach((_, i) => applyTrackState(i, false));
    applyMasterState(false);

    playButton.disabled = false;
    playButton.textContent = "▶ Lecture";
  }

  function stopSources() {
    sources.forEach((source) => {
      try { source.stop(); } catch (_) {}
      try { source.disconnect(); } catch (_) {}
    });
    sources = [];
  }

  function startSources(offset) {
    stopSources();
    const when = context.currentTime + 0.030;

    sources = decoded.map((buffer, index) => {
      const source = context.createBufferSource();
      source.buffer = buffer;
      source.connect(trackNodes[index].lowLP);
      source.connect(trackNodes[index].midHP);
      source.connect(trackNodes[index].highHP);
      const safeOffset = Math.max(
        0,
        Math.min(Number(offset) || 0, Math.max(0, buffer.duration - 0.001))
      );
      source.start(when, safeOffset);
      return source;
    });

    position = Math.max(0, Math.min(duration, Number(offset) || 0));
    startedAtContextTime = when;
    playing = true;
  }

  async function playAll() {
    await ensureReady();
    if (context.state === "suspended") await context.resume();
    if (playing) return;
    if (position >= duration - 0.01) position = 0;
    startSources(position);
  }

  function pauseAll() {
    if (!playing) return;
    position = currentTime();
    playing = false;
    stopSources();
  }

  function stopAll() {
    playing = false;
    stopSources();
    position = 0;
    seek.value = "0";
    renderLyrics(0);
    timeLabel.textContent = "0:00 / " + fmt(duration);
  }

  function seekTo(time) {
    const t = Math.max(0, Math.min(duration, Number(time) || 0));
    position = t;
    if (playing) startSources(t);
    renderLyrics(t);
  }

  function makeSlider(index, field, min, max, step, suffix, categoryClass = "") {
    const wrap = document.createElement("div");
    wrap.className = "control-cell" + (categoryClass ? " " + categoryClass : "");

    const slider = document.createElement("input");
    slider.type = "range";
    slider.min = String(min);
    slider.max = String(max);
    slider.step = String(step);
    slider.value = String(trackState[index][field]);

    const value = document.createElement("span");
    value.className = "control-value";

    function renderValue() {
      const v = Number(slider.value);
      value.textContent = suffix === "dB"
        ? ((v > 0 ? "+" : "") + v.toFixed(0) + " dB")
        : (Math.round(v * 100) + "%");
    }

    slider.addEventListener("input", () => {
      trackState[index][field] = Number(slider.value);
      renderValue();
      applyTrackState(index, true);
    });

    renderValue();
    wrap.append(slider, value);
    return {wrap, slider, value};
  }

  defs.forEach((track, index) => {
    const row = document.createElement("div");
    row.className = "track";

    const name = document.createElement("div");
    name.className = "track-name";
    name.textContent = String(track.label || track.name || "Track");

    const toggleWrap = document.createElement("label");
    toggleWrap.className = "track-toggle";
    const toggle = document.createElement("input");
    toggle.type = "checkbox";
    toggle.checked = trackState[index].enabled;
    const toggleText = document.createElement("span");
    toggleText.textContent = "Actif";
    toggle.addEventListener("change", () => {
      trackState[index].enabled = Boolean(toggle.checked);
      applyTrackState(index, true);
    });
    toggleWrap.append(toggle, toggleText);

    const volume = makeSlider(index, "volume", 0, 1.25, 0.01, "%", "volume-control");
    const low = makeSlider(index, "low", -6, 6, 1, "dB", "low-control");
    const mid = makeSlider(index, "mid", -6, 6, 1, "dB", "mid-control");
    const high = makeSlider(index, "high", -6, 6, 1, "dB", "high-control");

    const reset = document.createElement("button");
    reset.type = "button";
    reset.className = "eq-reset";
    reset.textContent = "Reset EQ";
    reset.addEventListener("click", () => {
      trackState[index].low = 0;
      trackState[index].mid = 0;
      trackState[index].high = 0;
      low.slider.value = "0";
      mid.slider.value = "0";
      high.slider.value = "0";
      low.value.textContent = "0 dB";
      mid.value.textContent = "0 dB";
      high.value.textContent = "0 dB";
      applyTrackState(index, true);
    });

    row.append(name, toggleWrap, volume.wrap, low.wrap, mid.wrap, high.wrap, reset);
    tracksNode.appendChild(row);
  });

  masterVolume.addEventListener("input", () => {
    masterState = Number(masterVolume.value);
    masterValue.textContent = Math.round(masterState * 100) + "%";
    applyMasterState(true);
  });

  const lyricNodes = words.map((word) => {
    const span = document.createElement("span");
    span.className = "lyric-word";
    span.textContent = String(word.text || "").trim();
    lyricsTrack.appendChild(span);
    return span;
  });
  if (!words.length) lyricsWrap.style.display = "none";

  function findWordIndex(time) {
    if (!words.length) return -1;
    let low = 0, high = words.length - 1, answer = 0;
    while (low <= high) {
      const middle = (low + high) >> 1;
      if (Number(words[middle].start || 0) <= time) {
        answer = middle; low = middle + 1;
      } else high = middle - 1;
    }
    return answer;
  }

  function renderLyrics(time) {
    if (!words.length) return;
    const index = findWordIndex(time);
    if (index < 0 || !lyricNodes[index]) return;

    if (index !== activeWordIndex) {
      activeWordIndex = index;
      lyricNodes.forEach((node, i) => {
        node.classList.toggle("past", i < index);
        node.classList.toggle("current", i === index);
      });
    }

    const current = lyricNodes[index];
    const next = lyricNodes[index + 1];
    const currentCenter = current.offsetLeft + current.offsetWidth / 2;
    let targetCenter = currentCenter;

    if (next) {
      const start = Number(words[index].start || 0);
      const nextStart = Math.max(start + 0.04, Number(words[index + 1].start || start + 0.5));
      const progress = Math.max(0, Math.min(1, (time - start) / (nextStart - start)));
      const nextCenter = next.offsetLeft + next.offsetWidth / 2;
      targetCenter = currentCenter + (nextCenter - currentCenter) * progress;
    }

    lyricsTrack.style.transform =
      "translate(" + (lyricsStrip.clientWidth / 2 - targetCenter) + "px,-50%)";
  }

  function tick() {
    if (disposed) return;
    const t = currentTime();
    seek.value = String(t);
    timeLabel.textContent = fmt(t) + " / " + fmt(duration);
    renderLyrics(t);
    if (playing && t >= duration - 0.01) stopAll();
    raf = requestAnimationFrame(tick);
  }

  playButton.addEventListener("click", playAll);
  pauseButton.addEventListener("click", pauseAll);
  stopButton.addEventListener("click", stopAll);
  seek.addEventListener("input", () => seekTo(Number(seek.value || 0)));

  tick();

  return function() {
    disposed = true;
    if (raf !== null) cancelAnimationFrame(raf);
    stopSources();
    try { if (context) context.close(); } catch (_) {}
  };
}
