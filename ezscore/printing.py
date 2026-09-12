"""Printing helpers for EZScore."""

from __future__ import annotations

import html
import json
from pathlib import Path

import streamlit as st

from EZScoreTemplate import ScoreTemplateRenderer

_SCORE = ScoreTemplateRenderer(Path(__file__).resolve().parents[1])

_PRINT_PAGE_CONTENT_MM = 279.0
_PRINT_FIRST_PAGE_HEADER_MM = 32.0
_PRINT_GRID_ROW_MM = 7.0
_PRINT_GRID_BLOCK_MARGIN_MM = 3.0
_PRINT_LYRICS_TITLE_MM = 7.0
_PRINT_LYRICS_LINE_MM = 9.6
_PRINT_LYRICS_BLOCK_MARGIN_MM = 3.0


def print_song_header_html(title, artist, editor, version_label, source_status, tempo, signature, key_name, capo, measures_count, strumming_primary="", strumming_secondary=""):
    title = html.escape(str(title or "")); artist = html.escape(str(artist or "")); editor = html.escape(str(editor or ""))
    version_label = html.escape(str(version_label or "")); source_status = html.escape(str(source_status or ""))
    signature = html.escape(str(signature or "")); key_name = html.escape(str(key_name or ""))
    strumming_primary = html.escape(str(strumming_primary or "").strip()); strumming_secondary = html.escape(str(strumming_secondary or "").strip())
    title_line = title + (f" — {artist}" if artist else "")
    capo_label = "—" if int(capo or 0) == 0 else str(int(capo))
    strum = []
    if strumming_primary: strum.append(f"<strong>Strumming</strong> : {strumming_primary}")
    if strumming_secondary: strum.append(f"<strong>Alternatif</strong> : {strumming_secondary}")
    editor_html = f'<div class="print-editor">Éditeur : {editor}</div>' if editor else ""
    strum_html = '<div class="print-strumming">🎸 ' + " · ".join(strum) + "</div>" if strum else ""
    return ('<div class="print-song-header"><div class="print-title-row>' if False else '<div class="print-song-header"><div class="print-title-row">') + f'<div class="print-title">{title_line}</div><div class="print-version">· {version_label} · {source_status}</div></div>{editor_html}<div class="print-metrics"><span><b>Tempo</b> {float(tempo):.1f} BPM</span><span><b>Signature</b> {signature}</span><span><b>Tonalité</b> {key_name}</span><span><b>Capo</b> {capo_label}</span><span><b>Mesures</b> {int(measures_count)}</span></div>{strum_html}</div>'


def print_paginate_blocks(blocks, first_page_used_mm=0.0):
    rendered=[]; used_mm=max(0.0,float(first_page_used_mm or 0.0))
    for block in blocks:
        block_html=str(block.get("html","")); h=max(0.0,float(block.get("height_mm",0.0))); fits=h<=_PRINT_PAGE_CONTENT_MM
        if used_mm>0.0 and ((fits and used_mm+h>_PRINT_PAGE_CONTENT_MM) or not fits):
            rendered.append('<div class="print-page-break" aria-hidden="true"></div>'); used_mm=0.0
        rendered.append(block_html); used_mm=used_mm+h if fits else _PRINT_PAGE_CONTENT_MM
    return "".join(rendered)


def print_grid_block_height_mm(row_count):
    return max(1,int(row_count))*_PRINT_GRID_ROW_MM+_PRINT_GRID_BLOCK_MARGIN_MM


def print_lyrics_block_height_mm(line_count):
    return _PRINT_LYRICS_TITLE_MM+max(1,int(line_count))*_PRINT_LYRICS_LINE_MM+_PRINT_LYRICS_BLOCK_MARGIN_MM


