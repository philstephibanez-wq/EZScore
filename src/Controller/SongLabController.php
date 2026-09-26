<?php

declare(strict_types=1);

namespace App\Controller;

use App\Domain\Song\Song;
use App\Domain\Song\SongTimelineEvent;
use App\Domain\Song\SongTimelineEventRepository;
use App\Domain\Song\UserSongStemMixRepository;
use App\Domain\User\User;
use App\Service\ChordTimelineAnalysisService;
use App\Service\SongChordJobService;
use App\Service\SongStemPlaybackStorage;
use Doctrine\ORM\EntityManagerInterface;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;

#[Route('/song/{id}/lab', requirements: ['id' => '\d+'])]
final class SongLabController extends AbstractController
{
    private const TIME_SIGNATURES = [
        'auto',
        '2/2', '2/4',
        '3/2', '3/4', '3/8',
        '4/2', '4/4', '4/8',
        '5/4', '5/8',
        '6/4', '6/8',
        '7/4', '7/8',
        '8/8',
        '9/8',
        '10/8',
        '11/8',
        '12/8', '12/16',
        '13/8', '13/16',
        '14/8',
        '15/8', '15/16',
        '16/8',
    ];

    #[Route('/analysis', name: 'app_song_analysis_lab', methods: ['GET'])]
    public function analysis(Song $song): Response
    {
        $this->requireEditor($song);
        return $this->renderLab($song, 'analysis');
    }

    #[Route('/chords', name: 'app_song_chordslab', methods: ['GET'])]
    public function chords(
        Song $song,
        SongTimelineEventRepository $timeline,
        UserSongStemMixRepository $mixes,
        SongStemPlaybackStorage $playback,
    ): Response {
        $user = $this->requireEditor($song);
        $activeProfile = $song->getChordAnalysisLevel();
        $profiles = [];

        foreach (['beginner', 'intermediate', 'expert'] as $profile) {
            $profiles[$profile] = array_map(
                static fn (SongTimelineEvent $event): array => [
                    'id' => $event->getId(),
                    'start_ms' => $event->getStartMs(),
                    'end_ms' => $event->getEndMs(),
                    'measure_index' => $event->getMeasureIndex(),
                    'beat_index' => $event->getBeatIndex(),
                    'subdivision_index' => $event->getSubdivisionIndex(),
                    'original' => $event->getOriginalValue(),
                    'override' => $event->getOverrideValue(),
                    'effective' => $event->getEffectiveValue(),
                ],
                $timeline->findChordEventsForProfile($song, $profile),
            );
        }

        return $this->render('song/chordslab.html.twig', [
            'song' => $song,
            'chord_profile' => $activeProfile,
            'chord_profiles' => $profiles,
            'chord_events' => $profiles[$activeProfile] ?? [],
            'beat_events' => array_map(
                static fn (SongTimelineEvent $event): array => [
                    'id' => $event->getId(),
                    'start_ms' => $event->getStartMs(),
                    'measure_index' => $event->getMeasureIndex(),
                    'beat_index' => $event->getBeatIndex(),
                    'subdivision_index' => $event->getSubdivisionIndex(),
                ],
                $timeline->findBeatEvents($song),
            ),
            'time_signatures' => self::TIME_SIGNATURES,
            'stem_mix_settings' => $mixes->findForUserAndSong($user, $song)?->getSettings() ?? [],
            'playback_ready' => $playback->isReady($song),
        ]);
    }

    #[Route('/chords/analyze', name: 'app_song_chordslab_analyze', methods: ['POST'])]
    public function analyzeChords(
        Song $song,
        Request $request,
        SongChordJobService $chordJobs,
    ): Response {
        $user = $this->requireEditor($song);

        if (!$this->isCsrfTokenValid(
            'song_chordslab_analyze_'.$song->getId(),
            (string) $request->request->get('_token'),
        )) {
            throw $this->createAccessDeniedException();
        }

        $chordJobs->queue($song, $user);

        return $this->redirectToRoute('app_song_chordslab', [
            '_locale' => $request->getLocale(),
            'id' => $song->getId(),
        ]);
    }

    #[Route('/chords/status', name: 'app_song_chordslab_status', methods: ['GET'])]
    public function chordStatus(Song $song, SongChordJobService $chordJobs): JsonResponse
    {
        $this->requireEditor($song);
        $job = $chordJobs->latest($song);

        if (!$job) {
            return $this->json(['status' => 'none', 'progress' => 0]);
        }

        return $this->json([
            'job_id' => $job->getId(),
            'status' => $job->getStatus()->value,
            'progress' => $job->getProgress(),
            'error' => $job->getErrorCode(),
        ]);
    }


    #[Route('/chords/profile', name: 'app_song_chordslab_profile', methods: ['POST'])]
    public function saveChordProfile(
        Song $song,
        Request $request,
        EntityManagerInterface $em,
    ): JsonResponse {
        $this->requireEditor($song);
        $payload = $request->toArray();

        if (!$this->isCsrfTokenValid(
            'song_chordslab_profile_'.$song->getId(),
            (string) ($payload['_token'] ?? ''),
        )) {
            return $this->json(['error' => 'invalid_csrf'], Response::HTTP_FORBIDDEN);
        }

        $profile = trim((string) ($payload['profile'] ?? ''));
        if (!in_array($profile, ['beginner', 'intermediate', 'expert'], true)) {
            return $this->json(['error' => 'invalid_profile'], Response::HTTP_UNPROCESSABLE_ENTITY);
        }

        $song->setChordAnalysisLevel($profile);
        $em->flush();

        return $this->json(['ok' => true, 'profile' => $profile]);
    }

