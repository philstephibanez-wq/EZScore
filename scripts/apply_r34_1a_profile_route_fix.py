#!/usr/bin/env python3
from __future__ import annotations
from datetime import datetime
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
BACKUP = ROOT / "var" / "backup" / ("r34-1a-profile-route-" + datetime.now().strftime("%Y%m%d-%H%M%S"))

def backup(path: Path) -> None:
    if not path.exists():
        return
    dst = BACKUP / path.relative_to(ROOT)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dst)

def save(path: Path, text: str, label: str) -> None:
    old = path.read_text(encoding="utf-8")
    if old == text:
        print(f"[OK] {label}: already applied")
        return
    backup(path)
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"[OK] {label}")

def main() -> None:
    path = ROOT / "src" / "Controller" / "SongLabController.php"
    text = path.read_text(encoding="utf-8")

    old = """    #[Route('/chords/profile/{profile}', name: 'app_song_chordslab_profile_data', requirements: ['profile' => 'beginner|intermediate|expert'], methods: ['GET'])]"""
    new = """    #[Route('/chords/profile/{profile}', name: 'app_song_chordslab_profile_data', methods: ['GET'])]"""

    if old in text:
        text = text.replace(old, new, 1)
    elif new in text:
        print("[OK] route requirement already removed")
    else:
        raise RuntimeError("R34.1 profile data route anchor not found")

    # Keep explicit runtime validation now that the router accepts the placeholder used by Twig.
    needle = """        $this->requireEditor($song);

        $events = array_map("""
    replacement = """        $this->requireEditor($song);

        if (!in_array($profile, ['beginner', 'intermediate', 'expert'], true)) {
            return $this->json(['error' => 'invalid_profile'], Response::HTTP_UNPROCESSABLE_ENTITY);
        }

        $events = array_map("""
    if replacement not in text:
        if needle not in text:
            raise RuntimeError("profile endpoint validation anchor not found")
        text = text.replace(needle, replacement, 1)

    save(path, text, "profile route placeholder fix")
    print(f"[OK] Backup: {BACKUP}")
    print("[OK] R34.1a applied.")

if __name__ == "__main__":
    main()
