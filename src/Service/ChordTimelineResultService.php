<?php

declare(strict_types=1);

namespace App\Service;

use App\Domain\Song\Song;
use App\Domain\Song\SongTimelineEvent;
use App\Domain\Song\SongTimelineEventRepository;
use Doctrine\ORM\EntityManagerInterface;

final class ChordTimelineResultService
{
    public const PROFILES = ['beginner', 'intermediate', 'expert'];

    public function __construct(
        private readonly SongTimelineEventRepository $timeline,
        private readonly EntityManagerInterface $em,
    ) {}

    public function apply(Song $song, array $result): array
    {
        // R35.8a: fresh harmonic analysis is authoritative; old manual overrides are discarded.
        $this->timeline->deleteMusicalAnalysisForSong($song);

        // Beats are canonical and shared by all chord profiles.
        foreach (($result['beats'] ?? []) as $beat) {
            if (!is_array($beat)) continue;

            $event = (new SongTimelineEvent(
                $song,
                SongTimelineEvent::TYPE_BEAT,
                max(0, (int) ($beat['start_ms'] ?? 0)),
            ))->setPosition(
                isset($beat['measure_index']) ? (int) $beat['measure_index'] : null,
                isset($beat['beat_index']) ? (int) $beat['beat_index'] : null,
                isset($beat['subdivision_index']) ? (int) $beat['subdivision_index'] : null,
            );

            $this->em->persist($event);
        }

        $counts = [];
        foreach (self::PROFILES as $profile) {
            $chords = $result['profiles'][$profile]['chords'] ?? [];
            $counts[$profile] = is_array($chords) ? count($chords) : 0;

            foreach ($chords as $chord) {
                if (!is_array($chord)) continue;

                $measure = isset($chord['measure_index']) ? (int) $chord['measure_index'] : null;
                $beat = isset($chord['beat_index']) ? (int) $chord['beat_index'] : null;

                $event = (new SongTimelineEvent(
                    $song,
                    SongTimelineEvent::TYPE_CHORD,
                    max(0, (int) ($chord['start_ms'] ?? 0)),
                ))
                    ->setPosition(
                        $measure,
                        $beat,
                        isset($chord['subdivision_index']) ? (int) $chord['subdivision_index'] : null,
                    )
                    ->setOriginalValue($this->normaliseMajorLabel(trim((string) ($chord['chord'] ?? '.'))))
                    ->setPayload([
                        'confidence' => isset($chord['confidence']) ? (float) $chord['confidence'] : null,
                        'profile' => $profile,
                        'analysis_level' => $profile,
                        'analysis_version' => (string) ($result['version'] ?? 'r34-three-profiles'),
                        'downbeat_phase' => $result['downbeat_phase'] ?? null,
                    ]);

                $this->em->persist($event);
            }
        }

        $key = trim((string) ($result['key'] ?? ''));
        if ($key !== '') {
            $song->setKeySignature($key);
        }

        if ($song->getTimeSignature() === 'auto') {
            $signature = trim((string) ($result['time_signature'] ?? ''));
            if ($signature !== '') {
                $song->setTimeSignature($signature);
            }
        }

        $this->em->flush();

        return [
            'schema_version' => 'ezscore.chords.r34',
            'beats' => count($result['beats'] ?? []),
            'profiles' => $counts,
            'key' => $result['key'] ?? null,
            'time_signature' => $result['time_signature'] ?? null,
            'downbeat_phase' => $result['downbeat_phase'] ?? 0,
        ];
    }

    private function normaliseMajorLabel(string $value): string
    {
        // "Cmaj" is redundant; "Cmaj7" remains significant and untouched.
        return preg_replace('/^([A-G](?:#|b)?)maj$/', '$1', $value) ?? $value;
    }
}