    #[Route('/chords/settings', name: 'app_song_chordslab_settings', methods: ['POST'])]
    public function saveChordSettings(
        Song $song,
        Request $request,
        EntityManagerInterface $em,
    ): Response {
        $this->requireEditor($song);

        if (!$this->isCsrfTokenValid(
            'song_chordslab_settings_'.$song->getId(),
            (string) $request->request->get('_token'),
        )) {
            throw $this->createAccessDeniedException();
        }

        $capo = (int) $request->request->get('capo', 0);
        $signature = trim((string) $request->request->get('time_signature', '4/4'));
        $level = trim((string) $request->request->get('chord_analysis_level', 'intermediate'));

        try {
            $song
                ->setCapo($capo)
                ->setTimeSignature($signature)
                ->setChordAnalysisLevel($level);
        } catch (\InvalidArgumentException) {
            $this->addFlash('error', 'chordslab.settings.invalid');

            return $this->redirectToRoute('app_song_chordslab', [
                '_locale' => $request->getLocale(),
                'id' => $song->getId(),
            ]);
        }

        $em->flush();
        $this->addFlash('success', 'chordslab.settings.saved');

        return $this->redirectToRoute('app_song_chordslab', [
            '_locale' => $request->getLocale(),
            'id' => $song->getId(),
        ]);
    }

    #[Route('/chords/event/{eventId}', name: 'app_song_chordslab_event', requirements: ['eventId' => '\d+'], methods: ['POST'])]
    public function saveChordOverride(
        Song $song,
        int $eventId,
        Request $request,
        SongTimelineEventRepository $timeline,
        EntityManagerInterface $em,
    ): JsonResponse {
        $this->requireEditor($song);

        $payload = $request->toArray();
        if (!$this->isCsrfTokenValid(
            'song_chordslab_edit_'.$song->getId(),
            (string) ($payload['_token'] ?? ''),
        )) {
            return $this->json(['error' => 'invalid_csrf'], Response::HTTP_FORBIDDEN);
        }

        $event = $timeline->find($eventId);
        if (!$event instanceof SongTimelineEvent
            || $event->getSong()->getId() !== $song->getId()
            || $event->getEventType() !== SongTimelineEvent::TYPE_CHORD) {
            return $this->json(['error' => 'not_found'], Response::HTTP_NOT_FOUND);
        }

        $chord = trim((string) ($payload['chord'] ?? ''));
        // Plain major triads use standard compact spelling: C, not redundant Cmaj.
        $chord = preg_replace('/^([A-G](?:#|b)?)maj$/', '$1', $chord) ?? $chord;
        if ($chord === '' || mb_strlen($chord) > 32 || !preg_match('/^[A-G](?:#|b)?[A-Za-z0-9()+#b°øΔ\/-]*$/u', $chord)) {
            return $this->json(['error' => 'invalid_chord'], Response::HTTP_UNPROCESSABLE_ENTITY);
        }

        $event->setOverrideValue($chord);
        $em->flush();

        return $this->json([
            'ok' => true,
            'id' => $event->getId(),
            'original' => $event->getOriginalValue(),
            'override' => $event->getOverrideValue(),
            'effective' => $event->getEffectiveValue(),
        ]);
    }

    #[Route('/chords/reset', name: 'app_song_chordslab_reset', methods: ['POST'])]
    public function resetChordOverrides(
        Song $song,
        Request $request,
        SongTimelineEventRepository $timeline,
        EntityManagerInterface $em,
    ): Response {
        $this->requireEditor($song);

        if (!$this->isCsrfTokenValid(
            'song_chordslab_reset_'.$song->getId(),
            (string) $request->request->get('_token'),
        )) {
            throw $this->createAccessDeniedException();
        }

        $profile = $song->getChordAnalysisLevel();
        foreach ($timeline->findChordEventsForProfile($song, $profile) as $event) {
            $event->resetOverride();
        }

        $em->flush();
        $this->addFlash('success', 'chordslab.reset.done');

        return $this->redirectToRoute('app_song_chordslab', [
            '_locale' => $request->getLocale(),
            'id' => $song->getId(),
        ]);
    }

    #[Route('/lyrics', name: 'app_song_lyricslab', methods: ['GET'])]
    public function lyrics(Song $song): Response
    {
        $this->requireEditor($song);
        return $this->renderLab($song, 'lyrics');
    }

    #[Route('/publication', name: 'app_song_publication_lab', methods: ['GET'])]
    public function publication(Song $song): Response
    {
        $this->requireEditor($song);
        return $this->renderLab($song, 'publication');
    }

    private function renderLab(Song $song, string $lab): Response
    {
        return $this->render('song/lab_placeholder.html.twig', [
            'song' => $song,
            'lab' => $lab,
        ]);
    }

    private function requireEditor(Song $song): User
    {
        $user = $this->getUser();

        $allowed = $user instanceof User && (
            $this->isGranted('ROLE_ADMIN')
            || (
                $this->isGranted('ROLE_EDITOR')
                && $song->getEditor()?->getId() === $user->getId()
            )
        );

        if (!$allowed) {
            throw $this->createAccessDeniedException();
        }

        return $user;
    }
}
