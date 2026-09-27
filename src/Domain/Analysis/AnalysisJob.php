<?php

declare(strict_types=1);

namespace App\Domain\Analysis;

use App\Domain\Song\Song;
use App\Domain\User\User;
use Doctrine\ORM\Mapping as ORM;

#[ORM\Entity(repositoryClass: AnalysisJobRepository::class)]
#[ORM\Table(name: 'analysis_jobs')]
class AnalysisJob
{
    #[ORM\Id]
    #[ORM\GeneratedValue]
    #[ORM\Column]
    private ?int $id = null;

    #[ORM\ManyToOne(targetEntity: Song::class)]
    #[ORM\JoinColumn(name: 'song_id', nullable: false, onDelete: 'CASCADE')]
    private Song $song;

    #[ORM\ManyToOne(targetEntity: User::class)]
    #[ORM\JoinColumn(name: 'created_by', nullable: false, onDelete: 'RESTRICT')]
    private User $createdBy;

    #[ORM\Column(length: 40)]
    private string $kind = '';

    #[ORM\Column(length: 16, enumType: AnalysisJobStatus::class)]
    private AnalysisJobStatus $status = AnalysisJobStatus::Queued;

    #[ORM\Column]
    private int $progress = 0;

    #[ORM\Column(type: 'json')]
    private array $requestData = [];

    #[ORM\Column(type: 'json', nullable: true)]
    private ?array $resultData = null;

    #[ORM\Column(length: 80, nullable: true)]
    private ?string $errorCode = null;

    #[ORM\Column]
    private \DateTimeImmutable $createdAt;

    #[ORM\Column]
    private \DateTimeImmutable $updatedAt;

    public function __construct(Song $song, User $createdBy, string $kind, array $requestData)
    {
        $kind = trim($kind);
        if ($kind === '') {
            throw new \InvalidArgumentException('Analysis job kind is required.');
        }

        $this->song = $song;
        $this->createdBy = $createdBy;
        $this->kind = $kind;
        $this->requestData = $requestData;
        $now = new \DateTimeImmutable();
        $this->createdAt = $now;
        $this->updatedAt = $now;
    }

    public function getId(): ?int { return $this->id; }
    public function getSong(): Song { return $this->song; }
    public function getCreatedBy(): User { return $this->createdBy; }
    public function getKind(): string { return $this->kind; }
    public function getStatus(): AnalysisJobStatus { return $this->status; }
    public function getProgress(): int { return $this->progress; }
    public function getRequestData(): array { return $this->requestData; }
    public function getResultData(): ?array { return $this->resultData; }
    public function getErrorCode(): ?string { return $this->errorCode; }
    public function getCreatedAt(): \DateTimeImmutable { return $this->createdAt; }
    public function getUpdatedAt(): \DateTimeImmutable { return $this->updatedAt; }

    public function markRunning(int $progress = 0): self
    {
        $this->status = AnalysisJobStatus::Running;
        return $this->setProgress($progress);
    }

    public function setProgress(int $progress): self
    {
        if ($progress < 0 || $progress > 100) {
            throw new \InvalidArgumentException('Analysis progress must be between 0 and 100.');
        }
        $this->progress = $progress;
        $this->updatedAt = new \DateTimeImmutable();
        return $this;
    }

    public function complete(array $resultData): self
    {
        $this->status = AnalysisJobStatus::Completed;
        $this->progress = 100;
        $this->resultData = $resultData;
        $this->errorCode = null;
        $this->updatedAt = new \DateTimeImmutable();
        return $this;
    }

    public function fail(string $errorCode): self
    {
        $errorCode = trim($errorCode);
        if ($errorCode === '') {
            throw new \InvalidArgumentException('Analysis error code is required.');
        }
        $this->status = AnalysisJobStatus::Failed;
        $this->errorCode = $errorCode;
        $this->updatedAt = new \DateTimeImmutable();
        return $this;
    }

    public function touchLease(): self
    {
        $this->updatedAt = new \DateTimeImmutable();
        return $this;
    }

    public function requeue(): self
    {
        $this->status = AnalysisJobStatus::Queued;
        $this->progress = 0;
        $this->errorCode = null;
        $this->updatedAt = new \DateTimeImmutable();
        return $this;
    }

    public function cancel(): self
    {
        $this->status = AnalysisJobStatus::Cancelled;
        $this->updatedAt = new \DateTimeImmutable();
        return $this;
    }
}
