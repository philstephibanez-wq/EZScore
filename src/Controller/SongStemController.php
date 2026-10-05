<?php

declare(strict_types=1);

namespace App\Controller;

use App\Domain\Analysis\AnalysisJobStatus;
use App\Domain\Song\Song;
use App\Domain\Song\UserSongStemMix;
use App\Domain\Song\UserSongStemMixRepository;
use App\Domain\User\User;
use App\Service\AnalysisCapabilityState;
use App\Service\SongStemJobService;
use App\Service\SongStemStorage;
use App\Service\SongStemPlaybackStorage;
use App\Service\SongAccessPolicy;
use Doctrine\ORM\EntityManagerInterface;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\BinaryFileResponse;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\HttpFoundation\ResponseHeaderBag;
use Symfony\Component\Routing\Attribute\Route;
use Symfony\Contracts\Translation\TranslatorInterface;

#[Route('/song/{id}/stems', requirements: ['id' => '\d+'])]
final class SongStemController extends AbstractController
{
    public function __construct(private readonly SongAccessPolicy $songAccess) {}

    #[Route('', name: 'app_song_stems', methods: ['GET'])]
    public function show(
        Song $song,
        SongStemJobService $jobs,
        SongStemStorage $storage,
        AnalysisCapabilityState $workerState,
        UserSongStemMixRepository $mixes,
        SongStemPlaybackStorage $playback,
    ): Response {
        $user = $this->requireEditor($song);

        $latest = $jobs->latest($song);
        $progress = $storage->progress($song);
        $manifest = $storage->manifest($song);
        $complete = $storage->hasCompleteStems($song);
        $mix = $mixes->findForUserAndSong($user, $song);

        $isActive = $latest !== null && in_array(
            $latest->getStatus(),
            [AnalysisJobStatus::Queued, AnalysisJobStatus::Running],
            true,
        );

        return $this->render('stems/index.html.twig', [
            'song' => $song,
            'latest_job' => $latest,
            'progress' => $progress,
            'manifest' => $manifest,
            'stems_complete' => $complete,
            'stem_names' => SongStemStorage::STEMS,
            'job_active' => $isActive,
            'analysis_worker_online' => $workerState->isAvailable(),
            'stem_mix_settings' => $mix?->getSettings() ?? [],
            'playback_ready' => $playback->isReady($song),
            'playback_manifest' => $playback->manifest($song),
        ]);
    }

    #[Route('/generate', name: 'app_song_stems_generate', methods: ['POST'])]
    public function generate(
        Song $song,
        Request $request,
        SongStemJobService $jobs,
        AnalysisCapabilityState $workerState,
    ): Response {
        $user = $this->requireEditor($song);

        if (!$this->isCsrfTokenValid(
            'song_stems_generate_'.$song->getId(),
            (string) $request->request->get('_token'),
        )) {
            throw $this->createAccessDeniedException();
        }

        if (!$workerState->isAvailable()) {
            $this->addFlash('error', 'stems.error.worker_offline');

            return $this->redirectToRoute('app_song_stems', [
                '_locale' => $request->getLocale(),
                'id' => $song->getId(),
            ]);
        }

        if (!$song->getAudioStoragePath() || !$song->getAudioSha256()) {
            $this->addFlash('error', 'stems.error.no_audio');

            return $this->redirectToRoute('app_song_stems', [
                '_locale' => $request->getLocale(),
                'id' => $song->getId(),
            ]);
        }

        $force = $request->request->getBoolean('force');
        $job = $jobs->queue($song, $user, $force);

        if ($job->getStatus() !== AnalysisJobStatus::Queued) {
            $this->addFlash('success', 'stems.already_running');
        }

        return $this->redirectToRoute('app_song_stems', [
            '_locale' => $request->getLocale(),
            'id' => $song->getId(),
        ]);
    }

