from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STEMS = ROOT / "data" / "analysis" / "stems"
LAB = ROOT / "data" / "analysis" / "stem_lab"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def files(root: Path):
    if not root.exists():
        return []
    return [p for p in root.rglob("*") if p.is_file() and p.stat().st_size > 0]


def main() -> None:
    stem_files = files(STEMS)
    lab_files = files(LAB)
    by_hash = {}

    for path in stem_files + lab_files:
        if path.suffix.lower() not in {
            ".wav", ".mp3", ".flac", ".m4a", ".ogg", ".opus", ".mid", ".json"
        }:
            continue
        by_hash.setdefault(digest(path), []).append(path)

    duplicates = [
        paths for paths in by_hash.values()
        if any(STEMS in p.parents for p in paths)
        and any(LAB in p.parents for p in paths)
    ]

    print(f"stems files   : {len(stem_files)}")
    print(f"stem_lab files: {len(lab_files)}")
    print(f"cross-tree duplicate groups: {len(duplicates)}")
    print()

    for paths in sorted(
        duplicates,
        key=lambda group: max(p.stat().st_size for p in group),
        reverse=True,
    ):
        size = max(p.stat().st_size for p in paths)
        print(f"{size / (1024*1024):8.2f} MiB")
        for path in paths:
            print("   ", path.relative_to(ROOT))
        print()

    print("Aucune suppression n'a ete effectuee.")


if __name__ == "__main__":
    main()
