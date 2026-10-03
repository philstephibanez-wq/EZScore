<?php
declare(strict_types=1);

namespace App\Domain\Event;

use App\Domain\User\User;
use Doctrine\ORM\Mapping as ORM;

#[ORM\Entity]
#[ORM\Table(name: 'live_runs')]
#[ORM\Index(name: 'IDX_LIVE_RUN_EVENT_STATUS', columns: ['event_id', 'status'])]
final class LiveRun
{
    #[ORM\Id]
    #[ORM\GeneratedValue]
    #[ORM\Column]
    private ?int $id = null;

    #[ORM\ManyToOne(targetEntity: Event::class, fetch: 'EAGER')]
    #[ORM\JoinColumn(name: 'event_id', nullable: false, onDelete: 'CASCADE')]
    private Event $event;

    #[ORM\ManyToOne(targetEntity: User::class)]
    #[ORM\JoinColumn(name: 'conductor_user_id', nullable: false, onDelete: 'CASCADE')]
    private User $conductor;

    #[ORM\Column(length: 16)]
    private string $status = 'live';

    #[ORM\Column(options: ['default' => true])]
    private bool $testMode = true;

    #[ORM\Column(options: ['default' => 0])]
    private int $revision = 0;

    #[ORM\Column(nullable: true)]
    private ?int $currentSongId = null;

    #[ORM\Column(options: ['default' => false])]
    private bool $playing = false;

    #[ORM\Column(options: ['default' => 0])]
    private int $positionMs = 0;

    #[ORM\Column(options: ['default' => 1.0])]
    private float $playbackRate = 1.0;

    #[ORM\Column(nullable: true)]
    private ?\DateTimeImmutable $stateUpdatedAt = null;

    #[ORM\Column(name: 'state_updated_at_ms', nullable: true)]
    private ?int $stateUpdatedAtMs = null;

    #[ORM\Column(name: 'diagram_enabled', options: ['default' => false])]
    private bool $diagramEnabled = false;

    #[ORM\Column]
    private \DateTimeImmutable $startedAt;

    #[ORM\Column(nullable: true)]
    private ?\DateTimeImmutable $endedAt = null;


    #[ORM\Column(name: 'countdown_ends_at', nullable: true)]
    private ?\DateTimeImmutable $countdownEndsAt = null;

    #[ORM\Column(name: 'countdown_total_seconds', options: ['default' => 0])]
    private int $countdownTotalSeconds = 0;

    public function __construct(Event $event, User $conductor, bool $testMode = true)
    {
        $this->event = $event;
        $this->conductor = $conductor;
        $this->testMode = $testMode;
        $this->startedAt = new \DateTimeImmutable();
    }

    public function getId(): ?int { return $this->id; }
    public function getEvent(): Event { return $this->event; }
    public function getConductor(): User { return $this->conductor; }
    public function getStatus(): string { return $this->status; }
    public function isLive(): bool { return $this->status === 'live'; }
    public function isTestMode(): bool { return $this->testMode; }
    public function getRevision(): int { return $this->revision; }
    public function getCurrentSongId(): ?int { return $this->currentSongId; }
    public function isPlaying(): bool { return $this->playing; }
    public function getPositionMs(): int { return $this->positionMs; }
    public function getPlaybackRate(): float { return $this->playbackRate; }
    public function getStateUpdatedAt(): ?\DateTimeImmutable { return $this->stateUpdatedAt; }
    public function getStateUpdatedAtMs(): ?int { return $this->stateUpdatedAtMs; }
    public function isDiagramEnabled(): bool { return $this->diagramEnabled; }
    public function getStartedAt(): \DateTimeImmutable { return $this->startedAt; }
    public function getEndedAt(): ?\DateTimeImmutable { return $this->endedAt; }

    public function updateTransport(int $songId, bool $playing, int $positionMs, float $playbackRate): self
    {
        $this->currentSongId = max(1, $songId);
        $this->playing = $playing;
        $this->positionMs = max(0, $positionMs);
        $this->playbackRate = max(0.5, min(2.0, $playbackRate));
        $this->stateUpdatedAt = new \DateTimeImmutable();
        $this->stateUpdatedAtMs = (int) round(microtime(true) * 1000);
        ++$this->revision;

        return $this;
    }


    public function getKaraokeCurrentSongId(): ?int { return $this->currentSongId; }
    public function isKaraokePlaying(): bool { return $this->playing; }
    public function getKaraokePositionMs(): int { return $this->positionMs; }
    public function getKaraokePlaybackRate(): float { return $this->playbackRate; }
    public function getKaraokeStateUpdatedAt(): ?\DateTimeImmutable { return $this->stateUpdatedAt; }
    public function getKaraokeStateUpdatedAtMs(): ?int { return $this->stateUpdatedAtMs; }
    public function isKaraokeDiagramEnabled(): bool { return $this->diagramEnabled; }


    public function getKaraokeCountdownEndsAt(): ?\DateTimeImmutable { return $this->countdownEndsAt; }
    public function getKaraokeCountdownTotalSeconds(): int { return $this->countdownTotalSeconds; }

    public function startKaraokeCountdown(int $songId, int $seconds, float $playbackRate, bool $diagramEnabled = false): self
    {
        $seconds = max(1, min(30, $seconds));
        $this->currentSongId = $songId;
        $this->playing = false;
        $this->positionMs = 0;
        $this->playbackRate = max(0.50, min(2.00, $playbackRate));
        $this->diagramEnabled = $diagramEnabled;
        $this->countdownTotalSeconds = $seconds;
        $this->countdownEndsAt = (new \DateTimeImmutable())->modify('+'.$seconds.' seconds');
        $this->stateUpdatedAt = new \DateTimeImmutable();
        $this->stateUpdatedAtMs = (int) round(microtime(true) * 1000);
        ++$this->revision;

        return $this;
    }

    public function clearKaraokeCountdown(): self
    {
        $this->countdownEndsAt = null;
        $this->countdownTotalSeconds = 0;

        return $this;
    }
    public function updateKaraokeTransport(
        int $songId,
        bool $playing,
        int $positionMs,
        float $playbackRate,
        bool $diagramEnabled = false,
    ): self {
        $this->currentSongId = $songId;
        $this->playing = $playing;
        // R1.C7 real transport clears pre-roll.
        if ($playing) {
            $this->countdownEndsAt = null;
            $this->countdownTotalSeconds = 0;
        }
        $this->positionMs = max(0, $positionMs);
        $this->playbackRate = max(0.50, min(2.00, $playbackRate));
        $this->diagramEnabled = $diagramEnabled;
        $this->stateUpdatedAt = new \DateTimeImmutable();
        $this->stateUpdatedAtMs = (int) round(microtime(true) * 1000);
        ++$this->revision;

        return $this;
    }
    public function end(): self
    {
        if ($this->status !== 'ended') {
            $this->status = 'ended';
            $this->playing = false;
            $this->endedAt = new \DateTimeImmutable();
            $this->stateUpdatedAt = $this->endedAt;
            $this->stateUpdatedAtMs = (int) round(microtime(true) * 1000);
            ++$this->revision;
        }

        return $this;
    }
}