    #[Route('/mix', name: 'app_song_stems_mix', methods: ['POST'])]
    public function saveMix(
        Song $song,
        Request $request,
        UserSongStemMixRepository $mixes,
        EntityManagerInterface $em,
    ): JsonResponse {
        $user = $this->requireEditor($song);
        $payload = $request->toArray();

        if (!$this->isCsrfTokenValid(
            'song_stems_mix_'.$song->getId(),
            (string) ($payload['_token'] ?? ''),
        )) {
            return $this->json(['error' => 'invalid_csrf'], Response::HTTP_FORBIDDEN);
        }

        $settings = $payload['settings'] ?? null;
        if (!is_array($settings)) {
            return $this->json(['error' => 'invalid_settings'], Response::HTTP_UNPROCESSABLE_ENTITY);
        }

        $sanitized = $this->sanitizeMixSettings($settings);

        $mix = $mixes->findForUserAndSong($user, $song) ?? new UserSongStemMix($user, $song);
        $mix->setSettings($sanitized);

        $em->persist($mix);
        $em->flush();

        return $this->json([
            'ok' => true,
            'settings' => $mix->getSettings(),
            'updated_at' => $mix->getUpdatedAt()->format(DATE_ATOM),
        ]);
    }

    #[Route('/playback/build', name: 'app_song_stems_playback_build', methods: ['POST'])]
    public function buildPlayback(
        Song $song,
        Request $request,
        SongStemJobService $jobs,
        AnalysisCapabilityState $workerState,
        SongStemStorage $storage,
        TranslatorInterface $translator,
    ): Response {
        $user = $this->requireEditor($song);

        if (!$this->isCsrfTokenValid(
            'song_stems_playback_build_'.$song->getId(),
            (string) $request->request->get('_token'),
        )) {
            throw $this->createAccessDeniedException();
        }

        if (!$workerState->isAvailable()) {
            $this->addFlash('error', 'stems.error.worker_offline');

            return $this->redirectToRoute('app_song_stems', [
                '_locale' => $request->getLocale(),
                'id' => $song->getId(),
            ]);
        }

        if (!$storage->hasCompleteStems($song)) {
            $this->addFlash('error', $translator->trans('stems.playback.requires_stems', [], 'stems'));

            return $this->redirectToRoute('app_song_stems', [
                '_locale' => $request->getLocale(),
                'id' => $song->getId(),
            ]);
        }

        // force=false is intentional: stems_only.py returns immediately for an
        // existing current run, then SongStemWorker only builds the Opus proxies.
        $jobs->queue($song, $user, false);
        $this->addFlash('success', $translator->trans('stems.playback.queued', [], 'stems'));

        return $this->redirectToRoute('app_song_stems', [
            '_locale' => $request->getLocale(),
            'id' => $song->getId(),
        ]);
    }

    #[Route('/log', name: 'app_song_stems_log', methods: ['GET'])]
    public function log(
        Song $song,
        SongStemStorage $storage,
        SongStemJobService $jobs,
    ): JsonResponse {
        $this->requireEditor($song);

        $latest = $jobs->latest($song);

        return $this->json([
            'exists' => $storage->logExists($song),
            'content' => $storage->readLogTail($song),
            'progress' => $storage->progress($song),
            'job_id' => $latest?->getId(),
            'job_status' => $latest?->getStatus()->value,
            'stems_complete' => $storage->hasCompleteStems($song),
            'generated_at' => (new \DateTimeImmutable())->format(DATE_ATOM),
        ]);
    }

    #[Route('/log/download', name: 'app_song_stems_log_download', methods: ['GET'])]
    public function downloadLog(
        Song $song,
        SongStemStorage $storage,
    ): Response {
        $this->requireEditor($song);

        $path = $storage->logPath($song);
        if (!is_file($path)) {
            throw $this->createNotFoundException();
        }

        $response = new BinaryFileResponse($path);
        $response->headers->set('Content-Type', 'text/plain; charset=UTF-8');
        $response->setContentDisposition(
            ResponseHeaderBag::DISPOSITION_ATTACHMENT,
            sprintf('ezscore-stems-song-%d.log', (int) $song->getId()),
        );

        return $response;
    }

    #[Route('/playback/{name}', name: 'app_song_stems_playback_audio', methods: ['GET'])]
    public function playbackAudio(
        Song $song,
        string $name,
        SongStemPlaybackStorage $playback,
    ): Response {
        $this->requireEditor($song);

        $mediaPath = $playback->mediaRelativePath($song, $name);
        if ($mediaPath === null) {
            throw $this->createNotFoundException();
        }

        // R41.0K6: authorization remains in Symfony; Caddy serves the media bytes.
        return $this->redirect('/media/'.$mediaPath, Response::HTTP_FOUND);
    }

