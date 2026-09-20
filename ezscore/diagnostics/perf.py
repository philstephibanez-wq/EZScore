"""File-based performance probes for EZScore.

All probe output goes to:
    <project>/data/logs/ezscore_perf.log

The logger is intentionally independent from stdout/stderr so performance
diagnostics do not flood the PowerShell console.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from functools import wraps
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import threading
import time
from typing import Any, Callable

import streamlit as st


APP_DIR = Path(__file__).resolve().parents[2]
LOG_DIR = APP_DIR / "data" / "logs"
PERF_LOG_PATH = LOG_DIR / "ezscore_perf.log"

_LOGGER_NAME = "ezscore.performance"
_logger = logging.getLogger(_LOGGER_NAME)
_lock = threading.RLock()
_installed = False


def _configure_logger() -> logging.Logger:
    global _logger

    with _lock:
        if getattr(_logger, "_ezscore_file_configured", False):
            return _logger

        LOG_DIR.mkdir(parents=True, exist_ok=True)

        handler = RotatingFileHandler(
            PERF_LOG_PATH,
            maxBytes=5_000_000,
            backupCount=5,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter("%(message)s"))

        _logger.handlers.clear()
        _logger.addHandler(handler)
        _logger.setLevel(logging.INFO)
        _logger.propagate = False
        _logger._ezscore_file_configured = True

    return _logger


def _safe_session_context() -> dict[str, Any]:
    try:
        state = st.session_state
    except Exception:
        return {}

    try:
        audio_hash = str(state.get("active_song_hash", "") or "")
    except Exception:
        audio_hash = ""

    hash12 = audio_hash[:12]
    context: dict[str, Any] = {}

    try:
        context["section"] = str(
            state.get("_pending_main_menu")
            or state.get("main_menu")
            or ""
        )
    except Exception:
        pass

    if hash12:
        context["audio_hash"] = hash12

        try:
            context["view"] = str(
                state.get(f"song_view_{hash12}", "")
            )
        except Exception:
            pass

        try:
            context["mode"] = str(
                state.get(f"song_mode_{hash12}", "")
            )
        except Exception:
            pass

    return {
        key: value
        for key, value in context.items()
        if value not in ("", None)
    }


def perf_event(
    event: str,
    *,
    duration_ms: float | None = None,
    **fields: Any,
) -> None:
    """Write one JSONL performance event to the rotating file."""
    logger = _configure_logger()

    payload: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": str(event),
    }
    payload.update(_safe_session_context())

    if duration_ms is not None:
        payload["duration_ms"] = round(float(duration_ms), 3)

    for key, value in fields.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            payload[str(key)] = value
        else:
            try:
                payload[str(key)] = json.loads(
                    json.dumps(value, ensure_ascii=False, default=str)
                )
            except Exception:
                payload[str(key)] = str(value)

    logger.info(
        json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )


@contextmanager
def perf_span(event: str, **fields: Any):
    started = time.perf_counter()
    try:
        yield
    except Exception as exc:
        perf_event(
            event,
            duration_ms=(time.perf_counter() - started) * 1000.0,
            status="error",
            error_type=type(exc).__name__,
            error=str(exc),
            **fields,
        )
        raise
    else:
        perf_event(
            event,
            duration_ms=(time.perf_counter() - started) * 1000.0,
            status="ok",
            **fields,
        )


def _wrap_function(
    module: Any,
    name: str,
    event_name: str | None = None,
) -> None:
    original = getattr(module, name, None)

    if original is None or not callable(original):
        return
    if getattr(original, "_ezscore_perf_wrapped", False):
        return

    label = event_name or f"{module.__name__}.{name}"

    @wraps(original)
    def wrapped(*args, **kwargs):
        started = time.perf_counter()
        try:
            result = original(*args, **kwargs)
        except Exception as exc:
            perf_event(
                label,
                duration_ms=(time.perf_counter() - started) * 1000.0,
                status="error",
                error_type=type(exc).__name__,
                error=str(exc),
            )
            raise

        extra: dict[str, Any] = {}
        try:
            if name == "build_midi_file":
                extra["beats"] = len(kwargs.get("beats", args[0] if args else []) or [])
                extra["bytes"] = len(result or b"")
            elif name == "build_chord_midi_events":
                extra["beats"] = len(kwargs.get("beats", args[0] if args else []) or [])
                extra["events"] = len(result or [])
            elif name == "waveform_preview_cache":
                extra["waveform_points"] = len((result or {}).get("times", []))
            elif name == "create_harmonic_timeline":
                extra["plotly_traces"] = len(getattr(result, "data", []) or [])
            elif isinstance(result, (list, tuple, dict, set)):
                extra["result_len"] = len(result)
        except Exception:
            pass

        perf_event(
            label,
            duration_ms=(time.perf_counter() - started) * 1000.0,
            status="ok",
            **extra,
        )
        return result

    wrapped._ezscore_perf_wrapped = True
    setattr(module, name, wrapped)


def _wrap_streamlit_call(
    obj: Any,
    name: str,
    event_name: str,
) -> None:
    original = getattr(obj, name, None)

    if original is None or not callable(original):
        return
    if getattr(original, "_ezscore_perf_wrapped", False):
        return

    @wraps(original)
    def wrapped(*args, **kwargs):
        started = time.perf_counter()
        try:
            result = original(*args, **kwargs)
        except Exception as exc:
            perf_event(
                event_name,
                duration_ms=(time.perf_counter() - started) * 1000.0,
                status="error",
                error_type=type(exc).__name__,
                error=str(exc),
            )
            raise

        extra = {}
        try:
            if name == "plotly_chart" and args:
                extra["plotly_traces"] = len(
                    getattr(args[0], "data", []) or []
                )
            elif name == "dataframe" and args:
                frame = args[0]
                extra["rows"] = int(len(frame))
        except Exception:
            pass

        perf_event(
            event_name,
            duration_ms=(time.perf_counter() - started) * 1000.0,
            status="ok",
            **extra,
        )
        return result

    wrapped._ezscore_perf_wrapped = True
    setattr(obj, name, wrapped)


def _install_rerun_probe() -> None:
    original = getattr(st, "set_page_config", None)
    if original is None or getattr(original, "_ezscore_perf_wrapped", False):
        return

    @wraps(original)
    def wrapped(*args, **kwargs):
        perf_event("rerun.start")
        return original(*args, **kwargs)

    wrapped._ezscore_perf_wrapped = True
    st.set_page_config = wrapped


def install_runtime_probes() -> None:
    """Install low-overhead probes before EZScore imports function aliases."""
    global _installed

    if _installed:
        return

    _configure_logger()
    _install_rerun_probe()

    # Streamlit render probes. We intentionally avoid markdown/write/text
    # because those are too frequent and would create noisy logs.
    _wrap_streamlit_call(st, "plotly_chart", "ui.plotly_chart")
    _wrap_streamlit_call(st, "dataframe", "ui.dataframe")
    # download_button is deliberately left unwrapped: Streamlit owns
    # the browser download lifecycle and callback semantics.
    _wrap_streamlit_call(st, "image", "ui.image")

    # Domain probes. Importing these modules here is deliberate: EZScore.py
    # imports their functions only after app_shell has loaded.
    try:
        import ezscore.timeline as timeline
        _wrap_function(
            timeline,
            "waveform_preview_cache",
            "timeline.waveform_preview_cache",
        )
        _wrap_function(
            timeline,
            "create_harmonic_timeline",
            "timeline.create_harmonic_timeline",
        )
        _wrap_function(
            timeline,
            "chord_regions",
            "timeline.chord_regions",
        )
    except Exception as exc:
        perf_event(
            "probe.install.timeline",
            status="error",
            error=str(exc),
        )

    try:
        import ezscore.transcription as transcription
        for name in (
            "construire_timeline_phonetique",
            "construire_groupes_phonetiques",
            "detecter_sections_structurelles",
            "extraire_mots",
        ):
            _wrap_function(
                transcription,
                name,
                f"transcription.{name}",
            )
    except Exception as exc:
        perf_event(
            "probe.install.transcription",
            status="error",
            error=str(exc),
        )

    try:
        import ezscore.midi as midi
        _wrap_function(
            midi,
            "build_midi_file",
            "midi.build_midi_file",
        )
        _wrap_function(
            midi,
            "build_chord_midi_events",
            "midi.build_chord_midi_events",
        )
    except Exception as exc:
        perf_event(
            "probe.install.midi",
            status="error",
            error=str(exc),
        )

    try:
        import ezscore.persistence as persistence
        for name in (
            "load_latest_persisted_analysis",
            "load_persisted_analysis",
            "load_structure_blocks",
            "materialiser_structure_blocks",
            "effective_lyrics_words_for_sections",
            "load_measure_edits",
            "load_lyric_block_edits",
            "list_song_catalog",
        ):
            _wrap_function(
                persistence,
                name,
                f"persistence.{name}",
            )
    except Exception as exc:
        perf_event(
            "probe.install.persistence",
            status="error",
            error=str(exc),
        )

    _installed = True
    perf_event(
        "probe.install.complete",
        log_file=str(PERF_LOG_PATH),
    )


def read_perf_log(max_bytes: int = 1_500_000) -> bytes:
    """Read the tail of the current performance log for UI download."""
    try:
        data = PERF_LOG_PATH.read_bytes()
    except FileNotFoundError:
        return b""

    if len(data) > max_bytes:
        return data[-max_bytes:]
    return data


def clear_perf_log() -> None:
    """Truncate the current log without touching rotated history files."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    PERF_LOG_PATH.write_text("", encoding="utf-8")
    perf_event("log.cleared")


def render_perf_log_sidebar() -> None:
    """Admin-only file diagnostics control in the sidebar."""
    try:
        from ezscore.auth import allowed
        if not allowed("admin.users"):
            return
    except Exception:
        return

    with st.sidebar.expander(
        "🧪 Diagnostic performances",
        expanded=False,
    ):
        st.caption(str(PERF_LOG_PATH))

        payload = read_perf_log()
        st.download_button(
            "⬇ Télécharger le log",
            data=payload,
            file_name="ezscore_perf.log",
            mime="application/x-ndjson",
            key="perf_log_download",
            disabled=not bool(payload),
            on_click="ignore",
            width="stretch",
        )

        if st.button(
            "🧹 Vider le log",
            key="perf_log_clear",
            width="stretch",
        ):
            clear_perf_log()
            st.success("Log vidé.")
