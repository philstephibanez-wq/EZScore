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
use Symfony\Component\Routing\Attribute\Route;

#[Route('/live')]
final class LiveRunKaraokeSyncController extends AbstractController
{
    #[Route('/events/{eventId}/karaoke-state', name: 'app_live_karaoke_state_update', requirements: ['eventId' => '\d+'], methods: ['POST'])]
    public function update(
        int $eventId,
        Request $request,
        EntityManagerInterface $em,
    ): JsonResponse {
        $event = $em->getRepository(Event::class)->find($eventId);
        if (!$event instanceof Event) {
            throw $this->createNotFoundException();
        }

        $user = $this->requireUser();
        if ($event->getCreatedBy()->getId() !== $user->getId()) {
            throw $this->createAccessDeniedException();
        }

        $payload = $request->toArray();
        if (!$this->isCsrfTokenValid(
            'live_karaoke_state_'.$event->getId(),
            (string) ($payload['_token'] ?? ''),
        )) {
            throw $this->createAccessDeniedException();
        }

        $liveRun = $em->getRepository(LiveRun::class)->findOneBy([
            'event' => $event,
            'status' => 'live',
        ]);
        if (!$liveRun instanceof LiveRun) {
            return $this->json(['ok' => false, 'error' => 'no_active_live_run'], 409);
        }

        $songId = (int) ($payload['song_id'] ?? 0);
        $song = $em->getRepository(Song::class)->find($songId);
        if (!$song instanceof Song || !$this->songBelongsToEvent($event, $song, $em)) {
            return $this->json(['ok' => false, 'error' => 'song_not_in_session_playlist'], 422);
        }

        $playing = (bool) ($payload['playing'] ?? false);
        $positionMs = max(0, (int) ($payload['position_ms'] ?? 0));
        $playbackRate = max(0.50, min(2.00, (float) ($payload['playback_rate'] ?? 1.0)));
        $countdownSeconds = max(0, min(30, (int) ($payload['countdown_seconds'] ?? 0)));
        $diagramEnabled = (bool) ($payload['diagram_enabled'] ?? false);

        if ($countdownSeconds > 0) {
            $liveRun->startKaraokeCountdown($songId, $countdownSeconds, $playbackRate, $diagramEnabled);
        } else {
            $liveRun->updateKaraokeTransport($songId, $playing, $positionMs, $playbackRate, $diagramEnabled);
        }
        $em->flush();

        return $this->json([
            'ok' => true,
            'revision' => $liveRun->getRevision(),
            'song_id' => $liveRun->getKaraokeCurrentSongId(),
        ]);
    }

    #[Route('/{id}/karaoke-state', name: 'app_live_karaoke_state_read', requirements: ['id' => '\d+'], methods: ['GET'])]
    public function state(
        LiveRun $liveRun,
        EntityManagerInterface $em,
    ): JsonResponse {
        $this->assertViewer($liveRun, $em);

        return $this->json([
            'active' => $liveRun->isLive(),
            'revision' => $liveRun->getRevision(),
            'song_id' => $liveRun->getKaraokeCurrentSongId(),
            'playing' => $liveRun->isKaraokePlaying(),
            'position_ms' => $liveRun->getKaraokePositionMs(),
            'playback_rate' => $liveRun->getKaraokePlaybackRate(),
            'updated_at' => $liveRun->getKaraokeStateUpdatedAt()?->format(DATE_ATOM),
            'state_updated_at_ms' => $liveRun->getKaraokeStateUpdatedAtMs(),
            'server_now_ms' => (int) round(microtime(true) * 1000),
            'diagram_enabled' => $liveRun->isKaraokeDiagramEnabled(),
            'countdown_ends_at' => $liveRun->getKaraokeCountdownEndsAt()?->format(DATE_ATOM),
            'countdown_total_seconds' => $liveRun->getKaraokeCountdownTotalSeconds(),
        ]);
    }

    #[Route('/{id}/karaoke-song/{songId}', name: 'app_live_karaoke_song_data', requirements: ['id' => '\d+', 'songId' => '\d+'], methods: ['GET'])]
    public function songData(
        LiveRun $liveRun,
        int $songId,
        EntityManagerInterface $em,
        SongTimelineEventRepository $timeline,
    ): JsonResponse {
        $this->assertViewer($liveRun, $em);

        $song = $em->getRepository(Song::class)->find($songId);
        if (!$song instanceof Song || !$this->songBelongsToEvent($liveRun->getEvent(), $song, $em)) {
            throw $this->createAccessDeniedException();
        }

        $chords = array_map(static fn(SongTimelineEvent $item): array => [
            'id' => $item->getId(),
            'start_ms' => $item->getStartMs(),
            'end_ms' => $item->getEndMs(),
            'measure_index' => $item->getMeasureIndex(),
            'beat_index' => $item->getBeatIndex(),
            'original' => $item->getOriginalValue(),
            'override' => $item->getOverrideValue(),
            'effective' => $item->getEffectiveValue(),
        ], $timeline->findChordEventsForProfile($song, $song->getChordAnalysisLevel()));

        $lyrics = array_map(static fn(SongTimelineEvent $item): array => [
            'id' => $item->getId(),
            'start_ms' => $item->getStartMs(),
            'end_ms' => $item->getEndMs(),
            'measure_index' => $item->getMeasureIndex(),
            'beat_index' => $item->getBeatIndex(),
            'original' => $item->getOriginalValue(),
            'override' => $item->getOverrideValue(),
            'effective' => $item->getEffectiveValue(),
            'payload' => $item->getPayload(),
        ], $timeline->findForSongAndType($song, SongTimelineEvent::TYPE_LYRIC));

        $beats = array_map(static fn(SongTimelineEvent $item): array => [
            'id' => $item->getId(),
            'start_ms' => $item->getStartMs(),
            'measure_index' => $item->getMeasureIndex(),
            'beat_index' => $item->getBeatIndex(),
            'subdivision_index' => $item->getSubdivisionIndex(),
        ], $timeline->findBeatEvents($song));

        return $this->json([
            'id' => $song->getId(),
            'title' => $song->getTitle(),
            'artist' => $song->getArtist(),
            'capo' => $song->getCapo(),
            'time_signature' => $song->getTimeSignature(),
            'chord_profile' => $song->getChordAnalysisLevel(),
            'beats' => $beats,
            'chords' => $chords,
            'lyrics' => $lyrics,
        ]);
    }

    private function assertViewer(LiveRun $liveRun, EntityManagerInterface $em): void
    {
        $user = $this->requireUser();

        if ($liveRun->getConductor()->getId() === $user->getId()) {
            return;
        }

        if (!in_array('ROLE_DISPLAY', $user->getRoles(), true)) {
            throw $this->createAccessDeniedException();
        }

        $group = $liveRun->getEvent()->getGroup();
        if ($group === null) {
            throw $this->createAccessDeniedException();
        }

        $membership = $em->getRepository(GroupMember::class)->findOneBy([
            'group' => $group,
            'user' => $user,
        ]);

        if (!$membership instanceof GroupMember) {
            throw $this->createAccessDeniedException();
        }
    }

    private function songBelongsToEvent(Event $event, Song $song, EntityManagerInterface $em): bool
    {
        $playlist = $event->getPlaylist();
        if ($playlist === null) {
            return false;
        }

        return $em->getRepository(PlaylistItem::class)->findOneBy([
            'playlist' => $playlist,
            'song' => $song,
        ]) instanceof PlaylistItem;
    }

    private function requireUser(): User
    {
        $user = $this->getUser();
        if (!$user instanceof User) {
            throw $this->createAccessDeniedException();
        }

        return $user;
    }
}
