#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else r"H:\EZScore_v1").resolve()

SONG = ROOT / "src/Domain/Song/Song.php"
SERVICE = ROOT / "src/Service/LyricsSourceHistoryService.php"
CTRL = ROOT / "src/Controller/LyricsHistoryController.php"
MIGRATION = ROOT / "migrations/Version20260929080000.php"

def sub_literal(pattern: str, replacement: str, text: str, count: int = 1) -> tuple[str, int]:
    return re.subn(pattern, lambda _m: replacement, text, count=count, flags=re.S)

def main() -> int:
    for p in (SONG, SERVICE, CTRL, MIGRATION):
        if not p.is_file():
            raise RuntimeError(f"Missing prerequisite: {p}")

    song = SONG.read_text(encoding="utf-8")
    service = SERVICE.read_text(encoding="utf-8")
    ctrl = CTRL.read_text(encoding="utf-8")

    # Song current revision field.
    if "private ?int $lyricsCurrentRevisionId" not in song:
        anchor = "    #[ORM\\Column(length: 500, nullable: true)]\n    private ?string $coverPath = null;\n"
        insert = """    #[ORM\\Column(name: 'lyrics_current_revision_id', nullable: true)]
    private ?int $lyricsCurrentRevisionId = null;

"""
        if anchor not in song:
            raise RuntimeError("Song property anchor not found")
        song = song.replace(anchor, insert + anchor, 1)

    if "getLyricsCurrentRevisionId()" not in song:
        anchor = "    public function getComment(): ?string { return $this->comment; }\n"
        insert = """    public function getLyricsCurrentRevisionId(): ?int { return $this->lyricsCurrentRevisionId; }
    public function setLyricsCurrentRevisionId(?int $revisionId): self
    {
        $this->lyricsCurrentRevisionId = $revisionId;
        return $this->touch();
    }

"""
        if anchor not in song:
            raise RuntimeError("Song accessor anchor not found")
        song = song.replace(anchor, insert + anchor, 1)

    # saveVersion: saved revision becomes exact current revision.
    if "$song->setLyricsCurrentRevisionId($latest->getId());" not in service:
        old = """            $latest->updateMetadata($sourceType, $comment, $user);
            $song->setLyricsSourceText($content);
            $this->em->flush();
            return $latest;
"""
        new = """            $latest->updateMetadata($sourceType, $comment, $user);
            $song->setLyricsSourceText($content);
            $song->setLyricsCurrentRevisionId($latest->getId());
            $this->em->flush();
            return $latest;
"""
        if old not in service:
            raise RuntimeError("saveVersion latest anchor not found")
        service = service.replace(old, new, 1)

    if "$song->setLyricsCurrentRevisionId($revision->getId());" not in service:
        old = """        $revision = new LyricsSourceRevision($song, $content, $sourceType, $comment, $user);
        $this->em->persist($revision);
        $song->setLyricsSourceText($content);
        $this->em->flush();

        return $revision;
"""
        new = """        $revision = new LyricsSourceRevision($song, $content, $sourceType, $comment, $user);
        $this->em->persist($revision);
        $song->setLyricsSourceText($content);
        $this->em->flush();

        $song->setLyricsCurrentRevisionId($revision->getId());
        $this->em->flush();

        return $revision;
"""
        if old not in service:
            raise RuntimeError("saveVersion revision anchor not found")
        service = service.replace(old, new, 1)

    # Restore = select clicked revision only, never create a duplicate revision.
    restore_pattern = r"""    public function restore\(Song \$song, LyricsSourceRevision \$target, User \$user\): LyricsSourceRevision
    \{
.*?
    \}

    public function delete"""
    restore_replacement = """    public function restore(Song $song, LyricsSourceRevision $target, User $user): LyricsSourceRevision
    {
        if ($target->getSong()->getId() !== $song->getId()) {
            throw new \\InvalidArgumentException('Revision does not belong to this song.');
        }

        $song->setLyricsSourceText($target->getContent());
        $song->setLyricsCurrentRevisionId($target->getId());
        $this->em->flush();

        return $target;
    }

    public function delete"""
    service, n = sub_literal(restore_pattern, restore_replacement, service, 1)
    if n != 1:
        raise RuntimeError("restore() block not found")

    # Delete protection: exact current revision ID only.
    if "$song->getLyricsCurrentRevisionId() === $revision->getId()" not in service:
        pattern_k = r"""        \$currentRevision = \$this->revisions->findCurrentForSong\(\$song\);
        if \(
            \$currentRevision instanceof LyricsSourceRevision
            && \$currentRevision->getId\(\) === \$revision->getId\(\)
        \) \{
            throw new \\LogicException\('current_revision'\);
        \}
"""
        repl = """        if ($song->getLyricsCurrentRevisionId() === $revision->getId()) {
            throw new \\LogicException('current_revision');
        }
"""
        service, n = sub_literal(pattern_k, repl, service, 1)

        if n == 0:
            pattern_old = r"""        if \(\$revision->getContent\(\) === \$this->normaliseContent\(\(string\) \$song->getLyricsSourceText\(\)\)\) \{
            throw new \\LogicException\('current_revision'\);
        \}
"""
            service, n = sub_literal(pattern_old, repl, service, 1)

        if n != 1:
            raise RuntimeError("delete current-revision protection not found")

    # Controller list: exact stored revision ID.
    if "$currentRevisionId = $song->getLyricsCurrentRevisionId();" not in ctrl:
        old_k = """        $currentRevision = $revisions->findCurrentForSong($song);
        $currentRevisionId = $currentRevision?->getId();
"""
        old_pre = """        $current = str_replace(["\\r\\n", "\\r"], "\\n", (string) $song->getLyricsSourceText());
"""
        new = """        $currentRevisionId = $song->getLyricsCurrentRevisionId();
"""
        if old_k in ctrl:
            ctrl = ctrl.replace(old_k, new, 1)
        elif old_pre in ctrl:
            ctrl = ctrl.replace(old_pre, new, 1)
            ctrl = ctrl.replace(
                "fn (LyricsSourceRevision $revision): array => $this->serialise($revision, $current),",
                "fn (LyricsSourceRevision $revision): array => $this->serialise($revision, $currentRevisionId),",
                1,
            )
        else:
            raise RuntimeError("controller current revision anchor not found")

    ctrl = ctrl.replace(
        "private function serialise(LyricsSourceRevision $revision, string $current): array",
        "private function serialise(LyricsSourceRevision $revision, ?int $currentRevisionId): array",
        1,
    )
    ctrl = ctrl.replace(
        "'is_current' => $revision->getContent() === $current,",
        "'is_current' => $currentRevisionId !== null && $revision->getId() === $currentRevisionId,",
        1,
    )

    if "'is_current' => $currentRevisionId !== null && $revision->getId() === $currentRevisionId" not in ctrl:
        raise RuntimeError("controller is_current anchor not patched")

    # Write only after every contract anchor has succeeded.
    SONG.write_text(song, encoding="utf-8", newline="\n")
    SERVICE.write_text(service, encoding="utf-8", newline="\n")
    CTRL.write_text(ctrl, encoding="utf-8", newline="\n")

    print("R38_16L1_RESTORE_EXACT_REVISION_REPAIR_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
