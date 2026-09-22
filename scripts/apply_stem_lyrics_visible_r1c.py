from __future__ import annotations

import ast
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "ezscore" / "player" / "stem_analysis_conductor.py"
EXPECTED_HEAD = "4abd2dd3cbc1e0b8a0d3fe39f5840230e3085282"

head = subprocess.check_output(
    ["git", "rev-parse", "HEAD"],
    cwd=ROOT,
    text=True,
).strip()

if head != EXPECTED_HEAD:
    raise RuntimeError(
        f"HEAD inattendu. Attendu={EXPECTED_HEAD} Trouvé={head}. "
        "Aucun fichier modifié."
    )

source = TARGET.read_text(encoding="utf-8")

start_marker = (
    "conductor_js = r" + "&#39;&#39;&#39;".replace("&#39;", chr(39))
    + "  // Continuous STEM conductor: one chord row + one lyric row.\n"
)
end_marker = (
    "\n" + "&#39;&#39;&#39;".replace("&#39;", chr(39))
    + "\n\n_JS = _replace_region(\n"
)

start = source.find(start_marker)
if start < 0:
    raise RuntimeError("Début du conductor_js introuvable. Aucun fichier modifié.")

end = source.find(end_marker, start)
if end < 0:
    raise RuntimeError("Fin du conductor_js introuvable. Aucun fichier modifié.")

