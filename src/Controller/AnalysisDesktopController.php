<?php

declare(strict_types=1);

namespace App\Controller;

use App\Domain\Analysis\AnalysisJob;
use App\Domain\Analysis\AnalysisJobStatus;
use App\Domain\Analysis\AnalysisJobRepository;
use App\Service\AnalysisDesktopStateStore;
use App\Service\AnalysisWorkerTokenGuard;
use App\Service\ChordTimelineResultService;
use App\Service\ChordTimelineStorage;
use App\Service\SongChordJobService;
use App\Service\SongStemJobService;
use App\Service\SongLyricsJobService;
use App\Service\LyricsTimelineStorage;
use App\Service\LyricsTimelineResultService;
use App\Service\SongStemStorage;
use Doctrine\ORM\EntityManagerInterface;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;

#[Route('/internal/analysis/desktop')]
final class AnalysisDesktopController extends AbstractController
{
    public function __construct(
        private readonly AnalysisWorkerTokenGuard $guard,
        private readonly AnalysisDesktopStateStore $state,
        private readonly AnalysisJobRepository $jobs,
        private readonly SongChordJobService $chordJobs,
        private readonly ChordTimelineStorage $chordStorage,
        private readonly ChordTimelineResultService $chordResults,
        private readonly SongStemJobService $stemJobs,
        private readonly SongStemStorage $stemStorage,
        private readonly SongLyricsJobService $lyricsJobs,
        private readonly LyricsTimelineStorage $lyricsStorage,
        private readonly LyricsTimelineResultService $lyricsResults,
        private readonly EntityManagerInterface $em,
    ) {}

    #[Route('/hello', name: 'internal_analysis_desktop_hello', methods: ['POST'])]
    public function hello(Request $request): JsonResponse
    {
        $this->guard->assertAuthorized($request);
        $payload = $request->toArray();
        $state = $this->state->updateHeartbeat($payload);
        $workerId = trim((string) ($payload['worker_id'] ?? ''));

        return $this->json([
            'schema_version' => AnalysisDesktopStateStore::SCHEMA_VERSION,
            'server_time' => (new \DateTimeImmutable())->format(DATE_ATOM),
            'state' => $state,
            'commands' => $this->state->pendingCommands($workerId),
        ]);
    }

    #[Route('/heartbeat', name: 'internal_analysis_desktop_heartbeat', methods: ['POST'])]
    public function heartbeat(Request $request): JsonResponse
    {
        $this->guard->assertAuthorized($request);
        $payload = $request->toArray();
        $state = $this->state->updateHeartbeat($payload);
        $workerId = trim((string) ($payload['worker_id'] ?? ''));

        $currentJob = $payload['current_job'] ?? null;
        $currentJobId = is_array($currentJob) ? (int) ($currentJob['job_id'] ?? 0) : 0;
        if ($currentJobId > 0) {
            $activeJob = $this->jobs->find($currentJobId);
            if ($activeJob instanceof AnalysisJob && $activeJob->getStatus() === AnalysisJobStatus::Running) {
                $activeJob->touchLease();
                $this->em->flush();
            }
        }

        return $this->json([
            'schema_version' => AnalysisDesktopStateStore::SCHEMA_VERSION,
            'server_time' => (new \DateTimeImmutable())->format(DATE_ATOM),
            'state' => $state,
            'commands' => $this->state->pendingCommands($workerId),
        ]);
    }

    #[Route('/commands/{id}/ack', name: 'internal_analysis_desktop_command_ack', methods: ['POST'])]
    public function acknowledge(string $id, Request $request): JsonResponse
    {
        $this->guard->assertAuthorized($request);
        $this->state->acknowledge($id);

        return $this->json(['ok' => true, 'id' => $id]);
    }

    #[Route('/jobs/queue', name: 'internal_analysis_desktop_job_queue', methods: ['GET'])]
    public function queue(Request $request): JsonResponse
    {
        $this->guard->assertAuthorized($request);
        $this->recoverStaleJobs();
        $rows = [];
        foreach ($this->jobs->findDesktopQueue() as $job) {
            $song = $job->getSong();
            $rows[] = [
                'job_id' => $job->getId(),
                'kind' => $job->getKind(),
                'status' => $job->getStatus()->value,
                'progress' => $job->getProgress(),
                'song_id' => $song->getId(),
                'title' => $song->getTitle(),
                'artist' => $song->getArtist(),
            ];
        }
        return $this->json([
            'schema_version' => AnalysisDesktopStateStore::SCHEMA_VERSION,
            'jobs' => $rows,
        ]);
    }

