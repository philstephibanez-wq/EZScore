<?php
declare(strict_types=1);

namespace App\Controller;

use App\Domain\Event\Event;
use App\Domain\Event\LiveRun;
use App\Domain\Group\GroupMember;
use App\Domain\Playlist\PlaylistItem;
use App\Domain\Song\Song;
use App\Domain\Song\SongTimelineEvent;
use App\Domain\Song\SongTimelineEventRepository;
use App\Domain\User\User;
use Doctrine\ORM\EntityManagerInterface;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;
use Symfony\Component\Security\Csrf\CsrfToken;
use Symfony\Component\Security\Csrf\CsrfTokenManagerInterface;

#[Route('/live')]
final class LiveRunController extends AbstractController
{
    #[Route('/events/{id}/test/start', name: 'app_live_test_start', requirements: ['id' => '\d+'], methods: ['POST'])]
    public function startTest(Event $event, Request $request, EntityManagerInterface $em): Response
    {
        $user = $this->requireUser();
        $this->assertOwner($event, $user);

        if (!$this->isCsrfTokenValid('live_test_start_'.$event->getId(), (string) $request->request->get('_token'))) {
            throw $this->createAccessDeniedException();
        }

        $active = $em->getRepository(LiveRun::class)->findOneBy([
            'event' => $event,
            'status' => 'live',
        ]);

        if (!$active instanceof LiveRun) {
            $active = new LiveRun($event, $user, true);
            $em->persist($active);
            $em->flush();
            $this->addFlash('success', 'event.live.test_started');
        }

        return $this->redirectToRoute('app_event_session_playlist', [
            '_locale' => $request->getLocale(),
            'id' => $event->getId(),
        ]);
    }

    #[Route('/events/{id}/test/stop', name: 'app_live_test_stop', requirements: ['id' => '\d+'], methods: ['POST'])]
    public function stopTest(Event $event, Request $request, EntityManagerInterface $em): Response
    {
        $user = $this->requireUser();
        $this->assertOwner($event, $user);

        if (!$this->isCsrfTokenValid('live_test_stop_'.$event->getId(), (string) $request->request->get('_token'))) {
            throw $this->createAccessDeniedException();
        }

        $active = $em->getRepository(LiveRun::class)->findOneBy([
            'event' => $event,
            'status' => 'live',
        ]);

        if ($active instanceof LiveRun) {
            $active->end();
            $em->flush();
            $this->addFlash('success', 'event.live.test_stopped');
        }

        return $this->redirectToRoute('app_event_show', [
            '_locale' => $request->getLocale(),
            'id' => $event->getId(),
        ]);
    }

    #[Route('/display-home', name: 'app_live_display_home', methods: ['GET'])]
    public function displayHome(): Response
    {
        $user = $this->requireUser();
        if (!in_array('ROLE_DISPLAY', $user->getRoles(), true)) {
            throw $this->createAccessDeniedException();
        }

        return $this->render('live/display_home.html.twig');
    }

    #[Route('/open', name: 'app_live_open', methods: ['GET'])]
    public function open(EntityManagerInterface $em): JsonResponse
    {
        $user = $this->requireUser();

        if (!in_array('ROLE_DISPLAY', $user->getRoles(), true)) {
            return $this->json(['active' => false]);
        }

        foreach ($em->getRepository(LiveRun::class)->findBy(['status' => 'live'], ['startedAt' => 'DESC']) as $liveRun) {
            if (!$liveRun instanceof LiveRun || !$this->displayMayJoin($liveRun, $user, $em)) {
                continue;
            }

            return $this->json([
                'active' => true,
                'test' => $liveRun->isTestMode(),
                'id' => $liveRun->getId(),
                'title' => $liveRun->getEvent()->getTitle(),
                'conductor' => $liveRun->getConductor()->getDisplayName(),
                'join_url' => $this->generateUrl('app_live_display', ['id' => $liveRun->getId()]),
            ]);
        }

        return $this->json(['active' => false]);
    }

