/* Shared visual word-layout engine for EZScore.

R1 visibility-safe layout:
Streamlit may mount the Paroles component while its tab is hidden. In that
state getBoundingClientRect()/offsetWidth can report 0 or 1px, which made the
initial collision pass believe every word was almost widthless. When the tab
became visible, the real glyph widths appeared and words overlapped.

This implementation keeps the historical visual layout contract but reruns the
same calculation once the lane is actually measurable.
*/

function ezIsContractionSuffix(text) {
  return /^[\'’]/.test(String(text || "").trim());
}

function ezNodeWidth(node) {
  if (!node) return 0;

  const rectWidth = Number(
    node.getBoundingClientRect?.().width || 0
  );
  const offsetWidth = Number(node.offsetWidth || 0);
  const scrollWidth = Number(node.scrollWidth || 0);

  return Math.max(rectWidth, offsetWidth, scrollWidth, 0);
}

function ezLayoutLaneNodes({
  nodes,
  words,
  rawXForWord,
  minGap = 10,
  contractionGap = 1,
  breakAfter = null,
}) {
  const lane = nodes?.[0]?.parentElement || null;

  function layoutNow() {
    const xs = [];
    let previousRight = Number.NEGATIVE_INFINITY;
    let measurableCount = 0;

    nodes.forEach((node, index) => {
      const word = words[index] || {};
      const rawX = Number(rawXForWord(word, index) || 0);
      let visualX = rawX;

      const isSuffix = (
        index > 0
        && ezIsContractionSuffix(word.text)
        && !(breakAfter && breakAfter(index - 1))
      );

      if (index > 0) {
        const previous = nodes[index - 1];
        const previousLeft = Number.parseFloat(
          previous?.style.left || "0"
        );
        const previousWidth = ezNodeWidth(previous);

        if (previousWidth > 2) {
          measurableCount += 1;
        }

        visualX = isSuffix
          ? previousLeft + Math.max(1, previousWidth) + contractionGap
          : Math.max(
              rawX,
              previousRight + minGap
            );
      }

      node.style.left = visualX + "px";
      node.dataset.timelineX = String(rawX);

      const width = ezNodeWidth(node);
      if (width > 2) {
        measurableCount += 1;
      }

      previousRight = visualX + Math.max(1, width);
      xs.push(visualX);
    });

    return {
      xs,
      right: Number.isFinite(previousRight) ? previousRight : 0,
      measurable: nodes.length === 0 || measurableCount > 0,
    };
  }

  const first = layoutNow();

  if (!lane || !nodes.length) {
    return first;
  }

  // A component mounted in an inactive Streamlit tab can be widthless.
  // Re-run when its lane becomes visible/resized.
  if (lane.__ezscoreWordLayoutObserver) {
    try {
      lane.__ezscoreWordLayoutObserver.disconnect();
    } catch (_) {}
  }

  const observer = new ResizeObserver(() => {
    if (!lane.isConnected) {
      try { observer.disconnect(); } catch (_) {}
      return;
    }

    if (lane.getBoundingClientRect().width > 0) {
      requestAnimationFrame(() => layoutNow());
    }
  });

  lane.__ezscoreWordLayoutObserver = observer;
  observer.observe(lane);

  // Fonts can settle after the component has already rendered.
  if (document.fonts?.ready) {
    document.fonts.ready.then(() => {
      if (!lane.isConnected) return;
      requestAnimationFrame(() => layoutNow());
    }).catch(() => {});
  }

  // Two small delayed passes cover tab activation / browser paint ordering.
  requestAnimationFrame(() => layoutNow());
  setTimeout(() => {
    if (lane.isConnected) layoutNow();
  }, 80);
  setTimeout(() => {
    if (lane.isConnected) layoutNow();
  }, 280);

  return first;
}

function ezVisualXForTime(words, xs, time, rawXForTime) {
  if (!Array.isArray(words) || !words.length || words.length !== xs.length) {
    return Number(rawXForTime(time) || 0);
  }

  const t = Number(time || 0);
  if (words.length === 1) return xs[0];

  if (t <= Number(words[0].start || 0)) {
    const firstTime = Math.max(.001, Number(words[0].start || 0));
    const progress = Math.max(0, Math.min(1, t / firstTime));
    return Math.max(0, xs[0] * progress);
  }

  let low = 0;
  let high = words.length - 1;
  let left = 0;

  while (low <= high) {
    const mid = (low + high) >> 1;
    if (Number(words[mid].start || 0) <= t) {
      left = mid;
      low = mid + 1;
    } else {
      high = mid - 1;
    }
  }

  if (left >= words.length - 1) {
    const last = words.length - 1;
    return xs[last] + Math.max(
      0,
      t - Number(words[last].start || 0)
    ) * 28;
  }

  const ta = Number(words[left].start || 0);
  const tb = Math.max(
    ta + .04,
    Number(words[left + 1].start || ta + .04)
  );
  const progress = Math.max(
    0,
    Math.min(1, (t - ta) / (tb - ta))
  );

  return xs[left] + (xs[left + 1] - xs[left]) * progress;
}
