<?php
declare(strict_types=1);

namespace App\Domain\Song;

use Doctrine\Bundle\DoctrineBundle\Repository\ServiceEntityRepository;
use Doctrine\Persistence\ManagerRegistry;

final class LyricsSourceRevisionRepository extends ServiceEntityRepository
{
    public function __construct(ManagerRegistry $registry)
    {
        parent::__construct($registry, LyricsSourceRevision::class);
    }

    /** @return list<LyricsSourceRevision> */
    public function findForSong(Song $song): array
    {
        return $this->createQueryBuilder('revision')
            ->andWhere('revision.song = :song')
            ->setParameter('song', $song)
            ->orderBy('revision.createdAt', 'DESC')
            ->addOrderBy('revision.id', 'DESC')
            ->getQuery()
            ->getResult();
    }

    public function findCurrentForSong(Song $song): ?LyricsSourceRevision
    {
        $current = str_replace(["\r\n", "\r"], "\n", (string) $song->getLyricsSourceText());
        if ($current === '') {
            return null;
        }

        $revision = $this->createQueryBuilder('revision')
            ->andWhere('revision.song = :song')
            ->andWhere('revision.content = :content')
            ->setParameter('song', $song)
            ->setParameter('content', $current)
            ->orderBy('revision.createdAt', 'DESC')
            ->addOrderBy('revision.id', 'DESC')
            ->setMaxResults(1)
            ->getQuery()
            ->getOneOrNullResult();

        return $revision instanceof LyricsSourceRevision ? $revision : null;
    }

    public function findLatestForSong(Song $song): ?LyricsSourceRevision
    {
        $revision = $this->createQueryBuilder('revision')
            ->andWhere('revision.song = :song')
            ->setParameter('song', $song)
            ->orderBy('revision.createdAt', 'DESC')
            ->addOrderBy('revision.id', 'DESC')
            ->setMaxResults(1)
            ->getQuery()
            ->getOneOrNullResult();

        return $revision instanceof LyricsSourceRevision ? $revision : null;
    }
}
