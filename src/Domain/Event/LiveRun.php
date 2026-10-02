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

    #[ORM\Column]
    private \DateTimeImmutable $startedAt;

    #[ORM\Column(nullable: true)]
    private ?\DateTimeImmutable $endedAt = null;

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
    public function getStartedAt(): \DateTimeImmutable { return $this->startedAt; }
    public function getEndedAt(): ?\DateTimeImmutable { return $this->endedAt; }

    public function end(): self
    {
        if ($this->status !== 'ended') {
            $this->status = 'ended';
            $this->endedAt = new \DateTimeImmutable();
            ++$this->revision;
        }

        return $this;
    }
}