body = '  // Continuous STEM conductor: one chord row + one lyric row.\n  // Known-good STEM layout restored: one absolute audio-time scale for\n  // chords and lyrics. No visual remapping through the Paroles editor.\n\n  function normalizedWords(input) {\n    const sorted=(Array.isArray(input) ? input : [])\n      .map(w => ({\n        text:String(w.text || w.word || "").trim(),\n        start:Number(w.start || 0),\n        end:Number(w.end ?? w.start ?? 0),\n      }))\n      .filter(w =>\n        w.text &&\n        Number.isFinite(w.start) &&\n        Number.isFinite(w.end) &&\n        w.end >= w.start\n      )\n      .sort((a,b)=>a.start-b.start || a.end-b.end);\n\n    const merged=[];\n    sorted.forEach(w => {\n      const previous=merged.length ? merged[merged.length-1] : null;\n      if (previous && Math.abs(w.start-previous.start) <= .005) {\n        previous.text=(previous.text+" "+w.text).trim();\n        previous.end=Math.max(previous.end,w.end);\n      } else {\n        merged.push({...w});\n      }\n    });\n    return merged;\n  }\n\n  const words=normalizedWords(rawWords);\n\n  function vocalDisplayText(word) {\n    const text=String(word.text || "").trim();\n    const duration=Math.max(0,Number(word.end || 0)-Number(word.start || 0));\n    const letters=Math.max(\n      1,\n      (text.match(/[A-Za-zÀ-ÖØ-öø-ÿĀ-ž]/g) || []).length\n    );\n    const expected=Math.min(.72,.24 + letters*.055);\n    const excess=Math.max(0,duration-expected);\n    const count=excess >= .24\n      ? Math.min(8,Math.max(1,Math.round(excess/.22)))\n      : 0;\n    return text + "_".repeat(count);\n  }\n\n  const lyricNodes=words.map(word => {\n    const span=document.createElement("span");\n    span.className="lyric-word";\n    span.textContent=vocalDisplayText(word);\n    lyricsTrack.appendChild(span);\n    return span;\n  });\n\n  function chordAt(index) {\n    return String(beats[index]?.chord || ".").trim() || ".";\n  }\n\n  const chordItems=beats.map((beat,index) => {\n    const localBeat=index % beatsPerMeasure;\n    const chord=chordAt(index);\n    const previous=index>0 ? chordAt(index-1) : ".";\n    const token=localBeat===0\n      ? chord\n      : (chord===previous && chord!=="." ? "-" : chord);\n\n    return {\n      index,\n      time:Number(beat.time ?? beat.start ?? 0),\n      chord,\n      token,\n      measureStart:localBeat===0,\n    };\n  }).filter(item => Number.isFinite(item.time));\n\n  const chordNodes=[];\n  chordItems.forEach(item => {\n    const span=document.createElement("span");\n    span.className="chord-token" + (item.measureStart ? " measure-start" : "");\n    span.textContent=item.token;\n    chordTrack.appendChild(span);\n    chordNodes.push(span);\n  });\n\n  let pixelsPerSecond=96;\n\n  function computeGlobalScale() {\n    let required=96;\n\n    for (let i=0;i<words.length-1;i++) {\n      const dt=Number(words[i+1].start)-Number(words[i].start);\n      if (!(dt > .005)) continue;\n\n      const width=Math.max(\n        1,\n        Number(\n          lyricNodes[i]?.getBoundingClientRect?.().width ||\n          lyricNodes[i]?.offsetWidth ||\n          lyricNodes[i]?.scrollWidth ||\n          1\n        )\n      );\n\n      required=Math.max(required,(width+16)/dt);\n    }\n\n    pixelsPerSecond=Math.max(96,required);\n  }\n\n  function xForTime(time) {\n    return Math.max(0,Number(time || 0))*pixelsPerSecond;\n  }\n\n  function layoutConductor() {\n    computeGlobalScale();\n\n    lyricNodes.forEach((node,index) => {\n      node.style.left=xForTime(words[index].start)+"px";\n    });\n\n    chordNodes.forEach((node,index) => {\n      node.style.left=xForTime(chordItems[index].time)+"px";\n    });\n\n    const lastWordEnd=words.length\n      ? Math.max(...words.map(w=>Number(w.end || w.start || 0)))\n      : 0;\n    const lastBeatTime=chordItems.length\n      ? Number(chordItems[chordItems.length-1].time || 0)\n      : 0;\n    const width=xForTime(Math.max(lastWordEnd,lastBeatTime)+4);\n\n    lyricsTrack.style.width=Math.max(1,width)+"px";\n    chordTrack.style.width=Math.max(1,width)+"px";\n  }\n\n  function findWordIndex(time) {\n    if (!words.length) return -1;\n    let low=0,high=words.length-1,answer=-1;\n\n    while (low<=high) {\n      const middle=(low+high)>>1;\n      if (words[middle].start<=time) {\n        answer=middle;\n        low=middle+1;\n      } else {\n        high=middle-1;\n      }\n    }\n\n    return answer;\n  }\n\n  function findBeatIndex(time) {\n    if (!chordItems.length) return -1;\n    let low=0,high=chordItems.length-1,answer=-1;\n\n    while (low<=high) {\n      const middle=(low+high)>>1;\n      if (chordItems[middle].time<=time) {\n        answer=middle;\n        low=middle+1;\n      } else {\n        high=middle-1;\n      }\n    }\n\n    return answer;\n  }\n\n  function updateDiagram(beatIndex) {\n    if (!currentDiagram) return;\n\n    if (!showDiagrams || beatIndex<0 || !chordItems[beatIndex]) {\n      currentDiagram.classList.remove("visible");\n      currentDiagram.innerHTML="";\n      return;\n    }\n\n    const chord=String(chordItems[beatIndex].chord || ".");\n    const svg=String(chordDiagrams[chord] || "");\n\n    if (!svg) {\n      currentDiagram.classList.remove("visible");\n      currentDiagram.innerHTML="";\n      return;\n    }\n\n    currentDiagram.innerHTML=svg;\n    currentDiagram.classList.add("visible");\n  }\n\n  function renderConductor(time) {\n    const t=Math.max(0,Number(time || 0));\n    const anchor=Math.max(90,lyricsStrip.clientWidth*.35);\n    const translate=anchor-xForTime(t);\n\n    lyricsTrack.style.transform="translate3d("+translate.toFixed(2)+"px,0,0)";\n    chordTrack.style.transform="translate3d("+translate.toFixed(2)+"px,0,0)";\n\n    const wordIndex=findWordIndex(t);\n\n    if (wordIndex!==activeWordIndex) {\n      activeWordIndex=wordIndex;\n      lyricNodes.forEach((node,index) => {\n        node.classList.toggle("past",index<wordIndex);\n        node.classList.toggle("current",index===wordIndex);\n      });\n    }\n\n    const beatIndex=findBeatIndex(t);\n\n    chordNodes.forEach((node,index) => {\n      node.classList.toggle("current",index===beatIndex);\n    });\n\n    updateDiagram(beatIndex);\n  }\n\n  if (!words.length && !chordItems.length) {\n    conductorWrap.style.display="none";\n  } else {\n    layoutConductor();\n  }\n\n  try {\n    const saved=localStorage.getItem(diagramStorageKey);\n\n    if (saved==="1" || saved==="0") {\n      showDiagrams=saved==="1";\n    }\n  } catch (_) {}\n\n  diagramCheckbox.checked=showDiagrams;\n\n  diagramCheckbox.addEventListener("change",() => {\n    showDiagrams=Boolean(diagramCheckbox.checked);\n\n    try {\n      localStorage.setItem(\n        diagramStorageKey,\n        showDiagrams ? "1" : "0"\n      );\n    } catch (_) {}\n\n    renderConductor(currentTime());\n  });\n\n  function relayoutStemConductor() {\n    if (!lyricsTrack.isConnected || !chordTrack.isConnected) return;\n    layoutConductor();\n    renderConductor(currentTime());\n  }\n\n  window.addEventListener("resize",() => {\n    requestAnimationFrame(relayoutStemConductor);\n  });\n\n  requestAnimationFrame(relayoutStemConductor);\n  setTimeout(relayoutStemConductor,80);\n  setTimeout(relayoutStemConductor,280);\n\n  if (document.fonts?.ready) {\n    document.fonts.ready.then(() => {\n      if (!lyricsTrack.isConnected) return;\n      requestAnimationFrame(relayoutStemConductor);\n    }).catch(() => {});\n  }\n\n  renderConductor(0);\n'
replacement = (
    "conductor_js = r"
    + "&#39;&#39;&#39;".replace("&#39;", chr(39))
    + body
)

