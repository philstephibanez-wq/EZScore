<?php
declare(strict_types=1);

namespace App\Controller;

use App\Domain\Event\Event;
use App\Domain\Playlist\PlaylistItem;
use App\Domain\Song\Song;
use App\Domain\Song\SongTimelineEvent;
use App\Domain\Song\SongTimelineEventRepository;
use App\Domain\Song\UserSongStemMix;
use App\Domain\Song\UserSongStemMixRepository;
use App\Domain\User\User;
use App\Security\Acl\AclPrivilege;
use App\Service\SongStemPlaybackStorage;
use Doctrine\ORM\EntityManagerInterface;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;
use Symfony\Component\Security\Csrf\CsrfTokenManagerInterface;

final class KaraokeController extends AbstractController
{
    private const TIME_SIGNATURES = [
        'auto','2/2','2/4','3/2','3/4','3/8','4/2','4/4','4/8','5/4','5/8',
        '6/4','6/8','7/4','7/8','8/8','9/8','10/8','11/8','12/8','12/16',
        '13/8','13/16','14/8','15/8','15/16','16/8',
    ];

    public function __construct(private readonly CsrfTokenManagerInterface $csrf) {}

    #[Route('/song/{id}/karaoke', name: 'app_song_karaoke', requirements: ['id' => '\d+'], methods: ['GET'])]
    public function song(
        Song $song,
        SongTimelineEventRepository $timeline,
        UserSongStemMixRepository $mixes,
        SongStemPlaybackStorage $playback,
    ): Response {
        $this->denyAccessUnlessGranted(AclPrivilege::SONG_EDIT, $song);
        $user = $this->requireUser();

        return $this->renderKaraoke(
            song: $song,
            event: null,
            timeline: $timeline,
            mixes: $mixes,
            playback: $playback,
            user: $user,
            mixSaveUrl: $this->generateUrl('app_song_stems_mix', ['id' => $song->getId()]),
            audioUrlTemplate: $this->generateUrl('app_song_stems_playback_audio', ['id' => $song->getId(), 'name' => '__TRACK__']),
            canConduct: true,
            settingsAction: $this->generateUrl('app_song_chordslab_settings', ['id' => $song->getId()]),
            settingsToken: (string) $this->csrf->getToken('song_chordslab_settings_'.$song->getId()),
            profileSaveUrl: $this->generateUrl('app_song_chordslab_profile', ['id' => $song->getId()]),
            profileDataUrlTemplate: $this->generateUrl('app_song_chordslab_profile_data', ['id' => $song->getId(), 'profile' => '__PROFILE__']),
            profileToken: (string) $this->csrf->getToken('song_chordslab_profile_'.$song->getId()),
        );
    }

    #[Route('/events/{eventId}/karaoke/{songId}', name: 'app_event_karaoke', requirements: ['eventId' => '\d+', 'songId' => '\d+'], methods: ['GET'])]
    public function sessionSong(
        int $eventId,
        int $songId,
        EntityManagerInterface $em,
        SongTimelineEventRepository $timeline,
        UserSongStemMixRepository $mixes,
        SongStemPlaybackStorage $playback,
    ): Response {
        $event = $em->getRepository(Event::class)->find($eventId);
        $song = $em->getRepository(Song::class)->find($songId);
        if (!$event instanceof Event || !$song instanceof Song) {
            throw $this->createNotFoundException();
        }

        $this->denyAccessUnlessGranted(AclPrivilege::EVENT_VIEW, $event);
        $this->assertSongInSessionPlaylist($event, $song, $em);

        $user = $this->requireUser();
        $canConduct = $event->getCreatedBy()->getId() === $user->getId();

        return $this->renderKaraoke(
            song: $song,
            event: $event,
            timeline: $timeline,
            mixes: $mixes,
            playback: $playback,
            user: $user,
            mixSaveUrl: $this->generateUrl('app_event_karaoke_mix', ['eventId' => $eventId, 'songId' => $songId]),
            audioUrlTemplate: $this->generateUrl('app_song_stems_playback_audio', ['id' => $song->getId(), 'name' => '__TRACK__']),
            canConduct: $canConduct,
            settingsAction: $this->generateUrl('app_event_karaoke_settings', ['eventId' => $eventId, 'songId' => $songId]),
            settingsToken: (string) $this->csrf->getToken('karaoke_settings_'.$eventId.'_'.$songId),
            profileSaveUrl: $this->generateUrl('app_event_karaoke_profile', ['eventId' => $eventId, 'songId' => $songId]),
            profileDataUrlTemplate: $this->generateUrl('app_event_karaoke_profile_data', ['eventId' => $eventId, 'songId' => $songId, 'profile' => '__PROFILE__']),
            profileToken: (string) $this->csrf->getToken('karaoke_profile_'.$eventId.'_'.$songId),
            sessionNavigation: $this->sessionNavigation($event, $song, $em),
        );
    }

