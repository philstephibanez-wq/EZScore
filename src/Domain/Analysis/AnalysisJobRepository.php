<?php

declare(strict_types=1);

namespace App\Domain\Analysis;

use Doctrine\Bundle\DoctrineBundle\Repository\ServiceEntityRepository;
use Doctrine\Persistence\ManagerRegistry;

final class AnalysisJobRepository extends ServiceEntityRepository
{
    public function __construct(ManagerRegistry $registry)
    {
        parent::__construct($registry, AnalysisJob::class);
    }

    /** @return list<AnalysisJob> */
    public function findDesktopQueue(int $limit = 100): array
    {
        return $this->createQueryBuilder('job')
            ->leftJoin('job.song', 'song')
            ->addSelect('song')
            ->andWhere('job.status IN (:statuses)')
            ->setParameter('statuses', [
                AnalysisJobStatus::Queued->value,
                AnalysisJobStatus::Running->value,
            ])
            ->orderBy('job.status', 'DESC')
            ->addOrderBy('job.createdAt', 'ASC')
            ->addOrderBy('job.id', 'ASC')
            ->setMaxResults(max(1, min(500, $limit)))
            ->getQuery()
            ->getResult();
    }

    public function findStaleRunning(\DateTimeImmutable $cutoff): array
    {
        return $this->createQueryBuilder('job')->andWhere('job.status = :status')->andWhere('job.updatedAt < :cutoff')->setParameter('status', AnalysisJobStatus::Running->value)->setParameter('cutoff',$cutoff)->orderBy('job.updatedAt','ASC')->getQuery()->getResult();
    }

    public function findNextQueued(): ?AnalysisJob
    {
        return $this->createQueryBuilder('job')
            ->andWhere('job.status = :status')
            ->setParameter('status', AnalysisJobStatus::Queued->value)
            ->orderBy('job.createdAt', 'ASC')
            ->addOrderBy('job.id', 'ASC')
            ->setMaxResults(1)
            ->getQuery()
            ->getOneOrNullResult();
    }
}
