(() => {
'use strict';

/**
 * EZScore shared fixed-focus track.
 *
 * Historical model restored from R37.2 / R38.1:
 * a fixed viewport + one inner track moved with translate3d().
 * No native horizontal scrolling is used for realtime following.
 */
class EZScoreFocusTrack {
    constructor(viewport, options = {}) {
        if (!(viewport instanceof Element)) {
            throw new TypeError('EZScoreFocusTrack requires a viewport Element');
        }
        this.viewport = viewport;
        this.track = options.track ?? null;
        this.target = options.target ?? null;
        this.fallbackRatio = typeof options.fallbackRatio === 'function'
            ? options.fallbackRatio
            : () => Number(options.fallbackRatio ?? 0.25);
    }

    resolve(value) {
        return typeof value === 'function' ? value() : value;
    }

    resolveTrack() {
        const el = this.resolve(this.track);
        return el instanceof Element ? el : null;
    }

    targetCenterX() {
        const target = this.resolve(this.target);
        if (target instanceof Element && target.isConnected && !target.hidden) {
            const r = target.getBoundingClientRect();
            return r.left + r.width / 2;
        }
        const r = this.viewport.getBoundingClientRect();
        const ratio = Math.max(0, Math.min(1, Number(this.fallbackRatio()) || 0));
        return r.left + r.width * ratio;
    }

    localCenterX(item) {
        const track = this.resolveTrack();
        if (!(item instanceof Element) || !track) return null;
        const ir = item.getBoundingClientRect();
        const tr = track.getBoundingClientRect();
        return (ir.left + ir.width / 2) - tr.left;
    }

    moveLocalX(sourceX) {
        const track = this.resolveTrack();
        if (!track || !Number.isFinite(Number(sourceX))) return false;

        const vr = this.viewport.getBoundingClientRect();
        const targetInViewport = this.targetCenterX() - vr.left;
        const tx = targetInViewport - Number(sourceX);

        track.style.transform = `translate3d(${tx}px,0,0)`;
        return true;
    }

    alignBetween(itemA, itemB, progress = 0) {
        const a = this.localCenterX(itemA);
        if (a === null) return false;

        const b = this.localCenterX(itemB);
        const p = Math.max(0, Math.min(1, Number(progress) || 0));
        const x = b === null ? a : a + (b - a) * p;

        return this.moveLocalX(x);
    }
}

window.EZScoreFocusTrack = EZScoreFocusTrack;
})();