    #[Route('/jobs/claim', name: 'internal_analysis_desktop_job_claim', methods: ['POST'])]
    public function claim(Request $request): Response
    {
        $this->guard->assertAuthorized($request);
        $this->recoverStaleJobs();

        $job = $this->chordJobs->claimNext() ?? $this->lyricsJobs->claimNext() ?? $this->stemJobs->claimNext();
        if (!$job instanceof AnalysisJob) {
            return new Response('', Response::HTTP_NO_CONTENT);
        }

        return $this->json($this->jobContext($job));
    }

    #[Route('/jobs/{id}/context', name: 'internal_analysis_desktop_job_context', requirements: ['id' => '\d+'], methods: ['GET'])]
    public function context(AnalysisJob $job, Request $request): JsonResponse
    {
        $this->guard->assertAuthorized($request);

        if (!in_array($job->getKind(), [SongStemJobService::KIND, SongChordJobService::KIND, SongLyricsJobService::KIND], true)) {
            return $this->json(['error' => 'Unsupported job kind.'], Response::HTTP_CONFLICT);
        }

        return $this->json($this->jobContext($job));
    }

    #[Route('/jobs/{id}/progress', name: 'internal_analysis_desktop_job_progress', requirements: ['id' => '\d+'], methods: ['POST'])]
    public function progress(AnalysisJob $job, Request $request): JsonResponse
    {
        $this->guard->assertAuthorized($request);

        if ($job->getStatus() !== AnalysisJobStatus::Running) {
            return $this->json(['error' => 'Job is not running.'], Response::HTTP_CONFLICT);
        }

        $payload = $request->toArray();
        $progress = filter_var(
            $payload['progress'] ?? null,
            FILTER_VALIDATE_INT,
            ['options' => ['min_range' => 0, 'max_range' => 100]],
        );
        if ($progress === false) {
            return $this->json(['error' => 'progress must be 0..100.'], Response::HTTP_UNPROCESSABLE_ENTITY);
        }

        $job->setProgress($progress);
        $this->em->flush();

        return $this->json([
            'job_id' => $job->getId(),
            'status' => $job->getStatus()->value,
            'progress' => $job->getProgress(),
        ]);
    }

    #[Route('/jobs/{id}/complete', name: 'internal_analysis_desktop_job_complete', requirements: ['id' => '\d+'], methods: ['POST'])]
    public function complete(AnalysisJob $job, Request $request): JsonResponse
    {
        $this->guard->assertAuthorized($request);

        if ($job->getKind() === SongLyricsJobService::KIND) {
            try {
                $result = $this->lyricsStorage->readResult($job->getSong());
                $mode = (string) ($job->getRequestData()['mode'] ?? ($result['mode'] ?? 'align'));

                if ($mode === 'extract') {
                    $text = trim((string) ($result['text'] ?? ''));
                    if ($text === '') {
                        throw new \RuntimeException('lyrics_extract_empty');
                    }

                    $job->getSong()->setLyricsSourceText($text);
                    if (method_exists($job->getSong(), 'setLyricsCurrentRevisionId')) {
                        $job->getSong()->setLyricsCurrentRevisionId(null);
                    }
                    $this->em->flush();

                    if (trim((string) $job->getSong()->getLyricsSourceText()) !== $text) {
                        throw new \RuntimeException('lyrics_extract_persist_failed');
                    }

                    $summary = [
                        'schema_version' => 'ezscore.lyrics.extract.r37',
                        'mode' => 'extract',
                        'characters' => mb_strlen($text),
                        'recognized_words' => (int) ($result['recognized_words'] ?? 0),
                        'languages' => $result['languages'] ?? [],
                        'model' => $result['model'] ?? null,
                    ];
                } else {
                    $summary = $this->lyricsResults->apply($job->getSong(), $result);
                    $summary['mode'] = 'align';
                    $summary['languages'] = $result['languages'] ?? [];
                    $summary['model'] = $result['model'] ?? null;
                }

                $this->lyricsJobs->complete($job, $summary);
            } catch (\Throwable $error) {
                $this->lyricsJobs->fail($job, $error->getMessage());
                return $this->json(['error' => $error->getMessage()], Response::HTTP_CONFLICT);
            }

            return $this->json([
                'job_id' => $job->getId(),
                'status' => 'completed',
                'progress' => 100,
                'mode' => $mode,
            ]);
        }

        if ($job->getKind() === SongChordJobService::KIND) {
            try {
                $result = $this->chordStorage->readResult($job->getSong());
                $summary = $this->chordResults->apply($job->getSong(), $result);
                $this->chordJobs->complete($job, $summary);
            } catch (\Throwable $error) {
                $this->chordJobs->fail($job, $error->getMessage());
                return $this->json(['error' => $error->getMessage()], Response::HTTP_CONFLICT);
            }
            return $this->json(['job_id' => $job->getId(), 'status' => 'completed', 'progress' => 100]);
        }

        if ($job->getKind() !== SongStemJobService::KIND) {
            return $this->json(['error' => 'Unsupported job kind.'], Response::HTTP_CONFLICT);
        }
        if (!$this->stemStorage->hasCompleteStems($job->getSong())) {
            return $this->json(['error' => 'Persistent STEM manifest is incomplete.'], Response::HTTP_CONFLICT);
        }

        $manifest = $this->stemStorage->manifest($job->getSong()) ?? [];
        $this->stemStorage->pruneOtherAudioHashes($job->getSong());

        $this->stemJobs->complete($job, [
            'schema_version' => 'ezscore.stems.v1',
            'scope' => 'stems_only',
            'audio_sha256' => $job->getSong()->getAudioSha256(),
            'manifest' => $manifest,
            'artifacts' => array_values(SongStemStorage::STEMS),
        ]);

        return $this->json(['job_id' => $job->getId(), 'status' => 'completed', 'progress' => 100]);
    }

