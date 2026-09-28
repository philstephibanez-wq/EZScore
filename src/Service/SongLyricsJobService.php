<?php
declare(strict_types=1);

namespace App\Service;

use App\Domain\Analysis\AnalysisJob;
use App\Domain\Analysis\AnalysisJobRepository;
use App\Domain\Analysis\AnalysisJobStatus;
use App\Domain\Song\Song;
use App\Domain\User\User;
use Doctrine\DBAL\Connection;
use Doctrine\ORM\EntityManagerInterface;

final class SongLyricsJobService
{
    public const KIND = 'lyrics';

    public function __construct(
        private readonly EntityManagerInterface $em,
        private readonly AnalysisJobRepository $jobs,
        private readonly Connection $connection,
        private readonly LyricsTimelineStorage $storage,
    ) {}

    public function queue(Song $song, User $user, string $mode = 'align'): AnalysisJob
    {
        if (!in_array($mode, ['align', 'extract'], true)) {
            throw new \InvalidArgumentException('Invalid lyrics job mode.');
        }

        if ($active = $this->findActive($song)) {
            return $active;
        }

        $request = [
            'audio_sha256' => $song->getAudioSha256(),
            'scope' => 'lyrics',
            'mode' => $mode,
            'language' => 'auto',
        ];

        if ($mode === 'align') {
            $lyrics = trim((string) $song->getLyricsSourceText());
            if ($lyrics === '') {
                throw new \DomainException('lyrics_text_required');
            }
            $request['lyrics_file'] = $this->storage->writeLyrics($song, $lyrics);
        }

        $job = new AnalysisJob($song, $user, self::KIND, $request);
        $this->em->persist($job);
        $this->em->flush();

        return $job;
    }

    public function claimNext(): ?AnalysisJob
    {
        for ($attempt = 0; $attempt < 3; ++$attempt) {
            $id = $this->connection->fetchOne(
                'SELECT id FROM analysis_jobs WHERE kind=:kind AND status=:status ORDER BY created_at ASC,id ASC LIMIT 1',
                ['kind' => self::KIND, 'status' => AnalysisJobStatus::Queued->value],
            );
            if ($id === false) {
                return null;
            }

            $updated = $this->connection->executeStatement(
                'UPDATE analysis_jobs SET status=:running, progress=1, updated_at=:updated WHERE id=:id AND status=:queued',
                [
                    'running' => AnalysisJobStatus::Running->value,
                    'updated' => (new \DateTimeImmutable())->format('Y-m-d H:i:s'),
                    'id' => (int) $id,
                    'queued' => AnalysisJobStatus::Queued->value,
                ],
            );
            if ($updated !== 1) {
                continue;
            }

            $this->em->clear();
            $job = $this->jobs->find((int) $id);
            return $job instanceof AnalysisJob ? $job : null;
        }

        return null;
    }

    public function latest(Song $song): ?AnalysisJob
    {
        return $this->jobs->createQueryBuilder('job')
            ->andWhere('job.song=:song')
            ->andWhere('job.kind=:kind')
            ->setParameter('song', $song)
            ->setParameter('kind', self::KIND)
            ->orderBy('job.createdAt', 'DESC')
            ->addOrderBy('job.id', 'DESC')
            ->setMaxResults(1)
            ->getQuery()
            ->getOneOrNullResult();
    }

    public function findActive(Song $song): ?AnalysisJob
    {
        return $this->jobs->createQueryBuilder('job')
            ->andWhere('job.song=:song')
            ->andWhere('job.kind=:kind')
            ->andWhere('job.status IN (:statuses)')
            ->setParameter('song', $song)
            ->setParameter('kind', self::KIND)
            ->setParameter('statuses', [
                AnalysisJobStatus::Queued->value,
                AnalysisJobStatus::Running->value,
            ])
            ->orderBy('job.createdAt', 'DESC')
            ->setMaxResults(1)
            ->getQuery()
            ->getOneOrNullResult();
    }

    public function complete(AnalysisJob $job, array $result): void
    {
        $job->complete($result);
        $this->em->flush();
    }

    public function fail(AnalysisJob $job, string $error): void
    {
        $job->fail(trim($error) !== '' ? mb_substr(trim($error), 0, 80) : 'lyrics_failed');
        $this->em->flush();
    }
}