    #[Route('/events/{eventId}/karaoke/{songId}/settings', name: 'app_event_karaoke_settings', requirements: ['eventId' => '\d+', 'songId' => '\d+'], methods: ['POST'])]
    public function saveSessionSettings(
        int $eventId,
        int $songId,
        Request $request,
        EntityManagerInterface $em,
    ): JsonResponse {
        [$event, $song, $user] = $this->requireSessionSong($eventId, $songId, $em);
        $this->assertConductor($event, $user);

        if (!$this->isCsrfTokenValid(
            'karaoke_settings_'.$eventId.'_'.$songId,
            (string) $request->request->get('_token'),
        )) {
            throw $this->createAccessDeniedException();
        }

        $capo = (int) $request->request->get('capo', $song->getCapo());
        $signature = trim((string) $request->request->get('time_signature', $song->getTimeSignature()));
        $profile = trim((string) $request->request->get('chord_analysis_level', $song->getChordAnalysisLevel()));

        try {
            $song->setCapo($capo)->setTimeSignature($signature)->setChordAnalysisLevel($profile);
        } catch (\InvalidArgumentException) {
            return $this->json(['error' => 'invalid_settings'], Response::HTTP_UNPROCESSABLE_ENTITY);
        }

        $em->flush();

        return $this->json([
            'ok' => true,
            'capo' => $song->getCapo(),
            'time_signature' => $song->getTimeSignature(),
            'profile' => $song->getChordAnalysisLevel(),
        ]);
    }

    #[Route('/events/{eventId}/karaoke/{songId}/profile', name: 'app_event_karaoke_profile', requirements: ['eventId' => '\d+', 'songId' => '\d+'], methods: ['POST'])]
    public function saveSessionProfile(
        int $eventId,
        int $songId,
        Request $request,
        EntityManagerInterface $em,
    ): JsonResponse {
        [$event, $song, $user] = $this->requireSessionSong($eventId, $songId, $em);
        $this->assertConductor($event, $user);

        $payload = $request->toArray();
        if (!$this->isCsrfTokenValid(
            'karaoke_profile_'.$eventId.'_'.$songId,
            (string) ($payload['_token'] ?? ''),
        )) {
            throw $this->createAccessDeniedException();
        }

        $profile = trim((string) ($payload['profile'] ?? ''));
        if (!in_array($profile, ['beginner', 'intermediate', 'expert'], true)) {
            return $this->json(['error' => 'invalid_profile'], Response::HTTP_UNPROCESSABLE_ENTITY);
        }

        $song->setChordAnalysisLevel($profile);
        $em->flush();

        return $this->json(['ok' => true, 'profile' => $profile]);
    }