    #[Route('/jobs/{id}/fail', name: 'internal_analysis_desktop_job_fail', requirements: ['id' => '\d+'], methods: ['POST'])]
    public function fail(AnalysisJob $job, Request $request): JsonResponse
    {
        $this->guard->assertAuthorized($request);
        $payload = $request->toArray();
        $error = trim((string) ($payload['error'] ?? 'desktop_worker_failed'));
        if ($job->getKind() === SongChordJobService::KIND) {
            $this->chordJobs->fail($job, $error);
        } elseif ($job->getKind() === SongLyricsJobService::KIND) {
            $this->lyricsJobs->fail($job, $error);
        } else {
            $this->stemJobs->fail($job, $error);
        }

        return $this->json(['job_id' => $job->getId(), 'status' => 'failed']);
    }

    private function recoverStaleJobs(): int
    {
        $count=0; $cutoff=(new \DateTimeImmutable())->modify('-120 seconds');
        foreach($this->jobs->findStaleRunning($cutoff) as $job){$job->requeue();++$count;}
        if($count>0)$this->em->flush();
        return $count;
    }

    /**
     * @return array<string,mixed>
     */
    private function jobContext(AnalysisJob $job): array
    {
        $song = $job->getSong();

        return [
            'schema_version' => AnalysisDesktopStateStore::SCHEMA_VERSION,
            'job_id' => $job->getId(),
            'song_id' => $song->getId(),
            'kind' => $job->getKind(),
            'status' => $job->getStatus()->value,
            'progress' => $job->getProgress(),
            'song' => [
                'title' => $song->getTitle(),
                'artist' => $song->getArtist(),
            ],
            'request' => $job->getRequestData(),
            'paths' => $job->getKind() === SongChordJobService::KIND
                ? [
                    'source' => $this->chordStorage->sourcePath($song),
                    'progress_file' => $this->chordStorage->progressPath($song),
                    'result_file' => $this->chordStorage->resultPath($song),
                    'harmony_stems' => array_values(array_filter([
                        $this->stemStorage->stemPath($song, 'bass'),
                        $this->stemStorage->stemPath($song, 'guitar'),
                        $this->stemStorage->stemPath($song, 'piano'),
                        $this->stemStorage->stemPath($song, 'other'),
                    ])),
                    'drums' => $this->stemStorage->stemPath($song, 'drums'),
                ]
                : ($job->getKind() === SongLyricsJobService::KIND
                    ? [
                        'source' => $this->lyricsStorage->sourcePath($song),
                        'lead_vocals' => $this->stemStorage->stemPath($song, 'lead_vocals'),
                        'lyrics_file' => $this->lyricsStorage->lyricsPath($song),
                        'progress_file' => $this->lyricsStorage->progressPath($song),
                        'result_file' => $this->lyricsStorage->resultPath($song),
                    ]
                    : [
                    'source' => $this->stemStorage->sourcePath($song),
                    'storage_root' => $this->stemStorage->storageRoot($song),
                    'progress_file' => $this->stemStorage->progressPath($song),
                    'log_file' => $this->stemStorage->logPath($song),
                ]),
        ];
    }
}
