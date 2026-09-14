"""EZScore diagnostic helpers."""

from .perf import (
    LOG_DIR,
    PERF_LOG_PATH,
    clear_perf_log,
    install_runtime_probes,
    perf_event,
    perf_span,
    read_perf_log,
    render_perf_log_sidebar,
)

__all__ = [
    "LOG_DIR",
    "PERF_LOG_PATH",
    "clear_perf_log",
    "install_runtime_probes",
    "perf_event",
    "perf_span",
    "read_perf_log",
    "render_perf_log_sidebar",
]