    #[Route('/events/{eventId}/karaoke/{songId}/profile/{profile}', name: 'app_event_karaoke_profile_data', requirements: ['eventId' => '\d+', 'songId' => '\d+', 'profile' => 'beginner|intermediate|expert'], methods: ['GET'])]
    public function sessionProfileData(
        int $eventId,
        int $songId,
        string $profile,
        EntityManagerInterface $em,
        SongTimelineEventRepository $timeline,
    ): JsonResponse {
        [, $song] = $this->requireSessionSong($eventId, $songId, $em);

        return $this->json([
            'profile' => $profile,
            'events' => $this->chordEvents($song, $timeline, $profile),
        ]);
    }

    #[Route('/events/{eventId}/karaoke/{songId}/mix', name: 'app_event_karaoke_mix', requirements: ['eventId' => '\d+', 'songId' => '\d+'], methods: ['POST'])]
    public function saveSessionMix(
        int $eventId,
        int $songId,
        Request $request,
        EntityManagerInterface $em,
        UserSongStemMixRepository $mixes,
    ): JsonResponse {
        [$event, $song, $user] = $this->requireSessionSong($eventId, $songId, $em);
        $this->assertConductor($event, $user);

        $payload = $request->toArray();
        if (!$this->isCsrfTokenValid(
            'karaoke_mix_'.$event->getId().'_'.$song->getId(),
            (string) ($payload['_token'] ?? ''),
        )) {
            return $this->json(['error' => 'invalid_csrf'], Response::HTTP_FORBIDDEN);
        }

        $settings = $payload['settings'] ?? null;
        if (!is_array($settings)) {
            return $this->json(['error' => 'invalid_settings'], Response::HTTP_UNPROCESSABLE_ENTITY);
        }

        $mix = $mixes->findForUserAndSong($user, $song) ?? new UserSongStemMix($user, $song);
        $mix->setSettings($this->sanitizeMixSettings($settings));
        $em->persist($mix);
        $em->flush();

        return $this->json([
            'ok' => true,
            'settings' => $mix->getSettings(),
            'updated_at' => $mix->getUpdatedAt()->format(DATE_ATOM),
        ]);
    }

    #[Route('/events/{eventId}/karaoke/{songId}/audio/{name}', name: 'app_event_karaoke_audio', requirements: ['eventId' => '\d+', 'songId' => '\d+'], methods: ['GET'])]
    public function sessionAudio(
        int $eventId,
        int $songId,
        string $name,
        EntityManagerInterface $em,
        SongStemPlaybackStorage $playback,
    ): Response {
        [, $song] = $this->requireSessionSong($eventId, $songId, $em);

        $mediaPath = $playback->mediaRelativePath($song, $name);
        if ($mediaPath === null) {
            throw $this->createNotFoundException();
        }

        return $this->redirect('/media/'.$mediaPath, Response::HTTP_FOUND);
    }