    #[Route('/conductor/context/{songId}', name: 'app_live_conductor_context', requirements: ['songId' => '\d+'], methods: ['GET'])]
    public function conductorContext(
        int $songId,
        EntityManagerInterface $em,
        CsrfTokenManagerInterface $csrf,
    ): JsonResponse {
        $user = $this->requireUser();
        $liveRun = $em->getRepository(LiveRun::class)->findOneBy([
            'conductor' => $user,
            'status' => 'live',
        ], ['startedAt' => 'DESC']);

        if (!$liveRun instanceof LiveRun || !$this->songBelongsToLivePlaylist($liveRun, $songId, $em)) {
            return $this->json(['active' => false]);
        }

        return $this->json([
            'active' => true,
            'live_run_id' => $liveRun->getId(),
            'state_url' => $this->generateUrl('app_live_state_update', ['id' => $liveRun->getId()]),
            'token' => (string) $csrf->getToken('live_state_'.$liveRun->getId()),
            'revision' => $liveRun->getRevision(),
        ]);
    }

    #[Route('/{id}/state', name: 'app_live_state_update', requirements: ['id' => '\d+'], methods: ['POST'])]
    public function updateState(
        LiveRun $liveRun,
        Request $request,
        EntityManagerInterface $em,
        CsrfTokenManagerInterface $csrf,
    ): JsonResponse {
        $user = $this->requireUser();
        if (!$liveRun->isLive() || $liveRun->getConductor()->getId() !== $user->getId()) {
            throw $this->createAccessDeniedException();
        }

        $payload = $request->toArray();
        $token = new CsrfToken('live_state_'.$liveRun->getId(), (string) ($payload['_token'] ?? ''));
        if (!$csrf->isTokenValid($token)) {
            return $this->json(['error' => 'invalid_csrf'], Response::HTTP_FORBIDDEN);
        }

        $songId = max(0, (int) ($payload['song_id'] ?? 0));
        if ($songId < 1 || !$this->songBelongsToLivePlaylist($liveRun, $songId, $em)) {
            return $this->json(['error' => 'song_not_in_session_playlist'], Response::HTTP_UNPROCESSABLE_ENTITY);
        }

        $liveRun->updateTransport(
            $songId,
            (bool) ($payload['playing'] ?? false),
            max(0, (int) ($payload['position_ms'] ?? 0)),
            (float) ($payload['playback_rate'] ?? 1.0),
        );
        $em->flush();

        return $this->json([
            'ok' => true,
            'revision' => $liveRun->getRevision(),
        ]);
    }

    #[Route('/{id}/state', name: 'app_live_state', requirements: ['id' => '\d+'], methods: ['GET'])]
    public function state(LiveRun $liveRun, EntityManagerInterface $em): JsonResponse
    {
        $user = $this->requireDisplayForRun($liveRun, $em);

        return $this->json([
            'live' => $liveRun->isLive(),
            'test' => $liveRun->isTestMode(),
            'revision' => $liveRun->getRevision(),
            'song_id' => $liveRun->getCurrentSongId(),
            'playing' => $liveRun->isPlaying(),
            'position_ms' => $liveRun->getPositionMs(),
            'playback_rate' => $liveRun->getPlaybackRate(),
            'state_updated_at' => $liveRun->getStateUpdatedAt()?->format(DATE_ATOM),
            'server_ms' => (int) floor(microtime(true) * 1000),
            'display_user_id' => $user->getId(),
        ]);
    }

