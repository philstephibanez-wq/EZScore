/* Shared visual word-layout engine for EZScore. */
function ezIsContractionSuffix(text) {
  return /^[\'’]/.test(String(text || "").trim());
}

function ezLayoutLaneNodes({
  nodes,
  words,
  rawXForWord,
  minGap = 10,
  contractionGap = 1,
  breakAfter = null,
}) {
  const xs = [];
  let previousRight = Number.NEGATIVE_INFINITY;

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
      const previousLeft = Number.parseFloat(previous?.style.left || "0");
      const previousWidth = Math.max(
        1,
        Number(previous?.getBoundingClientRect?.().width || previous?.offsetWidth || 0)
      );

      visualX = isSuffix
        ? previousLeft + previousWidth + contractionGap
        : Math.max(rawX, previousRight + minGap);
    }

    node.style.left = visualX + "px";
    node.dataset.timelineX = String(rawX);

    const width = Math.max(
      1,
      Number(node.getBoundingClientRect?.().width || node.offsetWidth || 0)
    );
    previousRight = visualX + width;
    xs.push(visualX);
  });

  return {
    xs,
    right: Number.isFinite(previousRight) ? previousRight : 0,
  };
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
    return xs[last] + Math.max(0, t - Number(words[last].start || 0)) * 28;
  }

  const ta = Number(words[left].start || 0);
  const tb = Math.max(
    ta + .04,
    Number(words[left + 1].start || ta + .04)
  );
  const progress = Math.max(0, Math.min(1, (t - ta) / (tb - ta)));

  return xs[left] + (xs[left + 1] - xs[left]) * progress;
}