    #[Route('/original', name: 'app_song_stems_original_audio', methods: ['GET'])]
    public function originalAudio(
        Song $song,
        SongStemStorage $storage,
    ): Response {
        $this->requireEditor($song);

        // Use the exact same source resolver as the STEM worker.
        // BinaryFileResponse keeps HTTP Range support, which is required by
        // the streaming player and future karaoke transport.
        $path = $storage->sourcePath($song);

        if (!is_file($path) || filesize($path) === 0) {
            throw $this->createNotFoundException();
        }

        $response = new BinaryFileResponse($path);
        $response->headers->set('Content-Type', $song->getAudioMimeType() ?: 'application/octet-stream');
        $response->headers->set('Cache-Control', 'private, max-age=3600');
        $response->headers->set('Accept-Ranges', 'bytes');
        $response->setContentDisposition(
            ResponseHeaderBag::DISPOSITION_INLINE,
            $song->getAudioOriginalName() ?: 'original-audio',
        );

        return $response;
    }

    #[Route('/audio/{name}', name: 'app_song_stem_audio', methods: ['GET'])]
    public function audio(
        Song $song,
        string $name,
        SongStemStorage $storage,
    ): Response {
        $this->requireEditor($song);

        $path = $storage->stemPath($song, $name);
        if ($path === null) {
            throw $this->createNotFoundException();
        }

        $response = new BinaryFileResponse($path);
        $response->headers->set('Content-Type', 'audio/wav');
        $response->headers->set('Cache-Control', 'private, max-age=3600');
        $response->setContentDisposition(
            ResponseHeaderBag::DISPOSITION_INLINE,
            $name.'.wav',
        );

        return $response;
    }

    /**
     * @param array<string,mixed> $settings
     * @return array<string,mixed>
     */
    private function sanitizeMixSettings(array $settings): array
    {
        $allowedTracks = [
            'original',
            'lead_vocals',
            'backing_vocals',
            'drums',
            'bass',
            'guitar',
            'piano',
            'other',
        ];
        $tracks = [];
        $rawTracks = is_array($settings['tracks'] ?? null) ? $settings['tracks'] : [];
        foreach ($allowedTracks as $track) {
            $raw = is_array($rawTracks[$track] ?? null) ? $rawTracks[$track] : [];
            $tracks[$track] = [
                'enabled' => (bool) ($raw['enabled'] ?? ($track === 'original')),
                'volume' => $this->clampFloat($raw['volume'] ?? ($track === 'original' ? 1.0 : 0.72), 0.0, 1.25),
            ];
        }
        $eq = is_array($settings['master_eq'] ?? null) ? $settings['master_eq'] : [];
        return [
            'schema_version' => 'ezscore.stem_mix.v2',
            'master_volume' => $this->clampFloat($settings['master_volume'] ?? 1.0, 0.0, 1.25),
            'playback_rate' => $this->clampFloat($settings['playback_rate'] ?? 1.0, 0.75, 1.25),
            'master_eq' => [
                'low' => $this->clampFloat($eq['low'] ?? 0.0, -12.0, 12.0),
                'mid' => $this->clampFloat($eq['mid'] ?? 0.0, -12.0, 12.0),
                'high' => $this->clampFloat($eq['high'] ?? 0.0, -12.0, 12.0),
            ],
            'master_compression' => $this->clampFloat($settings['master_compression'] ?? 0.0, 0.0, 100.0),
            'tracks' => $tracks,
        ];
    }

    private function clampFloat(mixed $value, float $min, float $max): float
    {
        $number = is_numeric($value) ? (float) $value : $min;

        return max($min, min($max, $number));
    }

    private function requireEditor(Song $song): User
    {
        $user=$this->getUser();
        if(!$user instanceof User || !$this->songAccess->canEdit($song,$user,$this->isGranted('ROLE_ADMIN'))) throw $this->createAccessDeniedException();
        return $user;
    }
}
