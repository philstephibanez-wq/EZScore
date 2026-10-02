<?php
declare(strict_types=1);

namespace App\Domain\Event;

use App\Domain\Group\UserGroup;
use App\Domain\Playlist\Playlist;
use App\Domain\User\User;
use Doctrine\ORM\Mapping as ORM;

#[ORM\Entity]
#[ORM\Table(name: 'events')]
#[ORM\Index(name: 'IDX_EVENT_STARTS_AT', columns: ['starts_at'])]
#[ORM\Index(name: 'IDX_EVENT_CREATED_BY', columns: ['created_by'])]
#[ORM\Index(name: 'IDX_EVENT_GROUP', columns: ['group_id'])]
#[ORM\Index(name: 'IDX_EVENT_PLAYLIST', columns: ['playlist_id'])]
final class Event
{
    #[ORM\Id]
    #[ORM\GeneratedValue]
    #[ORM\Column]
    private ?int $id = null;

    #[ORM\Column(length: 32, enumType: EventType::class)]
    private EventType $type = EventType::Session;

    #[ORM\Column(length: 180)]
    private string $title = '';

    #[ORM\Column(length: 1000, nullable: true)]
    private ?string $description = null;

    #[ORM\Column]
    private \DateTimeImmutable $startsAt;

    #[ORM\Column(nullable: true)]
    private ?\DateTimeImmutable $endsAt = null;


    #[ORM\Column(length: 255, nullable: true)]
    private ?string $location = null;
#[ORM\Column(length: 16, enumType: EventStatus::class)]
    private EventStatus $status = EventStatus::Draft;

    #[ORM\ManyToOne(targetEntity: User::class)]
    #[ORM\JoinColumn(name: 'created_by', nullable: false, onDelete: 'CASCADE')]
    private User $createdBy;

    #[ORM\ManyToOne(targetEntity: UserGroup::class)]
    #[ORM\JoinColumn(name: 'group_id', nullable: true, onDelete: 'SET NULL')]
    private ?UserGroup $group = null;

    #[ORM\ManyToOne(targetEntity: Playlist::class)]
    #[ORM\JoinColumn(name: 'playlist_id', nullable: true, onDelete: 'SET NULL')]
    private ?Playlist $playlist = null;

    #[ORM\Column]
    private \DateTimeImmutable $createdAt;

    #[ORM\Column]
    private \DateTimeImmutable $updatedAt;

    #[ORM\Column(nullable: true)]
    private ?\DateTimeImmutable $validatedAt = null;

    public function __construct(User $createdBy)
    {
        $now = new \DateTimeImmutable();
        $this->createdBy = $createdBy;
        $this->startsAt = $now->modify('+1 day');
        $this->createdAt = $now;
        $this->updatedAt = $now;
    }

    public function getId(): ?int { return $this->id; }
    public function getType(): EventType { return $this->type; }
    public function setType(EventType $type): self { $this->type = $type; return $this->touch(); }
    public function getTitle(): string { return $this->title; }
    public function setTitle(string $title): self { $this->title = trim($title); return $this->touch(); }
    public function getDescription(): ?string { return $this->description; }
    public function setDescription(?string $description): self { $this->description = $description !== null ? trim($description) : null; return $this->touch(); }
    public function getStartsAt(): \DateTimeImmutable { return $this->startsAt; }
    public function setStartsAt(\DateTimeImmutable $value): self { $this->startsAt = $value; return $this->touch(); }
    public function getEndsAt(): ?\DateTimeImmutable { return $this->endsAt; }
    public function setEndsAt(?\DateTimeImmutable $value): self { $this->endsAt = $value; return $this->touch(); }

    public function getLocation(): ?string { return $this->location; }
    public function setLocation(?string $location): self { $this->location = $location !== null ? trim($location) : null; return $this->touch(); }
    public function getStatus(): EventStatus { return $this->status; }
    public function setStatus(EventStatus $status): self { $this->status = $status; return $this->touch(); }
    public function getCreatedBy(): User { return $this->createdBy; }
    public function getGroup(): ?UserGroup { return $this->group; }
    public function setGroup(?UserGroup $group): self { $this->group = $group; return $this->touch(); }
    public function getPlaylist(): ?Playlist { return $this->playlist; }
    public function setPlaylist(?Playlist $playlist): self { $this->playlist = $playlist; return $this->touch(); }
    public function getCreatedAt(): \DateTimeImmutable { return $this->createdAt; }
    public function getUpdatedAt(): \DateTimeImmutable { return $this->updatedAt; }
    public function getValidatedAt(): ?\DateTimeImmutable { return $this->validatedAt; }

    public function validate(): self
    {
        if ($this->group === null || $this->playlist === null) {
            throw new \LogicException('A session requires exactly one group and one playlist.');
        }
        $this->status = EventStatus::Validated;
        $this->validatedAt = new \DateTimeImmutable();
        return $this->touch();
    }

    private function touch(): self
    {
        $this->updatedAt = new \DateTimeImmutable();
        return $this;
    }
}

