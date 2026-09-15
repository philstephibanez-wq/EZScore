"""HTTP media registration for EZScore browser players.

Contract:
- media bytes are NOT transported through Bidi/component payloads;
- Streamlit's media endpoint serves the file over HTTP;
- no silent recovery path;
- registration failures are raised and shown as real errors.

Streamlit itself uses the same MediaFileManager for st.audio/st.video.
"""

from __future__ import annotations

import mimetypes
from pathlib import Path

from streamlit import runtime


def register_media_url(
    path: Path,
    *,
    coordinates: str,
    mimetype: str | None = None,
) -> str:
    media_path = Path(path)
    if not media_path.is_file():
        raise FileNotFoundError(f"Fichier média introuvable : {media_path}")
    if media_path.stat().st_size <= 0:
        raise RuntimeError(f"Fichier média vide : {media_path}")

    if not runtime.exists():
        raise RuntimeError(
            "Runtime Streamlit indisponible : impossible d'enregistrer le média HTTP."
        )

    mime = str(mimetype or "").strip()
    if not mime:
        mime = mimetypes.guess_type(str(media_path))[0] or "application/octet-stream"

    url = runtime.get_instance().media_file_mgr.add(
        str(media_path),
        mime,
        str(coordinates),
    )
    if not url:
        raise RuntimeError(
            f"Streamlit n'a pas fourni d'URL média pour {media_path.name}."
        )
    return str(url)
