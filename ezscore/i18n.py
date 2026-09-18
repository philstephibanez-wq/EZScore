from __future__ import annotations

"""Mini service i18n EZScore inspiré du contrat OPUS.

Principes :
- langue initiale détectée depuis ``navigator.language`` ;
- catalogues externes JSON ;
- fallback français ;
- override utilisateur conservé dans la session ;
- aucune dépendance métier.

Le service est volontairement générique afin d'être réutilisé par les futures
surfaces EZScore, pas seulement le Répertoire.
"""

from functools import lru_cache
import json
from pathlib import Path
from typing import Any

import streamlit as st


APP_DIR = Path(__file__).resolve().parents[1]
I18N_DIR = APP_DIR / "i18n"
SUPPORTED_LANGUAGES = ("fr", "en")
DEFAULT_LANGUAGE = "fr"
_SESSION_LANGUAGE = "_ezscore_language"
_SESSION_BROWSER_LANGUAGE = "_ezscore_browser_language"


try:
    _BROWSER_LANGUAGE_COMPONENT = st.components.v2.component(
        "ezscore_browser_language_v1",
        html='<span hidden class="ezscore-browser-language"></span>',
        css=".ezscore-browser-language{display:none!important}",
        js=r"""
export default function(component) {
  const lang = String(
    navigator.language ||
    (navigator.languages && navigator.languages[0]) ||
    ""
  );
  component.setStateValue("language", lang);
}
""",
        isolate_styles=True,
    )
except Exception:
    _BROWSER_LANGUAGE_COMPONENT = None


def normalize_language(value: Any) -> str:
    raw = str(value or "").strip().lower().replace("_", "-")
    primary = raw.split("-", 1)[0] if raw else ""
    return primary if primary in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def detect_browser_language() -> str:
    if _SESSION_BROWSER_LANGUAGE in st.session_state:
        return normalize_language(st.session_state[_SESSION_BROWSER_LANGUAGE])

    if _BROWSER_LANGUAGE_COMPONENT is None:
        return DEFAULT_LANGUAGE

    try:
        result = _BROWSER_LANGUAGE_COMPONENT(
            data={},
            default={"language": ""},
            key="ezscore_browser_language_probe",
        )
        raw = ""
        try:
            raw = str(getattr(result, "language", "") or "")
        except Exception:
            pass
        if not raw:
            try:
                raw = str(result.get("language", "") or "")
            except Exception:
                raw = ""
        if raw:
            language = normalize_language(raw)
            st.session_state[_SESSION_BROWSER_LANGUAGE] = language
            return language
    except Exception:
        pass

    return DEFAULT_LANGUAGE


def current_language() -> str:
    if _SESSION_LANGUAGE not in st.session_state:
        st.session_state[_SESSION_LANGUAGE] = detect_browser_language()
    return normalize_language(st.session_state[_SESSION_LANGUAGE])


def set_language(language: str) -> str:
    value = normalize_language(language)
    st.session_state[_SESSION_LANGUAGE] = value
    return value


@lru_cache(maxsize=16)
def _load_catalog(domain: str, language: str) -> dict[str, str]:
    path = I18N_DIR / f"{domain}.{language}.json"
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(payload, dict):
        return {}
    return {
        str(key): str(value)
        for key, value in payload.items()
        if isinstance(key, str)
    }


def t(
    key: str,
    *,
    domain: str = "catalog",
    language: str | None = None,
    **params: Any,
) -> str:
    lang = normalize_language(language or current_language())
    primary = _load_catalog(domain, lang)
    fallback = _load_catalog(domain, DEFAULT_LANGUAGE)

    value = primary.get(key)
    if value is None:
        value = fallback.get(key, key)

    if params:
        try:
            value = value.format(**params)
        except Exception:
            pass
    return value
