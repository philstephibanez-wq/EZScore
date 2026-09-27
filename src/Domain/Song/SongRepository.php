<?php

declare(strict_types=1);

namespace App\Domain\Song;

use App\Domain\User\User;
use Doctrine\Bundle\DoctrineBundle\Repository\ServiceEntityRepository;
use Doctrine\ORM\QueryBuilder;
use Doctrine\Persistence\ManagerRegistry;

final class SongRepository extends ServiceEntityRepository
{
    public function __construct(ManagerRegistry $registry)
    {
        parent::__construct($registry, Song::class);
    }

    /** @return list<Song> */
    public function findCatalog(?string $query = null, string $sort = 'title', ?string $letter = null): array
    {
        $qb = $this->baseCatalogQuery();
        $this->applySearch($qb, $query);
        $this->applyLetter($qb, $letter, $sort);
        $this->applySort($qb, $sort);

        return $qb->getQuery()->getResult();
    }

    /** @return list<Song> */
    public function findPublished(?string $query = null, string $sort = 'title', ?string $letter = null): array
    {
        $qb = $this->baseCatalogQuery()
            ->andWhere('s.status = :status')
            ->setParameter('status', SongStatus::Published->value);

        $this->applySearch($qb, $query);
        $this->applyLetter($qb, $letter, $sort);
        $this->applySort($qb, $sort);

        return $qb->getQuery()->getResult();
    }

    /** @return list<Song> */
    public function findForEditor(User $editor, ?string $query = null, string $sort = 'title', ?string $letter = null): array
    {
        $qb = $this->baseCatalogQuery()
            ->leftJoin('App\\Domain\\Song\\SongCollaborator','sc','WITH','sc.song = s AND sc.user = :editor')
            ->andWhere('(s.status = :published OR s.editor = :editor OR sc.id IS NOT NULL)')
            ->setParameter('published', SongStatus::Published->value)
            ->setParameter('editor', $editor);

        $this->applySearch($qb, $query);
        $this->applyLetter($qb, $letter, $sort);
        $this->applySort($qb, $sort);

        return $qb->getQuery()->getResult();
    }

    public function findByAudioSha256(string $sha256): ?Song { return $this->findOneBy(['audioSha256'=>$sha256]); }
    public function findLikelyDuplicate(string $title,string $artist): array { return $this->createQueryBuilder('s')->andWhere('LOWER(TRIM(s.title)) = :title')->andWhere('LOWER(TRIM(s.artist)) = :artist')->setParameter('title',mb_strtolower(trim($title)))->setParameter('artist',mb_strtolower(trim($artist)))->orderBy('s.id','ASC')->getQuery()->getResult(); }

    private function baseCatalogQuery(): QueryBuilder
    {
        return $this->createQueryBuilder('s')
            ->leftJoin('s.editor', 'e')
            ->addSelect('e');
    }

    private function applySort(QueryBuilder $qb, string $sort): void
    {
        if ($sort === 'artist') {
            $qb->orderBy('LOWER(s.artist)', 'ASC')
                ->addOrderBy('LOWER(s.title)', 'ASC');
            return;
        }

        $qb->orderBy('LOWER(s.title)', 'ASC')
            ->addOrderBy('LOWER(s.artist)', 'ASC');
    }

    private function applyLetter(QueryBuilder $qb, ?string $letter, string $sort): void
    {
        $letter = mb_strtoupper(trim((string) $letter));
        if (!preg_match('/^[A-Z]$/', $letter)) {
            return;
        }

        $field = $sort === 'artist' ? 's.artist' : 's.title';
        $qb->andWhere(sprintf('UPPER(SUBSTRING(%s, 1, 1)) = :letter', $field))
            ->setParameter('letter', $letter);
    }

    private function applySearch(QueryBuilder $qb, ?string $query): void
    {
        $query = trim((string) $query);
        if ($query === '') {
            return;
        }

        $qb->andWhere(
            $qb->expr()->orX(
                'LOWER(s.title) LIKE :query',
                'LOWER(s.artist) LIKE :query',
                'LOWER(COALESCE(s.author, \'\')) LIKE :query',
                'LOWER(COALESCE(s.composer, \'\')) LIKE :query',
                'LOWER(COALESCE(e.displayName, \'\')) LIKE :query',
            )
        )->setParameter('query', '%' . mb_strtolower($query) . '%');
    }
}
