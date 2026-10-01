#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else r"H:\EZScore_v1").resolve()
REPO = ROOT / "src/Domain/Song/LyricsSourceRevisionRepository.php"
CTRL = ROOT / "src/Controller/LyricsHistoryController.php"
SERVICE = ROOT / "src/Service/LyricsSourceHistoryService.php"

REPO_METHOD = '    public function findCurrentForSong(Song $song): ?LyricsSourceRevision\n    {\n        $current = str_replace(["\\r\\n", "\\r"], "\\n", (string) $song->getLyricsSourceText());\n        if ($current === \'\') {\n            return null;\n        }\n\n        $revision = $this->createQueryBuilder(\'revision\')\n            ->andWhere(\'revision.song = :song\')\n            ->andWhere(\'revision.content = :content\')\n            ->setParameter(\'song\', $song)\n            ->setParameter(\'content\', $current)\n            ->orderBy(\'revision.createdAt\', \'DESC\')\n            ->addOrderBy(\'revision.id\', \'DESC\')\n            ->setMaxResults(1)\n            ->getQuery()\n            ->getOneOrNullResult();\n\n        return $revision instanceof LyricsSourceRevision ? $revision : null;\n    }\n\n'
OLD_LIST = '        $current = str_replace(["\\r\\n", "\\r"], "\\n", (string) $song->getLyricsSourceText());\n\n        return $this->json([\n            \'revisions\' => array_map(\n                fn (LyricsSourceRevision $revision): array => $this->serialise($revision, $current),\n                $revisions->findForSong($song),\n            ),\n        ]);\n'
NEW_LIST = "        $currentRevision = $revisions->findCurrentForSong($song);\n        $currentRevisionId = $currentRevision?->getId();\n\n        return $this->json([\n            'revisions' => array_map(\n                fn (LyricsSourceRevision $revision): array => $this->serialise($revision, $currentRevisionId),\n                $revisions->findForSong($song),\n            ),\n        ]);\n"
OLD_SERIALISE = "    private function serialise(LyricsSourceRevision $revision, string $current): array\n    {\n        $author = $revision->getCreatedBy();\n\n        return [\n            'id' => $revision->getId(),\n            'source_type' => $revision->getSourceType(),\n            'comment' => $revision->getComment(),\n            'created_at' => $revision->getCreatedAt()->format(DATE_ATOM),\n            'created_by' => $author?->getDisplayName(),\n            'is_current' => $revision->getContent() === $current,\n        ];\n    }\n"
NEW_SERIALISE = "    private function serialise(LyricsSourceRevision $revision, ?int $currentRevisionId): array\n    {\n        $author = $revision->getCreatedBy();\n\n        return [\n            'id' => $revision->getId(),\n            'source_type' => $revision->getSourceType(),\n            'comment' => $revision->getComment(),\n            'created_at' => $revision->getCreatedAt()->format(DATE_ATOM),\n            'created_by' => $author?->getDisplayName(),\n            'is_current' => $currentRevisionId !== null && $revision->getId() === $currentRevisionId,\n        ];\n    }\n"
OLD_DELETE = "        if ($revision->getContent() === $this->normaliseContent((string) $song->getLyricsSourceText())) {\n            throw new \\LogicException('current_revision');\n        }\n"
NEW_DELETE = "        $currentRevision = $this->revisions->findCurrentForSong($song);\n        if (\n            $currentRevision instanceof LyricsSourceRevision\n            && $currentRevision->getId() === $revision->getId()\n        ) {\n            throw new \\LogicException('current_revision');\n        }\n"

def main():
    for p in (REPO, CTRL, SERVICE):
        if not p.is_file():
            raise RuntimeError(f"Missing prerequisite: {p}")

    repo = REPO.read_text(encoding="utf-8")
    ctrl = CTRL.read_text(encoding="utf-8")
    service = SERVICE.read_text(encoding="utf-8")

    if "public function findCurrentForSong(" not in repo:
        anchor = "    public function findLatestForSong(Song $song): ?LyricsSourceRevision\n"
        pos = repo.find(anchor)
        if pos < 0:
            raise RuntimeError("Repository anchor not found")
        repo = repo[:pos] + REPO_METHOD + repo[pos:]

    if OLD_LIST in ctrl:
        ctrl = ctrl.replace(OLD_LIST, NEW_LIST, 1)
    elif "findCurrentForSong($song)" not in ctrl:
        raise RuntimeError("Controller list anchor not found")

    if OLD_SERIALISE in ctrl:
        ctrl = ctrl.replace(OLD_SERIALISE, NEW_SERIALISE, 1)
    elif "currentRevisionId" not in ctrl:
        raise RuntimeError("Controller serialise anchor not found")

    if OLD_DELETE in service:
        service = service.replace(OLD_DELETE, NEW_DELETE, 1)
    elif "findCurrentForSong($song)" not in service:
        raise RuntimeError("Service delete anchor not found")

    REPO.write_text(repo, encoding="utf-8", newline="\n")
    CTRL.write_text(ctrl, encoding="utf-8", newline="\n")
    SERVICE.write_text(service, encoding="utf-8", newline="\n")

    print("R38_16K_SINGLE_CURRENT_LYRICS_REVISION_INSTALL_OK")

if __name__ == "__main__":
    main()