    /**
     * Source de vérité unique du Karaoké pour un Song.
     * Solo et Session consomment STRICTEMENT ce même contexte.
     * La Session n'ajoute ensuite que autorité/navigation/synchronisation.
     *
     * @return array<string,mixed>
     */
    private function canonicalKaraokeSongContext(
        Song $song,
        SongTimelineEventRepository $timeline,
        UserSongStemMixRepository $mixes,
        SongStemPlaybackStorage $playback,
        User $user,
    ): array {
        return [
            'song' => $song,
            'beat_events' => $this->beatEvents($song, $timeline),
            'chord_events' => $this->chordEvents($song, $timeline, $song->getChordAnalysisLevel()),
            'lyric_events' => $this->lyricEvents($song, $timeline),
            'time_signatures' => self::TIME_SIGNATURES,
            'stem_mix_settings' => $mixes->findForUserAndSong($user, $song)?->getSettings() ?? [],
            'playback_ready' => $playback->isReady($song),
            'canonical_audio_url_template' => $this->generateUrl(
                'app_song_stems_playback_audio',
                ['id' => $song->getId(), 'name' => '__TRACK__'],
            ),
        ];
    }
    private function renderKaraoke(
        Song $song,
        ?Event $event,
        SongTimelineEventRepository $timeline,
        UserSongStemMixRepository $mixes,
        SongStemPlaybackStorage $playback,
        User $user,
        string $mixSaveUrl,
        string $audioUrlTemplate,
        bool $canConduct,
        string $settingsAction,
        string $settingsToken,
        string $profileSaveUrl,
        string $profileDataUrlTemplate,
        string $profileToken,
        array $sessionNavigation = [],
    ): Response {
        $canonical = $this->canonicalKaraokeSongContext($song, $timeline, $mixes, $playback, $user);

        return $this->render('song/karaoke.html.twig', array_merge($canonical, [
            'session_event' => $event,
            'session_navigation' => $sessionNavigation,
            'can_conduct' => $canConduct,
            'mix_save_url' => $mixSaveUrl,
            'mix_token' => (string) ($event
                ? $this->csrf->getToken('karaoke_mix_'.$event->getId().'_'.$song->getId())
                : $this->csrf->getToken('song_stems_mix_'.$song->getId())),
            // R1.C13: always the same media source as solo. Session does not own audio storage.
            'audio_url_template' => $canonical['canonical_audio_url_template'],
            'settings_action' => $settingsAction,
            'settings_token' => $settingsToken,
            'profile_save_url' => $profileSaveUrl,
            'profile_data_url_template' => $profileDataUrlTemplate,
            'profile_token' => $profileToken,
        ]));
    }

    /** @return list<array<string,mixed>> */
    private function chordEvents(Song $song, SongTimelineEventRepository $timeline, string $profile): array
    {
        return array_map(static fn(SongTimelineEvent $item): array => [
            'id' => $item->getId(),
            'start_ms' => $item->getStartMs(),
            'end_ms' => $item->getEndMs(),
            'measure_index' => $item->getMeasureIndex(),
            'beat_index' => $item->getBeatIndex(),
            'subdivision_index' => $item->getSubdivisionIndex(),
            'original' => $item->getOriginalValue(),
            'override' => $item->getOverrideValue(),
            'effective' => $item->getEffectiveValue(),
        ], $timeline->findChordEventsForProfile($song, $profile));
    }

    /** @return list<array<string,mixed>> */
    private function lyricEvents(Song $song, SongTimelineEventRepository $timeline): array
    {
        return array_map(static fn(SongTimelineEvent $item): array => [
            'id' => $item->getId(),
            'start_ms' => $item->getStartMs(),
            'end_ms' => $item->getEndMs(),
            'measure_index' => $item->getMeasureIndex(),
            'beat_index' => $item->getBeatIndex(),
            'subdivision_index' => $item->getSubdivisionIndex(),
            'original' => $item->getOriginalValue(),
            'override' => $item->getOverrideValue(),
            'effective' => $item->getEffectiveValue(),
            'payload' => $item->getPayload(),
        ], $timeline->findForSongAndType($song, SongTimelineEvent::TYPE_LYRIC));
    }

    /** @return list<array<string,mixed>> */
    private function beatEvents(Song $song, SongTimelineEventRepository $timeline): array
    {
        return array_map(static fn(SongTimelineEvent $item): array => [
            'id' => $item->getId(),
            'start_ms' => $item->getStartMs(),
            'measure_index' => $item->getMeasureIndex(),
            'beat_index' => $item->getBeatIndex(),
            'subdivision_index' => $item->getSubdivisionIndex(),
        ], $timeline->findBeatEvents($song));
    }

