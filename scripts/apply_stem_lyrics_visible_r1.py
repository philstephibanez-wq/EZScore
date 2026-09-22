from __future__ import annotations

import ast
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "ezscore" / "player" / "stem_analysis_conductor.py"
EXPECTED_HEAD = '4abd2dd3cbc1e0b8a0d3fe39f5840230e3085282'


def replace_once(source, old, new, label):
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: attendu 1 motif, trouvé {count}. Aucun fichier modifié.")
    return source.replace(old, new, 1)


def replace_region(source, start_marker, end_marker, replacement, label):
    start = source.find(start_marker)
    if start < 0:
        raise RuntimeError(f"{label}: début introuvable.")
    end = source.find(end_marker, start)
    if end < 0:
        raise RuntimeError(f"{label}: fin introuvable.")
    return source[:start] + replacement + source[end:]


head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
if head != EXPECTED_HEAD:
    raise RuntimeError(
        f"HEAD inattendu. Attendu={EXPECTED_HEAD} Trouvé={head}. "
        "Patch bloqué pour ne pas modifier une autre version."
    )

source = TARGET.read_text(encoding="utf-8")
source = replace_once(source, '_TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "templates" / "views"\n_LYRICS_LAYOUT_JS = (_TEMPLATE_DIR / "lyrics-layout.js").read_text(encoding="utf-8")\n\n', '', "layout Paroles")
source = replace_once(source, '_JS = _LYRICS_LAYOUT_JS + "\\n\\n" + base._PLAYER_JS\n', '_JS = base._PLAYER_JS\n', "JS autonome")
source = replace_region(
    source,
    "conductor_js = r'''  // Continuous STEM conductor: one chord row + one lyric row.\n",
    "\n'''\n\n_JS = _replace_region(\n",
    'conductor_js = r\'\'\'  // Continuous STEM conductor: one chord row + one lyric row.\n  // Restore the known-good STEM layout: absolute original-audio seconds.\n\n  function normalizedWords(input) {\n    const sorted=(Array.isArray(input) ? input : [])\n      .map(w => ({\n        text:String(w.text ?? w.word ?? "").trim(),\n        start:Number(w.start || 0),\n        end:Number(w.end ?? w.start ?? 0),\n      }))\n      .filter(w =>\n        w.text &&\n        Number.isFinite(w.start) &&\n        Number.isFinite(w.end) &&\n        w.end >= w.start\n      )\n      .sort((a,b)=>a.start-b.start || a.end-b.end);\n\n    const merged=[];\n    sorted.forEach(w => {\n      const previous=merged.length ? merged[merged.length-1] : null;\n      if (previous && Math.abs(w.start-previous.start) <= .005) {\n        previous.text=(previous.text+" "+w.text).trim();\n        previous.end=Math.max(previous.end,w.end);\n      } else {\n        merged.push({...w});\n      }\n    });\n    return merged;\n  }\n\n  const words=normalizedWords(rawWords);\n\n  function vocalDisplayText(word) {\n    const text=String(word.text || "").trim();\n    const duration=Math.max(0,Number(word.end || 0)-Number(word.start || 0));\n    const letters=Math.max(1,(text.match(/[A-Za-zÀ-ÖØ-öø-ÿĀ-ž]/g) || []).length);\n    const expected=Math.min(.72,.24 + letters*.055);\n    const excess=Math.max(0,duration-expected);\n    const count=excess >= .24\n      ? Math.min(8,Math.max(1,Math.round(excess/.22)))\n      : 0;\n    return text + "_".repeat(count);\n  }\n\n  const lyricNodes=words.map(word => {\n    const span=document.createElement("span");\n    span.className="lyric-word";\n    span.textContent=vocalDisplayText(word);\n    span.dataset.wordStart=String(word.start);\n    lyricsTrack.appendChild(span);\n    return span;\n  });\n\n  function chordAt(index) {\n    return String(beats[index]?.chord || ".").trim() || ".";\n  }\n\n  const chordItems=beats.map((beat,index) => {\n    const localBeat=index % beatsPerMeasure;\n    const chord=chordAt(index);\n    const previous=index>0 ? chordAt(index-1) : ".";\n    const token=localBeat===0\n      ? chord\n      : (chord===previous && chord!=="." ? "-" : chord);\n\n    return {\n      index,\n      time:Number(beat.time ?? beat.start ?? 0),\n      chord,\n      token,\n      measureStart:localBeat===0,\n    };\n  }).filter(item => Number.isFinite(item.time));\n\n  const chordNodes=[];\n  chordItems.forEach(item => {\n    const span=document.createElement("span");\n    span.className="chord-token" + (item.measureStart ? " measure-start" : "");\n    span.textContent=item.token;\n    chordTrack.appendChild(span);\n    chordNodes.push(span);\n  });\n\n  let pixelsPerSecond=96;\n\n  function computeGlobalScale() {\n    let required=96;\n\n    for (let i=0;i<words.length-1;i++) {\n      const dt=Number(words[i+1].start)-Number(words[i].start);\n      if (!(dt > .005)) continue;\n\n      const width=Math.max(\n        1,\n        Number(\n          lyricNodes[i]?.getBoundingClientRect?.().width ||\n          lyricNodes[i]?.offsetWidth ||\n          lyricNodes[i]?.scrollWidth ||\n          1\n        )\n      );\n      required=Math.max(required,(width+16)/dt);\n    }\n\n    pixelsPerSecond=Math.max(96,required);\n  }\n\n  function xForTime(time) {\n    return Math.max(0,Number(time || 0))*pixelsPerSecond;\n  }\n\n  function layoutConductor() {\n    computeGlobalScale();\n\n    lyricNodes.forEach((node,index) => {\n      const x=xForTime(words[index].start);\n      node.style.left=x+"px";\n      node.dataset.timelineX=String(x);\n    });\n\n    chordNodes.forEach((node,index) => {\n      const x=xForTime(chordItems[index].time);\n      node.style.left=x+"px";\n      node.dataset.timelineX=String(x);\n    });\n\n    const lastWordEnd=words.length\n      ? Math.max(...words.map(w=>Number(w.end || w.start || 0)))\n      : 0;\n    const lastBeatTime=chordItems.length\n      ? Number(chordItems[chordItems.length-1].time || 0)\n      : 0;\n    const width=xForTime(Math.max(lastWordEnd,lastBeatTime)+4);\n\n    lyricsTrack.style.width=Math.max(1,width)+"px";\n    chordTrack.style.width=Math.max(1,width)+"px";\n  }\n\n  function findWordIndex(time) {\n    if (!words.length) return -1;\n    let low=0,high=words.length-1,answer=-1;\n    while (low<=high) {\n      const middle=(low+high)>>1;\n      if (words[middle].start<=time) {\n        answer=middle;\n        low=middle+1;\n      } else {\n        high=middle-1;\n      }\n    }\n    return answer;\n  }\n\n  function findBeatIndex(time) {\n    if (!chordItems.length) return -1;\n    let low=0,high=chordItems.length-1,answer=-1;\n    while (low<=high) {\n      const middle=(low+high)>>1;\n      if (chordItems[middle].time<=time) {\n        answer=middle;\n        low=middle+1;\n      } else {\n        high=middle-1;\n      }\n    }\n    return answer;\n  }\n\n  function updateDiagram(beatIndex) {\n    if (!currentDiagram) return;\n    if (!showDiagrams || beatIndex<0 || !chordItems[beatIndex]) {\n      currentDiagram.classList.remove("visible");\n      currentDiagram.innerHTML="";\n      return;\n    }\n\n    const chord=String(chordItems[beatIndex].chord || ".");\n    const svg=String(chordDiagrams[chord] || "");\n    if (!svg) {\n      currentDiagram.classList.remove("visible");\n      currentDiagram.innerHTML="";\n      return;\n    }\n\n    currentDiagram.innerHTML=svg;\n    currentDiagram.classList.add("visible");\n  }\n\n  function renderConductor(time) {\n    const t=Math.max(0,Number(time || 0));\n    const anchor=Math.max(90,lyricsStrip.clientWidth*.35);\n    const translate=anchor-xForTime(t);\n\n    lyricsTrack.style.transform="translate3d("+translate.toFixed(2)+"px,0,0)";\n    chordTrack.style.transform="translate3d("+translate.toFixed(2)+"px,0,0)";\n\n    const wordIndex=findWordIndex(t);\n    if (wordIndex!==activeWordIndex) {\n      activeWordIndex=wordIndex;\n      lyricNodes.forEach((node,index) => {\n        node.classList.toggle("past",index<wordIndex);\n        node.classList.toggle("current",index===wordIndex);\n      });\n    }\n\n    const beatIndex=findBeatIndex(t);\n    chordNodes.forEach((node,index) => {\n      node.classList.toggle("current",index===beatIndex);\n    });\n    updateDiagram(beatIndex);\n  }\n\n  if (!words.length && !chordItems.length) {\n    conductorWrap.style.display="none";\n  } else {\n    layoutConductor();\n  }\n\n  try {\n    const saved=localStorage.getItem(diagramStorageKey);\n    if (saved==="1" || saved==="0") {\n      showDiagrams=saved==="1";\n    }\n  } catch (_) {}\n\n  diagramCheckbox.checked=showDiagrams;\n  diagramCheckbox.addEventListener("change",() => {\n    showDiagrams=Boolean(diagramCheckbox.checked);\n    try {\n      localStorage.setItem(diagramStorageKey,showDiagrams ? "1" : "0");\n    } catch (_) {}\n    renderConductor(currentTime());\n  });\n\n  function relayoutStemConductor() {\n    if (!lyricsTrack.isConnected || !chordTrack.isConnected) return;\n    layoutConductor();\n    renderConductor(currentTime());\n  }\n\n  window.addEventListener("resize",() => {\n    requestAnimationFrame(relayoutStemConductor);\n  });\n\n  requestAnimationFrame(relayoutStemConductor);\n  setTimeout(relayoutStemConductor,80);\n  setTimeout(relayoutStemConductor,280);\n\n  if (document.fonts?.ready) {\n    document.fonts.ready.then(() => {\n      if (!lyricsTrack.isConnected) return;\n      requestAnimationFrame(relayoutStemConductor);\n    }).catch(() => {});\n  }\n\n  renderConductor(0);\n\n\'\'\'\n\n',
    "conducteur STEM",
)
source = replace_once(source, '    player_words = list(words or [])\n    if not player_words:\n        forced = load_alignment(audio_hash) or {}\n        player_words = list(forced.get("words", []) or [])\n', '    forced = load_alignment(audio_hash) or {}\n    forced_words = list(forced.get("words", []) or [])\n    player_words = forced_words or list(words or [])\n', "paroles MMS_FA prioritaires")
source = replace_once(source, '"ezscore_stem_analysis_conductor_r1",', '"ezscore_stem_analysis_conductor_r2",', "identité composant")
source = replace_once(source, '.lyric-word {\n  margin:0;\n  font-size:18px;\n  opacity:.34;\n', '.lyric-word {\n  margin:0;\n  font-size:18px;\n  color:var(--st-text-color);\n  opacity:.42;\n', "CSS paroles")

ast.parse(source, filename=str(TARGET))

with tempfile.TemporaryDirectory(prefix="ezscore_stem_lyrics_r1_") as td:
    candidate = Path(td) / TARGET.name
    candidate.write_text(source, encoding="utf-8")
    ast.parse(candidate.read_text(encoding="utf-8"), filename=str(candidate))

    backup_root = Path("H:/temp") if Path("H:/temp").exists() else ROOT / ".ezscore_patch_backup"
    backup_root.mkdir(parents=True, exist_ok=True)
    backup = backup_root / "stem_analysis_conductor.before_STEM_LYRICS_VISIBLE_R1.py"
    shutil.copy2(TARGET, backup)
    shutil.copy2(candidate, TARGET)

print("EZScore_STEM_LYRICS_VISIBLE_R1 appliqué.")
print("Modifié : ezscore/player/stem_analysis_conductor.py")
print("Backup :", backup)
