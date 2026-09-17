"""Editorial lyrics + word-boundary anchors for EZScore Analyse > Paroles.

This module patches only the "Texte transcrit" textarea rendered by
stem_lab_analysis. It does not modify Whisper, timestamps, STEMs, player audio,
rhythm/harmony analysis, measures or MIDI.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import streamlit as st


_SCHEMA_VERSION = 1
_PATCH_INSTALLED = False


_ANCHOR_HTML = """
<div class="ez-anchor-picker">
  <div class="ez-anchor-help">
    Cliquez exactement entre deux mots pour choisir la position de l’ancre.
  </div>
  <div class="ez-anchor-words"></div>
</div>
"""

_ANCHOR_CSS = r"""
.ez-anchor-picker {
  padding:.65rem .75rem .85rem;
  border:1px solid color-mix(in srgb, var(--st-text-color) 18%, transparent);
  border-radius:9px;
  background:color-mix(in srgb, var(--st-text-color) 3%, transparent);
  font-family:var(--st-font);
  color:var(--st-text-color);
}
.ez-anchor-help {
  font-size:.82rem;
  opacity:.72;
  margin-bottom:.55rem;
}
.ez-anchor-words {
  display:flex;
  align-items:baseline;
  flex-wrap:wrap;
  row-gap:.55rem;
  line-height:1.55;
}
.ez-anchor-word {
  display:inline-block;
  font-size:18px;
  font-weight:560;
  padding:0 .08rem;
}
.ez-anchor-gap {
  position:relative;
  display:inline-flex;
  width:14px;
  height:28px;
  padding:0;
  margin:0 1px;
  border:0;
  border-radius:4px;
  background:transparent;
  cursor:pointer;
  align-items:center;
  justify-content:center;
  vertical-align:middle;
}
.ez-anchor-gap::before {
  content:"";
  display:block;
  width:2px;
  height:16px;
  border-radius:2px;
  background:color-mix(in srgb, var(--st-text-color) 18%, transparent);
  transition:height .08s linear, background .08s linear;
}
.ez-anchor-gap:hover::before,
.ez-anchor-gap.selected::before {
  height:25px;
  background:#4da3ff;
}
.ez-anchor-gap.anchored::before {
  height:25px;
  width:3px;
  background:#4da3ff;
}
.ez-anchor-gap .ez-anchor-label {
  position:absolute;
  left:50%;
  bottom:28px;
  transform:translateX(-50%);
  white-space:nowrap;
  padding:2px 6px;
  border-radius:5px;
  background:#1f6fb2;
  color:#fff;
  font-size:10px;
  font-weight:800;
  z-index:4;
  pointer-events:none;
}
"""

_ANCHOR_JS = r"""
export default function(component) {
  const { parentElement, data, setStateValue } = component;
  const host = parentElement.querySelector(".ez-anchor-words");
  const words = Array.isArray(data?.words) ? data.words : [];
  const anchors = Array.isArray(data?.anchors) ? data.anchors : [];
  const selected = Number(component.state?.boundary ?? data?.selected_boundary ?? -1);

  host.innerHTML = "";

  const byBoundary = new Map();
  anchors.forEach(anchor => {
    const boundary = Number(anchor.boundary_index);
    if (Number.isInteger(boundary)) {
      byBoundary.set(boundary, String(anchor.label || ""));
    }
  });

  words.forEach((word, index) => {
    if (index > 0) {
      const gap = document.createElement("button");
      gap.type = "button";
      gap.className = "ez-anchor-gap";
      gap.title = "Placer une ancre ici";
      gap.dataset.boundary = String(index);

      if (index === selected) gap.classList.add("selected");

      const label = byBoundary.get(index);
      if (label !== undefined) {
        gap.classList.add("anchored");
        const badge = document.createElement("span");
        badge.className = "ez-anchor-label";
        badge.textContent = label || "Ancre";
        gap.appendChild(badge);
      }

      gap.onclick = () => {
        setStateValue("boundary", index);
      };
      host.appendChild(gap);
    }

    const token = document.createElement("span");
    token.className = "ez-anchor-word";
    token.textContent = String(word.text || "");
    host.appendChild(token);
  });
}
"""

_ANCHOR_COMPONENT = st.components.v2.component(
    "ezscore_lyrics_anchor_picker_r2",
    html=_ANCHOR_HTML,
    css=_ANCHOR_CSS,
    js=_ANCHOR_JS,
    isolate_styles=True,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _editorial_path(stem_module, audio_hash: str) -> Path:
    return stem_module._work_dir(audio_hash) / "lyrics_editorial.json"


def _normalized_source_words(words: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for index, word in enumerate(words or []):
        text = str(word.get("text", "") or "").strip()
        if not text:
            raise RuntimeError(
                f"Timeline Whisper invalide : mot vide à l’index {index}."
            )
        start = float(word.get("start", 0.0) or 0.0)
        end = float(word.get("end", start) or start)
        if end < start:
            raise RuntimeError(
                f"Timeline Whisper invalide : fin < début pour le mot {index}."
            )
        normalized.append(
            {
                "word_index": index,
                "text": text,
                "start": start,
                "end": end,
            }
        )
    return normalized


def _source_fingerprint(words: list[dict[str, Any]]) -> str:
    raw = json.dumps(
        [
            [
                int(word["word_index"]),
                str(word["text"]),
                round(float(word["start"]), 6),
                round(float(word["end"]), 6),
            ]
            for word in words
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _validate_anchor(
    anchor: dict[str, Any],
    *,
    words: list[dict[str, Any]],
) -> dict[str, Any]:
    if len(words) < 2:
        raise RuntimeError(
            "Impossible de placer une ancre : moins de deux mots horodatés."
        )

    anchor_id = str(anchor.get("anchor_id", "") or "").strip()
    label = str(anchor.get("label", "") or "").strip()

    if not anchor_id:
        raise RuntimeError("Ancre invalide : identifiant absent.")
    if not label:
        raise RuntimeError("Ancre invalide : nom vide.")

    try:
        boundary = int(anchor.get("boundary_index"))
    except (TypeError, ValueError) as exc:
        raise RuntimeError("Ancre invalide : position non entière.") from exc

    if boundary < 1 or boundary >= len(words):
        raise RuntimeError(
            f"Ancre invalide : frontière {boundary} hors plage "
            f"1–{len(words) - 1}."
        )

    left = words[boundary - 1]
    right = words[boundary]
    anchor_time = (
        float(left["end"]) + float(right["start"])
    ) / 2.0

    return {
        "anchor_id": anchor_id,
        "label": label,
        "boundary_index": boundary,
        "time": anchor_time,
        "left_word_index": int(left["word_index"]),
        "right_word_index": int(right["word_index"]),
        "left_word": str(left["text"]),
        "right_word": str(right["text"]),
    }


def _validate_anchors(
    anchors: list[dict[str, Any]],
    *,
    words: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    validated = [
        _validate_anchor(anchor, words=words)
        for anchor in list(anchors or [])
    ]

    boundaries = [int(anchor["boundary_index"]) for anchor in validated]
    if len(boundaries) != len(set(boundaries)):
        raise RuntimeError(
            "Deux ancres occupent la même frontière entre mots."
        )

    ids = [str(anchor["anchor_id"]) for anchor in validated]
    if len(ids) != len(set(ids)):
        raise RuntimeError("Deux ancres possèdent le même identifiant.")

    validated.sort(key=lambda anchor: int(anchor["boundary_index"]))
    return validated


def _read_editorial(
    stem_module,
    audio_hash: str,
    words: list[dict[str, Any]],
    whisper_text: str,
) -> dict[str, Any]:
    path = _editorial_path(stem_module, audio_hash)
    fingerprint = _source_fingerprint(words)

    if not path.is_file():
        return {
            "schema_version": _SCHEMA_VERSION,
            "source_fingerprint": fingerprint,
            "corrected_text": str(whisper_text or ""),
            "anchors": [],
            "updated_at": "",
        }

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(
            f"Impossible de lire {path.name}: {exc}"
        ) from exc

    if int(payload.get("schema_version", 0) or 0) != _SCHEMA_VERSION:
        raise RuntimeError(
            "Version de données éditoriales Paroles inconnue. "
            "Aucune conversion silencieuse n’est appliquée."
        )

    stored_fingerprint = str(
        payload.get("source_fingerprint", "") or ""
    ).strip()
    if stored_fingerprint != fingerprint:
        raise RuntimeError(
            "La transcription Whisper source a changé depuis la sauvegarde "
            "des paroles/ancres. Aucune ancre n’est remappée automatiquement."
        )

    corrected_text = payload.get("corrected_text")
    if not isinstance(corrected_text, str):
        raise RuntimeError(
            "Données éditoriales invalides : corrected_text n’est pas une chaîne."
        )

    anchors_raw = payload.get("anchors", [])
    if not isinstance(anchors_raw, list):
        raise RuntimeError(
            "Données éditoriales invalides : anchors n’est pas une liste."
        )

    return {
        "schema_version": _SCHEMA_VERSION,
        "source_fingerprint": fingerprint,
        "corrected_text": corrected_text,
        "anchors": _validate_anchors(anchors_raw, words=words),
        "updated_at": str(payload.get("updated_at", "") or ""),
    }


def _write_editorial(
    stem_module,
    audio_hash: str,
    *,
    words: list[dict[str, Any]],
    corrected_text: str,
    anchors: list[dict[str, Any]],
) -> None:
    path = _editorial_path(stem_module, audio_hash)
    path.parent.mkdir(parents=True, exist_ok=True)

    validated_anchors = _validate_anchors(
        anchors,
        words=words,
    )

    payload = {
        "schema_version": _SCHEMA_VERSION,
        "source_fingerprint": _source_fingerprint(words),
        "corrected_text": str(corrected_text),
        "anchors": validated_anchors,
        "updated_at": _utc_now_iso(),
    }

    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(path)


def _boundary_context(
    words: list[dict[str, Any]],
    boundary: int,
) -> str:
    if boundary < 1 or boundary >= len(words):
        return "position invalide"

    left0 = max(0, boundary - 4)
    right1 = min(len(words), boundary + 4)
    left = " ".join(
        str(word["text"]) for word in words[left0:boundary]
    )
    right = " ".join(
        str(word["text"]) for word in words[boundary:right1]
    )
    return f"{left}  │  {right}"


def _render_anchor_editor(
    *,
    stem_module,
    audio_hash: str,
    words: list[dict[str, Any]],
    editorial: dict[str, Any],
    corrected_text: str,
) -> None:
    st.markdown("### ⚑ Ancres")
    st.caption(
        "Une ancre est attachée à une frontière entre deux mots Whisper. "
        "Aucune mesure et aucun timestamp ne sont modifiés."
    )

    draft_key = f"_ez_lyrics_anchor_draft_{audio_hash[:12]}"
    saved_anchors = [dict(anchor) for anchor in editorial["anchors"]]

    if draft_key not in st.session_state:
        st.session_state[draft_key] = [
            dict(anchor) for anchor in saved_anchors
        ]

    draft = [
        dict(anchor)
        for anchor in st.session_state.get(draft_key, [])
    ]
    draft = _validate_anchors(draft, words=words)

    picker = _ANCHOR_COMPONENT(
        data={
            "words": [
                {
                    "text": word["text"],
                    "word_index": word["word_index"],
                }
                for word in words
            ],
            "anchors": draft,
            "selected_boundary": -1,
        },
        default={"boundary": -1},
        key=f"ez_anchor_picker_{audio_hash[:12]}",
        on_boundary_change=lambda: None,
    )

    selected_boundary = int(
        getattr(picker, "boundary", -1) or -1
    )

    if 1 <= selected_boundary < len(words):
        st.info(
            "Position sélectionnée : "
            + _boundary_context(words, selected_boundary)
        )
        c_label, c_add = st.columns([3.0, 1.15])
        with c_label:
            new_label = st.text_input(
                "Nom de la nouvelle ancre",
                placeholder="Couplet 1, Refrain, Pont…",
                key=f"ez_anchor_label_{audio_hash[:12]}",
            )
        with c_add:
            st.write("")
            st.write("")
            if st.button(
                "＋ Ajouter",
                key=f"ez_anchor_add_{audio_hash[:12]}",
                width="stretch",
            ):
                label = str(new_label or "").strip()
                if not label:
                    st.error("Le nom de l’ancre est obligatoire.")
                elif any(
                    int(anchor["boundary_index"]) == selected_boundary
                    for anchor in draft
                ):
                    st.error(
                        "Une ancre existe déjà à cette frontière."
                    )
                else:
                    draft.append(
                        _validate_anchor(
                            {
                                "anchor_id": uuid.uuid4().hex,
                                "label": label,
                                "boundary_index": selected_boundary,
                            },
                            words=words,
                        )
                    )
                    draft = _validate_anchors(
                        draft,
                        words=words,
                    )
                    st.session_state[draft_key] = draft
                    st.session_state.pop(
                        f"ez_anchor_label_{audio_hash[:12]}",
                        None,
                    )
                    st.rerun()

    if draft:
        st.markdown("#### Ancres en cours")
        for index, anchor in enumerate(draft):
            anchor_id = str(anchor["anchor_id"])
            c_name, c_context, c_delete = st.columns(
                [1.35, 3.7, .8]
            )
            with c_name:
                edited_label = st.text_input(
                    "Nom",
                    value=str(anchor["label"]),
                    key=(
                        f"ez_anchor_edit_label_"
                        f"{audio_hash[:10]}_{anchor_id}"
                    ),
                    label_visibility="collapsed",
                )
                draft[index]["label"] = str(
                    edited_label or ""
                ).strip()
            with c_context:
                st.caption(
                    _boundary_context(
                        words,
                        int(anchor["boundary_index"]),
                    )
                )
            with c_delete:
                if st.button(
                    "🗑",
                    key=(
                        f"ez_anchor_delete_"
                        f"{audio_hash[:10]}_{anchor_id}"
                    ),
                    help="Supprimer cette ancre du brouillon.",
                ):
                    st.session_state[draft_key] = [
                        item
                        for item in draft
                        if str(item["anchor_id"]) != anchor_id
                    ]
                    st.rerun()

        # Keep text-input edits in the current in-memory draft.
        draft = _validate_anchors(draft, words=words)
        st.session_state[draft_key] = draft

    anchors_dirty = [
        (
            str(anchor["anchor_id"]),
            str(anchor["label"]),
            int(anchor["boundary_index"]),
        )
        for anchor in draft
    ] != [
        (
            str(anchor["anchor_id"]),
            str(anchor["label"]),
            int(anchor["boundary_index"]),
        )
        for anchor in saved_anchors
    ]

    if anchors_dirty:
        st.warning("● Ancres modifiées non enregistrées.")
    else:
        st.caption("✓ Ancres enregistrées.")

    save_col, cancel_col = st.columns([1.2, 1.0])
    with save_col:
        if st.button(
            "💾 Enregistrer les ancres",
            type="primary",
            key=f"ez_anchor_save_{audio_hash[:12]}",
            width="stretch",
        ):
            _write_editorial(
                stem_module,
                audio_hash,
                words=words,
                corrected_text=corrected_text,
                anchors=draft,
            )
            st.session_state[draft_key] = [
                dict(anchor) for anchor in draft
            ]
            st.success("Ancres enregistrées.")
            st.rerun()

    with cancel_col:
        if st.button(
            "↩ Annuler",
            key=f"ez_anchor_cancel_{audio_hash[:12]}",
            width="stretch",
            disabled=not anchors_dirty,
        ):
            st.session_state[draft_key] = [
                dict(anchor) for anchor in saved_anchors
            ]
            st.rerun()


def _render_lyrics_editor_after_textarea(
    *,
    stem_module,
    audio_hash: str,
    original_textarea: Callable[..., Any],
    label: str,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> str:
    speech = stem_module._load_speech(audio_hash)
    if speech is None:
        raise RuntimeError(
            "Éditeur Paroles appelé sans transcription Whisper."
        )

    words = _normalized_source_words(
        list(speech.get("words", []) or [])
    )
    if not words:
        raise RuntimeError(
            "Transcription Whisper sans mots horodatés : édition impossible."
        )

    editorial = _read_editorial(
        stem_module,
        audio_hash,
        words,
        str(speech.get("text", "") or ""),
    )

    widget_key = f"ezstem_lyrics_editor_{audio_hash[:12]}"
    persisted_text = str(editorial["corrected_text"])

    # Dedicated widget key: an old unsaved experimental textarea value cannot
    # silently override the persisted editorial state.
    if widget_key not in st.session_state:
        st.session_state[widget_key] = persisted_text

    st.markdown(
        f"""
        <style>
        .st-key-{widget_key} textarea {{
            font-size:20px !important;
            line-height:1.48 !important;
            font-family:var(--st-font) !important;
            min-height:360px !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    textarea_kwargs = dict(kwargs)
    textarea_kwargs.pop("value", None)
    textarea_kwargs["key"] = widget_key
    textarea_kwargs["height"] = max(
        360,
        int(textarea_kwargs.get("height", 320) or 320),
    )

    current_text = original_textarea(
        label,
        *args,
        **textarea_kwargs,
    )

    lyrics_dirty = str(current_text) != persisted_text

    status_col, action_col, reset_col = st.columns(
        [2.1, 1.0, 1.35]
    )
    with status_col:
        if lyrics_dirty:
            st.warning("● Modifications non enregistrées.")
        else:
            st.success("✓ Enregistré.")

    with action_col:
        if st.button(
            "💾 Enregistrer",
            type="primary",
            key=f"ez_lyrics_save_{audio_hash[:12]}",
            width="stretch",
        ):
            _write_editorial(
                stem_module,
                audio_hash,
                words=words,
                corrected_text=str(current_text),
                anchors=editorial["anchors"],
            )
            st.success("Paroles enregistrées.")
            st.rerun()

    with reset_col:
        if st.button(
            "↩ Texte Whisper",
            key=f"ez_lyrics_reset_{audio_hash[:12]}",
            width="stretch",
            help=(
                "Recharge le texte Whisper dans l’éditeur. "
                "Il ne sera persistant qu’après Enregistrer."
            ),
        ):
            st.session_state[widget_key] = str(
                speech.get("text", "") or ""
            )
            st.rerun()

    _render_anchor_editor(
        stem_module=stem_module,
        audio_hash=audio_hash,
        words=words,
        editorial=editorial,
        corrected_text=str(current_text),
    )

    return str(current_text)


def install(stem_module) -> None:
    """Install the Paroles editor around the existing EZScore analysis screen."""
    global _PATCH_INSTALLED

    if _PATCH_INSTALLED:
        return

    original_render = stem_module.render_stem_lab_fresh_analysis

    def render_with_lyrics_editor(audio_hash: str) -> None:
        original_textarea = st.text_area

        def patched_text_area(label, *args, **kwargs):
            if str(label) != "Texte transcrit":
                return original_textarea(label, *args, **kwargs)

            return _render_lyrics_editor_after_textarea(
                stem_module=stem_module,
                audio_hash=audio_hash,
                original_textarea=original_textarea,
                label=label,
                args=args,
                kwargs=kwargs,
            )

        st.text_area = patched_text_area
        try:
            original_render(audio_hash)
        finally:
            st.text_area = original_textarea

    stem_module.render_stem_lab_fresh_analysis = render_with_lyrics_editor
    _PATCH_INSTALLED = True
