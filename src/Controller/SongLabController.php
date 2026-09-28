<?php

declare(strict_types=1);

namespace App\Controller;

use App\Domain\Song\Song;
use App\Domain\Song\SongTimelineEvent;
use App\Domain\Song\SongTimelineEventRepository;
use App\Domain\Song\SongCollaboratorRepository;
use App\Domain\Song\UserSongStemMixRepository;
use App\Domain\User\User;
use App\Service\ChordTimelineAnalysisService;
use App\Service\SongChordJobService;
use App\Service\SongStemPlaybackStorage;
use App\Service\SongWorkflowState;
use App\Service\SongAccessPolicy;
use Doctrine\ORM\EntityManagerInterface;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;

#[Route('/song/{id}/lab', requirements: ['id' => '\d+'])]
final class SongLabController extends AbstractController
{
    public function __construct(private readonly SongAccessPolicy $songAccess) {}

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
    public function analysis(Song $song, SongWorkflowState $workflow, SongCollaboratorRepository $collaborators): Response
    {
        $this->requireEditor($song);
        return $this->render('song/analysis_dashboard.html.twig', ['song'=>$song,'workflow'=>$workflow->forSong($song),'collaborators'=>$collaborators->findForSong($song)]);
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
            'has_chord_overrides' => (bool) array_filter(
                $profiles[$activeProfile] ?? [],
                static fn (array $event): bool => ($event['override'] ?? null) !== null && trim((string) $event['override']) !== ''
            ),
        ]);
    }

    #[Route('/chords/analyze', name: 'app_song_chordslab_analyze', methods: ['POST'])]
    public function analyzeChords(
        Song $song,
        Request $request,
        SongChordJobService $chordJobs,
        SongWorkflowState $workflow,
        EntityManagerInterface $em,
    ): Response {
        $user = $this->requireEditor($song);

        if (!$this->isCsrfTokenValid(
            'song_chordslab_analyze_'.$song->getId(),
            (string) $request->request->get('_token'),
        )) {
            throw $this->createAccessDeniedException();
        }

        if (!$workflow->forSong($song)['can_chords']) {
            $this->addFlash('error','Les stems doivent être terminés avant l’analyse des accords.');
            return $this->redirectToRoute('app_song_analysis_lab',['_locale'=>$request->getLocale(),'id'=>$song->getId()]);
        }
        $filterNoise = $request->request->getBoolean('filter_noise');
        $song->setChordNoiseFilterEnabled($filterNoise);
        $em->flush();
        $chordJobs->queue($song, $user, $song->isChordNoiseFilterEnabled());

        return $this->redirectToRoute('app_song_chordslab', [
            '_locale' => $request->getLocale(),
            'id' => $song->getId(),
        ]);
    }

    #[Route('/chords/noise-filter', name: 'app_song_chordslab_noise_filter', methods: ['POST'])]
    public function saveChordNoiseFilter(Song $song, Request $request, EntityManagerInterface $em): JsonResponse
    {
        $this->requireEditor($song);
        $payload = $request->toArray();
        if (!$this->isCsrfTokenValid('song_chordslab_noise_filter_'.$song->getId(), (string) ($payload['_token'] ?? ''))) {
            return $this->json(['error' => 'invalid_csrf'], Response::HTTP_FORBIDDEN);
        }
        $song->setChordNoiseFilterEnabled((bool) ($payload['enabled'] ?? false));
        $em->flush();
        return $this->json(['ok' => true, 'enabled' => $song->isChordNoiseFilterEnabled()]);
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



    #[Route('/chords/profile/{profile}', name: 'app_song_chordslab_profile_data', methods: ['GET'])]
    public function chordProfileData(
        Song $song,
        string $profile,
        SongTimelineEventRepository $timeline,
    ): JsonResponse {
        $this->requireEditor($song);

        if (!in_array($profile, ['beginner', 'intermediate', 'expert'], true)) {
            return $this->json(['error' => 'invalid_profile'], Response::HTTP_UNPROCESSABLE_ENTITY);
        }

        $events = array_map(
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

        return $this->json([
            'profile' => $profile,
            'count' => count($events),
            'events' => $events,
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

        if ($request->getPreferredFormat() === 'json' || str_contains((string) $request->headers->get('Accept'), 'application/json')) {
            return $this->json([
                'ok' => true,
                'capo' => $song->getCapo(),
                'time_signature' => $song->getTimeSignature(),
                'profile' => $song->getChordAnalysisLevel(),
            ]);
        }

        $this->addFlash('success', 'chordslab.settings.saved');

        return $this->redirectToRoute('app_song_chordslab', [
            '_locale' => $request->getLocale(),
            'id' => $song->getId(),
        ]);
    }

    #[Route('/chords/beat/{beatId}', name: 'app_song_chordslab_beat_override', requirements: ['beatId' => '\d+'], methods: ['POST'])]
    public function saveChordAtBeat(
        Song $song,
        int $beatId,
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

        $profile = trim((string) ($payload['profile'] ?? $song->getChordAnalysisLevel()));
        if (!in_array($profile, ['beginner', 'intermediate', 'expert'], true)) {
            return $this->json(['error' => 'invalid_profile'], Response::HTTP_UNPROCESSABLE_ENTITY);
        }

        $beat = $timeline->find($beatId);
        if (!$beat instanceof SongTimelineEvent
            || $beat->getSong()->getId() !== $song->getId()
            || $beat->getEventType() !== SongTimelineEvent::TYPE_BEAT) {
            return $this->json(['error' => 'beat_not_found'], Response::HTTP_NOT_FOUND);
        }

        $chord = trim((string) ($payload['chord'] ?? ''));
        $chord = preg_replace('/^\\[([^\\]]+)\\]$/', '$1', $chord) ?? $chord;
        $chord = preg_replace('/^([A-G](?:#|b)?)maj$/', '$1', $chord) ?? $chord;

        if ($chord === '-') {
            return $this->json(['error' => 'continuation_is_display_only'], Response::HTTP_UNPROCESSABLE_ENTITY);
        }
        if ($chord !== '.'
            && ($chord === '' || mb_strlen($chord) > 32
                || !preg_match('/^[A-G](?:#|b)?[A-Za-z0-9()+#b°øΔ\\/-]*$/u', $chord))) {
            return $this->json(['error' => 'invalid_chord'], Response::HTTP_UNPROCESSABLE_ENTITY);
        }

        $event = null;
        foreach ($timeline->findChordEventsForProfile($song, $profile) as $candidate) {
            if ($candidate->getStartMs() === $beat->getStartMs()) {
                $event = $candidate;
                break;
            }
        }

        if (!$event instanceof SongTimelineEvent) {
            $event = (new SongTimelineEvent($song, SongTimelineEvent::TYPE_CHORD, $beat->getStartMs()))
                ->setPosition($beat->getMeasureIndex(), $beat->getBeatIndex(), $beat->getSubdivisionIndex())
                ->setOriginalValue('.')
                ->setPayload([
                    'confidence' => 0.0,
                    'profile' => $profile,
                    'analysis_level' => $profile,
                    'analysis_version' => 'manual-beat-r35.9',
                ]);
            $em->persist($event);
        }

        if ($chord === '.') {
            $event->resetOverride();
        } else {
            $event->setOverrideValue($chord);
        }
        $em->flush();

        return $this->json([
            'ok' => true,
            'id' => $event->getId(),
            'start_ms' => $event->getStartMs(),
            'measure_index' => $event->getMeasureIndex(),
            'beat_index' => $event->getBeatIndex(),
            'original' => $event->getOriginalValue(),
            'override' => $event->getOverrideValue(),
            'effective' => $event->getEffectiveValue(),
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
        $chord = preg_replace('/^\[([^\]]+)\]$/', '$1', $chord) ?? $chord;
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
public function lyrics(
    Song $song,
    SongWorkflowState $workflow,
    Request $request,
    SongTimelineEventRepository $timeline,
    UserSongStemMixRepository $mixes,
    SongStemPlaybackStorage $playback,
): Response {
    $user=$this->requireEditor($song);
    if (!$workflow->forSong($song)['can_lyrics']) {
        $this->addFlash('error','Les accords doivent être terminés avant les paroles.');
        return $this->redirectToRoute('app_song_analysis_lab',['_locale'=>$request->getLocale(),'id'=>$song->getId()]);
    }

    $chords=array_map(static fn(SongTimelineEvent $event):array=>[
        'id'=>$event->getId(),'start_ms'=>$event->getStartMs(),'end_ms'=>$event->getEndMs(),
        'measure_index'=>$event->getMeasureIndex(),'beat_index'=>$event->getBeatIndex(),
        'original'=>$event->getOriginalValue(),'override'=>$event->getOverrideValue(),'effective'=>$event->getEffectiveValue(),
    ],$timeline->findChordEventsForProfile($song,$song->getChordAnalysisLevel()));

    $lyrics=array_map(static fn(SongTimelineEvent $event):array=>[
        'id'=>$event->getId(),'start_ms'=>$event->getStartMs(),'end_ms'=>$event->getEndMs(),
        'measure_index'=>$event->getMeasureIndex(),'beat_index'=>$event->getBeatIndex(),
        'original'=>$event->getOriginalValue(),'override'=>$event->getOverrideValue(),'effective'=>$event->getEffectiveValue(),
        'payload'=>$event->getPayload(),
    ],$timeline->findForSongAndType($song,SongTimelineEvent::TYPE_LYRIC));

    return $this->render('song/lyricslab.html.twig',[
        'song'=>$song,
        'beat_events'=>array_map(static fn(SongTimelineEvent $event):array=>[
            'id'=>$event->getId(),'start_ms'=>$event->getStartMs(),'measure_index'=>$event->getMeasureIndex(),'beat_index'=>$event->getBeatIndex(),
        ],$timeline->findBeatEvents($song)),
        'chord_events'=>$chords,'lyric_events'=>$lyrics,
        'stem_mix_settings'=>$mixes->findForUserAndSong($user,$song)?->getSettings()??[],
        'playback_ready'=>$playback->isReady($song),
    ]);
}

#[Route('/lyrics/source', name: 'app_song_lyricslab_source', methods: ['POST'])]
public function saveLyricsSource(Song $song,Request $request,EntityManagerInterface $em): JsonResponse
{
    $this->requireEditor($song);$payload=$request->toArray();
    if(!$this->isCsrfTokenValid('song_lyricslab_source_'.$song->getId(),(string)($payload['_token']??'')))return $this->json(['error'=>'invalid_csrf'],Response::HTTP_FORBIDDEN);
    $song->setLyricsSourceText((string)($payload['text']??''));$em->flush();return $this->json(['ok'=>true]);
}

#[Route('/lyrics/analyze', name: 'app_song_lyricslab_analyze', methods: ['POST'])]
public function analyzeLyrics(
    Song $song,
    Request $request,
    \App\Service\SongLyricsJobService $jobs,
    EntityManagerInterface $em,
): Response
{
    $user=$this->requireEditor($song);
    $postedText = (string) $request->request->get('lyrics_source', '');
    if ($postedText !== '') {
        $song->setLyricsSourceText($postedText);
        $em->flush();
    }
    if(!$this->isCsrfTokenValid('song_lyricslab_analyze_'.$song->getId(),(string)$request->request->get('_token')))throw $this->createAccessDeniedException();
    if(trim((string)$song->getLyricsSourceText())===''){
        $this->addFlash('error','Collez les paroles avant de lancer l’analyse.');
        return $this->redirectToRoute('app_song_lyricslab',['_locale'=>$request->getLocale(),'id'=>$song->getId()]);
    }
    $jobs->queue($song,$user,'align');
    return $this->redirectToRoute('app_song_lyricslab',['_locale'=>$request->getLocale(),'id'=>$song->getId()]);
}


#[Route('/lyrics/extract', name: 'app_song_lyricslab_extract', methods: ['POST'])]
public function extractLyrics(
    Song $song,
    Request $request,
    \App\Service\SongLyricsJobService $jobs,
    \App\Service\LyricsSourceHistoryService $lyricsHistory,
): Response {
    $user = $this->requireEditor($song);

    if (!$this->isCsrfTokenValid(
        'song_lyricslab_extract_'.$song->getId(),
        (string) $request->request->get('_token'),
    )) {
        throw $this->createAccessDeniedException();
    }

    $lyricsHistory->archiveCurrentIfChanged(
        $song,
        $user,
        'manual',
        'Sauvegarde automatique avant extraction Whisper.',
    );

    $jobs->queue($song, $user, 'extract');

    return $this->redirectToRoute('app_song_lyricslab', [
        '_locale' => $request->getLocale(),
        'id' => $song->getId(),
    ]);
}

#[Route('/lyrics/status', name: 'app_song_lyricslab_status', methods: ['GET'])]
public function lyricsStatus(Song $song,\App\Service\SongLyricsJobService $jobs): JsonResponse
{
    $this->requireEditor($song);$job=$jobs->latest($song);
    if(!$job)return $this->json(['status'=>'none','progress'=>0]);
    return $this->json(['job_id'=>$job->getId(),'status'=>$job->getStatus()->value,'progress'=>$job->getProgress(),'error'=>$job->getErrorCode(),'mode'=>(string)($job->getRequestData()['mode']??'align')]);
}

#[Route('/lyrics/word/{eventId}', name: 'app_song_lyricslab_word', requirements: ['eventId'=>'\\d+'], methods: ['POST'])]
public function saveLyricsWord(Song $song,int $eventId,Request $request,SongTimelineEventRepository $timeline,EntityManagerInterface $em): JsonResponse
{
    $this->requireEditor($song);$payload=$request->toArray();
    if(!$this->isCsrfTokenValid('song_lyricslab_word_'.$song->getId(),(string)($payload['_token']??'')))return $this->json(['error'=>'invalid_csrf'],Response::HTTP_FORBIDDEN);
    $event=$timeline->find($eventId);
    if(!$event instanceof SongTimelineEvent||$event->getSong()->getId()!==$song->getId()||$event->getEventType()!==SongTimelineEvent::TYPE_LYRIC)return $this->json(['error'=>'not_found'],Response::HTTP_NOT_FOUND);
    $text=trim((string)($payload['text']??''));
    if($text===''||mb_strlen($text)>80)return $this->json(['error'=>'invalid_text'],Response::HTTP_UNPROCESSABLE_ENTITY);
    $event->setOverrideValue($text);$em->flush();
    return $this->json(['ok'=>true,'override'=>$event->getOverrideValue(),'effective'=>$event->getEffectiveValue()]);
}

    #[Route('/publication', name: 'app_song_publication_lab', methods: ['GET'])]
    public function publication(Song $song, SongWorkflowState $workflow, Request $request): Response
    {
        $this->requireEditor($song);
        if (!$workflow->forSong($song)['can_publish']) {
            $this->addFlash('error','Les paroles doivent être terminées avant la publication.');
            return $this->redirectToRoute('app_song_analysis_lab',['_locale'=>$request->getLocale(),'id'=>$song->getId()]);
        }
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
        $user=$this->getUser();
        if(!$user instanceof User || !$this->songAccess->canEdit($song,$user,$this->isGranted('ROLE_ADMIN'))) throw $this->createAccessDeniedException();
        return $user;
    }
}