candidate_source = source[:start] + replacement + source[end:]

old_component = '"ezscore_stem_analysis_conductor_r1",'
new_component = '"ezscore_stem_analysis_conductor_r3",'
if candidate_source.count(old_component) != 1:
    raise RuntimeError(
        "Identité composant r1 absente/ambiguë. Aucun fichier modifié."
    )
candidate_source = candidate_source.replace(
    old_component,
    new_component,
    1,
)

old_css = ".lyric-word {\n  margin:0;\n  font-size:18px;\n  opacity:.34;\n"
new_css = ".lyric-word {\n  margin:0;\n  font-size:18px;\n  color:var(--st-text-color);\n  opacity:.42;\n"
if candidate_source.count(old_css) != 1:
    raise RuntimeError("Bloc CSS paroles absent/ambigu. Aucun fichier modifié.")
candidate_source = candidate_source.replace(old_css, new_css, 1)

# Validation du vrai source final AVANT toute écriture.
ast.parse(candidate_source, filename=str(TARGET))

with tempfile.TemporaryDirectory(prefix="ezscore_stem_lyrics_r1c_") as td:
    candidate = Path(td) / TARGET.name
    candidate.write_text(candidate_source, encoding="utf-8")
    ast.parse(candidate.read_text(encoding="utf-8"), filename=str(candidate))

    backup_root = (
        Path("H:/temp")
        if Path("H:/temp").exists()
        else ROOT / ".ezscore_patch_backup"
    )
    backup_root.mkdir(parents=True, exist_ok=True)
    backup = (
        backup_root
        / "stem_analysis_conductor.before_STEM_LYRICS_VISIBLE_R1c.py"
    )
    shutil.copy2(TARGET, backup)
    shutil.copy2(candidate, TARGET)

print("EZScore_STEM_LYRICS_VISIBLE_R1c appliqué.")
print("Modifié : ezscore/player/stem_analysis_conductor.py")
print("Backup :", backup)
