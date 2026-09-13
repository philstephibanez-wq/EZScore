"""Continuous right-to-left chord/lyrics ribbon assets."""

RIBBON_HTML = """
<div class="ez-ribbon">
  <div class="ez-ribbon-center"></div>
  <div class="ez-ribbon-diagram" aria-hidden="true"></div>
  <div class="ez-ribbon-track"></div>
</div>
"""

RIBBON_CSS = """
.ez-ribbon {
  position: relative;
  overflow: hidden;
  height: 112px;
  margin-top: 10px;
  border-radius: 10px;
  background: rgba(127,127,127,.08);
}
.ez-ribbon-center {
  position: absolute;
  left: 50%;
  top: 0;
  bottom: 0;
  width: 2px;
  background: rgba(77,163,255,.85);
  z-index: 2;
}
.ez-ribbon-track {
  position: absolute;
  left: 50%;
  top: 10px;
  white-space: nowrap;
  will-change: transform;
  transition: transform 70ms linear;
}
.ez-ribbon-item {
  display: inline-flex;
  flex-direction: column;
  justify-content: center;
  min-width: 170px;
  padding: 0 18px;
  box-sizing: border-box;
  text-align: center;
}
.ez-ribbon-chord {
  font-size: 28px;
  font-weight: 800;
}
.ez-ribbon-lyric {
  font-size: 18px;
  margin-top: 8px;
  opacity: .90;
}
.ez-ribbon-diagram {
  display: none;
}
.ez-ribbon.has-diagram {
  height: 250px;
}
.ez-ribbon.has-diagram .ez-ribbon-diagram {
  display: block;
  position: absolute;
  z-index: 3;
  top: 6px;
  left: 50%;
  transform: translateX(-50%);
  min-width: 118px;
  min-height: 145px;
  padding: 2px 6px;
  border-radius: 10px;
  background: color-mix(in srgb, var(--st-text-color) 7%, transparent);
  text-align: center;
}
.ez-ribbon.has-diagram .ez-ribbon-track {
  top: 165px;
}
@media (max-width: 640px) {
  .ez-ribbon {
    height: 96px;
  }
  .ez-ribbon-item {
    min-width: 125px;
    padding: 0 10px;
  }
  .ez-ribbon-chord {
    font-size: 23px;
  }
  .ez-ribbon-lyric {
    font-size: 15px;
  }
  .ez-ribbon.has-diagram {
    height: 225px;
  }
  .ez-ribbon.has-diagram .ez-ribbon-track {
    top: 150px;
  }
  .ez-ribbon.has-diagram .ez-ribbon-diagram svg {
    width: 100px;
    height: 132px;
  }
}
"""
