from __future__ import annotations

import warnings


def main() -> int:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")

        import authlib
        import httpx2
        from authlib.integrations.httpx_client import AsyncOAuth2Client

        assert AsyncOAuth2Client is not None

    deprecated = [
        item
        for item in caught
        if item.category.__name__ == "AuthlibDeprecationWarning"
    ]

    if deprecated:
        details = "\n".join(
            f"{item.filename}:{item.lineno}: {item.message}"
            for item in deprecated
        )
        raise RuntimeError(
            "AuthlibDeprecationWarning detected:\n" + details
        )

    print("AUTHLIB HTTPX2 OK")
    print("Authlib:", authlib.__version__)
    print("httpx2:", getattr(httpx2, "__version__", "installed"))
    print("AuthlibDeprecationWarning: NONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