    /** @return array{index:int,count:int,previous:?int,next:?int} */
    private function sessionNavigation(Event $event, Song $song, EntityManagerInterface $em): array
    {
        $playlist = $event->getPlaylist();
        if ($playlist === null) {
            return ['index' => 1, 'count' => 1, 'previous' => null, 'next' => null];
        }

        $items = $em->getRepository(PlaylistItem::class)->findBy(
            ['playlist' => $playlist],
            ['position' => 'ASC', 'id' => 'ASC'],
        );

        $songIds = [];
        foreach ($items as $item) {
            if ($item instanceof PlaylistItem && $item->getSong()->getId() !== null) {
                $songIds[] = (int) $item->getSong()->getId();
            }
        }

        $position = array_search((int) $song->getId(), $songIds, true);
        if ($position === false) {
            return ['index' => 1, 'count' => max(1, count($songIds)), 'previous' => null, 'next' => null];
        }

        return [
            'index' => $position + 1,
            'count' => count($songIds),
            'previous' => $position > 0 ? $songIds[$position - 1] : null,
            'next' => $position + 1 < count($songIds) ? $songIds[$position + 1] : null,
        ];
    }

    /** @return array{0:Event,1:Song,2:User} */
    private function requireSessionSong(int $eventId, int $songId, EntityManagerInterface $em): array
    {
        $event = $em->getRepository(Event::class)->find($eventId);
        $song = $em->getRepository(Song::class)->find($songId);
        if (!$event instanceof Event || !$song instanceof Song) {
            throw $this->createNotFoundException();
        }

        $this->denyAccessUnlessGranted(AclPrivilege::EVENT_VIEW, $event);
        $this->assertSongInSessionPlaylist($event, $song, $em);

        return [$event, $song, $this->requireUser()];
    }

    private function assertConductor(Event $event, User $user): void
    {
        if ($event->getCreatedBy()->getId() !== $user->getId()) {
            throw $this->createAccessDeniedException();
        }
    }

    private function assertSongInSessionPlaylist(Event $event, Song $song, EntityManagerInterface $em): void
    {
        $playlist = $event->getPlaylist();
        if ($playlist === null) {
            throw $this->createAccessDeniedException();
        }

        $item = $em->getRepository(PlaylistItem::class)->findOneBy([
            'playlist' => $playlist,
            'song' => $song,
        ]);

        if (!$item instanceof PlaylistItem) {
            throw $this->createAccessDeniedException();
        }
    }

    private function requireUser(): User
    {
        $user = $this->getUser();
        if (!$user instanceof User) {
            throw $this->createAccessDeniedException();
        }

        return $user;
    }

    /** @param array<string,mixed> $settings */
    private function sanitizeMixSettings(array $settings): array
    {
        $allowedTracks = ['original','lead_vocals','backing_vocals','drums','bass','guitar','piano','other'];
        $tracks = [];
        $rawTracks = is_array($settings['tracks'] ?? null) ? $settings['tracks'] : [];
        foreach ($allowedTracks as $track) {
            $raw = is_array($rawTracks[$track] ?? null) ? $rawTracks[$track] : [];
            $tracks[$track] = [
                'enabled' => (bool) ($raw['enabled'] ?? ($track === 'original')),
                'volume' => $this->clamp($raw['volume'] ?? ($track === 'original' ? 1.0 : 0.72), 0.0, 1.25),
            ];
        }

        $eq = is_array($settings['master_eq'] ?? null) ? $settings['master_eq'] : [];

        return [
            'schema_version' => 'ezscore.stem_mix.v2',
            'master_volume' => $this->clamp($settings['master_volume'] ?? 1.0, 0.0, 1.25),
            'playback_rate' => $this->clamp($settings['playback_rate'] ?? 1.0, 0.75, 1.25),
            'master_eq' => [
                'low' => $this->clamp($eq['low'] ?? 0.0, -12.0, 12.0),
                'mid' => $this->clamp($eq['mid'] ?? 0.0, -12.0, 12.0),
                'high' => $this->clamp($eq['high'] ?? 0.0, -12.0, 12.0),
            ],
            'master_compression' => $this->clamp($settings['master_compression'] ?? 0.0, 0.0, 100.0),
            'tracks' => $tracks,
        ];
    }

    private function clamp(mixed $value, float $min, float $max): float
    {
        $number = is_numeric($value) ? (float) $value : $min;
        return max($min, min($max, $number));
    }
}
