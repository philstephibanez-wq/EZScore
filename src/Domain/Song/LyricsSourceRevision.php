<?php
declare(strict_types=1);

namespace App\Domain\Song;

use App\Domain\User\User;
use Doctrine\ORM\Mapping as ORM;

#[ORM\Entity(repositoryClass: LyricsSourceRevisionRepository::class)]
#[ORM\Table(name: 'lyrics_source_revisions')]
#[ORM\Index(name: 'IDX_LYRICS_REVISION_SONG_CREATED', columns: ['song_id', 'created_at'])]
class LyricsSourceRevision
{
    #[ORM\Id]
    #[ORM\GeneratedValue]
    #[ORM\Column]
    private ?int $id = null;

    #[ORM\ManyToOne(targetEntity: Song::class)]
    #[ORM\JoinColumn(name: 'song_id', nullable: false, onDelete: 'CASCADE')]
    private Song $song;

    #[ORM\ManyToOne(targetEntity: User::class)]
    #[ORM\JoinColumn(name: 'created_by_user_id', nullable: true, onDelete: 'SET NULL')]
    private ?User $createdBy;

    #[ORM\Column(type: 'text')]
    private string $content;

    #[ORM\Column(length: 32)]
    private string $sourceType;

    #[ORM\Column(length: 1000, nullable: true)]
    private ?string $comment;

    #[ORM\Column]
    private \DateTimeImmutable $createdAt;

    public function __construct(
        Song $song,
        string $content,
        string $sourceType,
        ?string $comment,
        ?User $createdBy,
    ) {
        $this->song = $song;
        $this->content = $content;
        $this->sourceType = $sourceType;
        $this->comment = $this->normaliseComment($comment);
        $this->createdBy = $createdBy;
        $this->createdAt = new \DateTimeImmutable();
    }

    public function getId(): ?int { return $this->id; }
    public function getSong(): Song { return $this->song; }
    public function getCreatedBy(): ?User { return $this->createdBy; }
    public function getContent(): string { return $this->content; }
    public function getSourceType(): string { return $this->sourceType; }
    public function getComment(): ?string { return $this->comment; }
    public function getCreatedAt(): \DateTimeImmutable { return $this->createdAt; }

    public function updateMetadata(string $sourceType, ?string $comment, ?User $createdBy): self
    {
        $this->sourceType = $sourceType;
        $this->comment = $this->normaliseComment($comment);
        $this->createdBy = $createdBy;
        return $this;
    }

    private function normaliseComment(?string $comment): ?string
    {
        if ($comment === null) {
            return null;
        }
        $comment = trim($comment);
        return $comment === '' ? null : mb_substr($comment, 0, 1000);
    }
}
