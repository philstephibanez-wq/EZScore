<?php
declare(strict_types=1);

namespace App\Service;

use App\Domain\Song\LyricsSourceRevision;
use App\Domain\Song\LyricsSourceRevisionRepository;
use App\Domain\Song\Song;
use App\Domain\User\User;
use Doctrine\ORM\EntityManagerInterface;

final class LyricsSourceHistoryService
{
    public const SOURCES = ['manual', 'lyrics_ovh', 'whisper', 'other', 'restore', 'legacy'];

    public function __construct(
        private readonly LyricsSourceRevisionRepository $revisions,
        private readonly EntityManagerInterface $em,
    ) {
    }

    public function saveVersion(
        Song $song,
        string $content,
        User $user,
        string $sourceType,
        ?string $comment,
    ): LyricsSourceRevision {
        $content = $this->normaliseContent($content);
        $sourceType = $this->normaliseSource($sourceType);
        $comment = $this->normaliseComment($comment);

        $latest = $this->revisions->findLatestForSong($song);
        if ($latest instanceof LyricsSourceRevision && $latest->getContent() === $content) {
            $latest->updateMetadata($sourceType, $comment, $user);
            $song->setLyricsSourceText($content);
            $this->em->flush();
            return $latest;
        }

        $revision = new LyricsSourceRevision($song, $content, $sourceType, $comment, $user);
        $this->em->persist($revision);
        $song->setLyricsSourceText($content);
        $this->em->flush();

        return $revision;
    }

    public function archiveCurrentIfChanged(
        Song $song,
        User $user,
        string $sourceType = 'manual',
        ?string $comment = null,
    ): ?LyricsSourceRevision {
        $current = $this->normaliseContent((string) $song->getLyricsSourceText());
        if (trim($current) === '') {
            return null;
        }

        $latest = $this->revisions->findLatestForSong($song);
        if ($latest instanceof LyricsSourceRevision && $latest->getContent() === $current) {
            return $latest;
        }

        $revision = new LyricsSourceRevision(
            $song,
            $current,
            $this->normaliseSource($sourceType),
            $this->normaliseComment($comment),
            $user,
        );
        $this->em->persist($revision);
        $this->em->flush();

        return $revision;
    }

    public function restore(Song $song, LyricsSourceRevision $target, User $user): LyricsSourceRevision
    {
        if ($target->getSong()->getId() !== $song->getId()) {
            throw new \InvalidArgumentException('Revision does not belong to this song.');
        }

        $this->archiveCurrentIfChanged(
            $song,
            $user,
            'manual',
            'Sauvegarde automatique avant restauration.',
        );

        $origin = sprintf(
            'Restauration de la sauvegarde #%d%s',
            (int) $target->getId(),
            $target->getComment() ? ' — '.$target->getComment() : '',
        );

        return $this->saveVersion($song, $target->getContent(), $user, 'restore', $origin);
    }

    public function delete(Song $song, LyricsSourceRevision $revision): void
    {
        if ($revision->getSong()->getId() !== $song->getId()) {
            throw new \InvalidArgumentException('Revision does not belong to this song.');
        }

        if ($revision->getContent() === $this->normaliseContent((string) $song->getLyricsSourceText())) {
            throw new \LogicException('current_revision');
        }

        $this->em->remove($revision);
        $this->em->flush();
    }

    private function normaliseSource(string $sourceType): string
    {
        $sourceType = trim($sourceType);
        return in_array($sourceType, self::SOURCES, true) ? $sourceType : 'other';
    }

    private function normaliseComment(?string $comment): ?string
    {
        if ($comment === null) {
            return null;
        }
        $comment = trim($comment);
        return $comment === '' ? null : mb_substr($comment, 0, 1000);
    }

    private function normaliseContent(string $content): string
    {
        return str_replace(["\r\n", "\r"], "\n", $content);
    }
}
