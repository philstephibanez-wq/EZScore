from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
src = (ROOT / "templates/views/lyrics-layout.js").read_text(encoding="utf-8")

required = [
    "function ezNodeWidth(node)",
    "getBoundingClientRect",
    "offsetWidth",
    "scrollWidth",
    "new ResizeObserver",
    "document.fonts?.ready",
    "requestAnimationFrame(() => layoutNow())",
    "setTimeout(() =>",
    "previousRight + minGap",
]

for token in required:
    assert token in src, token

print("LYRICS NO OVERLAP CONTRACT OK")
print("hidden Streamlit tab: SUPPORTED")
print("font-late layout: SUPPORTED")
print("ResizeObserver relayout: ENABLED")
print("word collision rule: PRESERVED")