    #[Route('/{id}/song/{songId}', name: 'app_live_song_data', requirements: ['id' => '\d+', 'songId' => '\d+'], methods: ['GET'])]
    public function songData(
        LiveRun $liveRun,
        int $songId,
        EntityManagerInterface $em,
        SongTimelineEventRepository $timeline,
    ): JsonResponse {
        $this->requireDisplayForRun($liveRun, $em);

        if (!$this->songBelongsToLivePlaylist($liveRun, $songId, $em)) {
            throw $this->createNotFoundException();
        }

        $song = $em->getRepository(Song::class)->find($songId);
        if (!$song instanceof Song) {
            throw $this->createNotFoundException();
        }

        $beats = array_map(static fn(SongTimelineEvent $event): array => [
            'id' => $event->getId(),
            'start_ms' => $event->getStartMs(),
            'measure_index' => $event->getMeasureIndex(),
            'beat_index' => $event->getBeatIndex(),
            'subdivision_index' => $event->getSubdivisionIndex(),
        ], $timeline->findBeatEvents($song));

        $chords = array_map(static fn(SongTimelineEvent $event): array => [
            'id' => $event->getId(),
            'start_ms' => $event->getStartMs(),
            'end_ms' => $event->getEndMs(),
            'measure_index' => $event->getMeasureIndex(),
            'beat_index' => $event->getBeatIndex(),
            'original' => $event->getOriginalValue(),
            'override' => $event->getOverrideValue(),
            'effective' => $event->getEffectiveValue(),
        ], $timeline->findChordEventsForProfile($song, $song->getChordAnalysisLevel()));

        $lyrics = array_map(static fn(SongTimelineEvent $event): array => [
            'id' => $event->getId(),
            'start_ms' => $event->getStartMs(),
            'end_ms' => $event->getEndMs(),
            'measure_index' => $event->getMeasureIndex(),
            'beat_index' => $event->getBeatIndex(),
            'original' => $event->getOriginalValue(),
            'override' => $event->getOverrideValue(),
            'effective' => $event->getEffectiveValue(),
            'payload' => $event->getPayload(),
        ], $timeline->findForSongAndType($song, SongTimelineEvent::TYPE_LYRIC));

        return $this->json([
            'song' => [
                'id' => $song->getId(),
                'title' => $song->getTitle(),
                'artist' => $song->getArtist(),
                'capo' => $song->getCapo(),
                'time_signature' => $song->getTimeSignature(),
            ],
            'beats' => $beats,
            'chords' => $chords,
            'lyrics' => $lyrics,
        ]);
    }

    #[Route('/{id}/display', name: 'app_live_display', requirements: ['id' => '\d+'], methods: ['GET'])]
    public function display(LiveRun $liveRun, EntityManagerInterface $em): Response
    {
        $this->requireDisplayForRun($liveRun, $em);

        return $this->render('live/display.html.twig', [
            'live_run' => $liveRun,
            'event' => $liveRun->getEvent(),
            'state_url' => $this->generateUrl('app_live_state', ['id' => $liveRun->getId()]),
            'song_url_template' => $this->generateUrl('app_live_song_data', [
                'id' => $liveRun->getId(),
                'songId' => 999999,
            ]),
        ]);
    }

    private function songBelongsToLivePlaylist(LiveRun $liveRun, int $songId, EntityManagerInterface $em): bool
    {
        $playlist = $liveRun->getEvent()->getPlaylist();
        if ($playlist === null) {
            return false;
        }

        return $em->getRepository(PlaylistItem::class)->createQueryBuilder('i')
            ->select('COUNT(i.id)')
            ->andWhere('i.playlist = :playlist')
            ->andWhere('IDENTITY(i.song) = :songId')
            ->setParameter('playlist', $playlist)
            ->setParameter('songId', $songId)
            ->getQuery()
            ->getSingleScalarResult() > 0;
    }

    private function displayMayJoin(LiveRun $liveRun, User $user, EntityManagerInterface $em): bool
    {
        if (!in_array('ROLE_DISPLAY', $user->getRoles(), true) || !$liveRun->isLive()) {
            return false;
        }

        $group = $liveRun->getEvent()->getGroup();
        if ($group === null) {
            return false;
        }

        return $em->getRepository(GroupMember::class)->findOneBy([
            'group' => $group,
            'user' => $user,
        ]) instanceof GroupMember;
    }

    private function requireDisplayForRun(LiveRun $liveRun, EntityManagerInterface $em): User
    {
        $user = $this->requireUser();
        if (!$this->displayMayJoin($liveRun, $user, $em)) {
            throw $this->createAccessDeniedException();
        }

        return $user;
    }

    private function requireUser(): User
    {
        $user = $this->getUser();
        if (!$user instanceof User) {
            throw $this->createAccessDeniedException();
        }

        return $user;
    }

    private function assertOwner(Event $event, User $user): void
    {
        if ($event->getCreatedBy()->getId() !== $user->getId()) {
            throw $this->createAccessDeniedException();
        }
    }
}