def print_css_text(kind):
    return """
    @page { size: A4 portrait; margin: 9mm; }
    html, body { margin:0; padding:0; background:#fff; color:#000; font-family:Arial,Helvetica,sans-serif; }
    body { padding:0; } .print-sheet { width:100%; box-sizing:border-box; }
    .print-song-header { border-bottom:1.5px solid #111; padding:0 0 7px 0; margin:0 0 10px 0; }
    .print-title-row { display:flex; justify-content:space-between; align-items:baseline; gap:12px; }
    .print-title { font-size:20pt; font-weight:800; line-height:1.05; }
    .print-version { font-size:8.5pt; color:#444; white-space:nowrap; }
    .print-editor { font-size:8.5pt; margin-top:2px; color:#444; }
    .print-metrics { display:flex; flex-wrap:wrap; gap:5px 18px; font-size:9.5pt; margin-top:6px; }
    .print-strumming { font-size:10pt; margin-top:5px; }
    .print-page-break { display:block; height:0; margin:0; padding:0; break-before:page; page-break-before:always; }
    .print-grid-block { display:grid; grid-template-columns:82px minmax(0,1fr); gap:6px; align-items:start; margin:0 0 8px 0; break-inside:avoid; page-break-inside:avoid; }
    .print-grid-block.print-allow-split,.print-lyrics-block.print-allow-split { break-inside:auto; page-break-inside:auto; }
    .print-grid-block-name { font-size:11.5pt; font-weight:800; padding-top:3px; break-after:avoid; page-break-after:avoid; }
    table.print-chord-grid { border-collapse:collapse; table-layout:fixed; width:100%; font-family:Consolas,"Courier New",monospace; }
    table.print-chord-grid tr { break-inside:avoid; page-break-inside:avoid; }
    table.print-chord-grid td { border:1px solid #111; width:25%; height:22px; padding:2px 5px; vertical-align:middle; text-align:left; font-size:13.5pt; font-weight:800; line-height:1; white-space:nowrap; overflow:hidden; }
    .print-lyrics-block { margin:0 0 8px 0; break-inside:avoid; page-break-inside:avoid; }
    .print-lyrics-block-title { font-size:12pt; font-weight:800; margin:7px 0 3px 0; break-after:avoid; page-break-after:avoid; orphans:2; widows:2; }
    .print-lyrics-line { font-family:Consolas,"Courier New",monospace; break-inside:avoid; page-break-inside:avoid; margin:0 0 5px 0; orphans:2; widows:2; }
    .print-lyrics-first-line { break-before:avoid; page-break-before:avoid; }
    .print-lyrics-chords { white-space:pre; font-size:12pt; line-height:1; font-weight:800; }
    .print-lyrics-text { white-space:pre; font-size:13.5pt; line-height:1.04; font-weight:500; }
    @media print { html,body { margin:0!important; padding:0!important; } .print-sheet { width:100%!important; } }
    """


def make_print_document(kind, body_html, title="EZScore"):
    return _SCORE.render("templates/EZScore.score", {"document":{"lang":"fr","title":str(title),"css":print_css_text(kind),"body_class":f"ezscore-print ezscore-print-{kind}","body":str(body_html)}})


def print_icon(key_suffix, print_document):
    payload=json.dumps(str(print_document),ensure_ascii=False).replace("</","<\\/")
    st.iframe(f'''<!doctype html><html><head><meta charset="utf-8"><style>html,body{{width:40px;height:40px;margin:0;padding:0;overflow:hidden;background:transparent}}body{{display:flex;align-items:center;justify-content:center}}button{{width:34px;height:34px;margin:0;padding:0;display:inline-flex;align-items:center;justify-content:center;border:1px solid rgba(120,120,120,.45);border-radius:7px;background:transparent;color:#f2f2f2;cursor:pointer}}button:hover{{background:rgba(127,127,127,.10)}}svg{{width:18px;height:18px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}}</style></head><body><button id="print-{html.escape(str(key_suffix))}" title="Imprimer cette vue" aria-label="Imprimer cette vue" onclick='const doc = {payload}; const w=window.open("", "_blank"); if(!w){{alert("Le navigateur a bloqué la fenêtre d’impression.");return;}} w.document.open();w.document.write(doc);w.document.close();const launchPrint=()=>{{w.focus();setTimeout(()=>w.print(),120);}};if(w.document.readyState==="complete")launchPrint();else{{w.addEventListener("load",launchPrint,{{once:true}});setTimeout(launchPrint,350);}}'><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 8V3h10v5"/><rect x="6" y="14" width="12" height="7" rx="1"/><path d="M6 17H4a2 2 0 0 1-2-2v-4a3 3 0 0 1 3-3h14a3 3 0 0 1 3 3v4a2 2 0 0 1-2 2h-2"/><path d="M17 11h.01"/></svg></button></body></html>''',width=40,height=40)
