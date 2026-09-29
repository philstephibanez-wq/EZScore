<?php

declare(strict_types=1);

namespace App\Domain\Song;

use App\Domain\User\User;
use Doctrine\ORM\Mapping as ORM;

#[ORM\Entity(repositoryClass: SongRepository::class)]
#[ORM\Table(name: 'songs')]
#[ORM\Index(name: 'IDX_SONGS_PUBLISHED_AT', columns: ['published_at'])]
class Song
{
    #[ORM\Id]
    #[ORM\GeneratedValue]
    #[ORM\Column]
    private ?int $id = null;

    #[ORM\Column(length: 180)]
    private string $title = '';

    #[ORM\Column(length: 180)]
    private string $artist = '';

    #[ORM\Column(length: 180, nullable: true)]
    private ?string $author = null;

    #[ORM\Column(length: 180, nullable: true)]
    private ?string $composer = null;

    #[ORM\ManyToOne(targetEntity: User::class)]
    #[ORM\JoinColumn(name: 'editor_id', nullable: true, onDelete: 'SET NULL')]
    private ?User $editor = null;

    #[ORM\Column(length: 16, enumType: SongStatus::class)]
    private SongStatus $status = SongStatus::Imported;

    #[ORM\Column(length: 8)]
    private string $timeSignature = 'auto';

    #[ORM\Column]
    private int $capo = 0;

    #[ORM\Column(name: 'key_signature', length: 16, nullable: true)]
    private ?string $keySignature = null;

    #[ORM\Column(name: 'chord_analysis_level', length: 16, options: ['default' => 'intermediate'])]
    private string $chordAnalysisLevel = 'intermediate';

    #[ORM\Column(name: 'chord_noise_filter_enabled', options: ['default' => false])]
    private bool $chordNoiseFilterEnabled = false;

    #[ORM\Column(length: 120, nullable: true)]
    private ?string $strummingPrimary = null;

    #[ORM\Column(length: 120, nullable: true)]
    private ?string $strummingAlternate = null;

    #[ORM\Column(length: 1000, nullable: true)]
    private ?string $comment = null;

    #[ORM\Column(name: 'lyrics_source_text', type: 'text', nullable: true)]
    private ?string $lyricsSourceText = null;

    #[ORM\Column(name: 'lyrics_current_revision_id', nullable: true)]
    private ?int $lyricsCurrentRevisionId = null;

    #[ORM\Column(length: 500, nullable: true)]
    private ?string $coverPath = null;

    #[ORM\Column(length: 255, nullable: true)]
    private ?string $audioOriginalName = null;

    #[ORM\Column(length: 500, nullable: true)]
    private ?string $audioStoragePath = null;

    #[ORM\Column(length: 120, nullable: true)]
    private ?string $audioMimeType = null;

    #[ORM\Column(nullable: true)]
    private ?int $audioSize = null;

    #[ORM\Column(length: 64, nullable: true)]
    private ?string $audioSha256 = null;

    #[ORM\Column(nullable: true)]
    private ?\DateTimeImmutable $importedAt = null;

    #[ORM\Column(nullable: true)]
    private ?\DateTimeImmutable $publishedAt = null;

    #[ORM\Column]
    private \DateTimeImmutable $createdAt;

    #[ORM\Column]
    private \DateTimeImmutable $updatedAt;

    public function __construct()
    {
        $now = new \DateTimeImmutable();
        $this->createdAt = $now;
        $this->updatedAt = $now;
    }

    public function getId(): ?int { return $this->id; }
    public function getTitle(): string { return $this->title; }
    public function setTitle(string $title): self { $this->title = trim($title); return $this->touch(); }
    public function getArtist(): string { return $this->artist; }
    public function setArtist(string $artist): self { $this->artist = trim($artist); return $this->touch(); }
    public function getAuthor(): ?string { return $this->author; }
    public function setAuthor(?string $author): self { $this->author = $this->normaliseNullable($author); return $this->touch(); }
    public function getComposer(): ?string { return $this->composer; }
    public function setComposer(?string $composer): self { $this->composer = $this->normaliseNullable($composer); return $this->touch(); }
    public function getEditor(): ?User { return $this->editor; }
    public function setEditor(?User $editor): self { $this->editor = $editor; return $this->touch(); }
    public function getStatus(): SongStatus { return $this->status; }

    public function markImported(): self
    {
        $this->status = SongStatus::Imported;
        $this->publishedAt = null;
        return $this->touch();
    }

    public function markAnalyzed(): self
    {
        $this->status = SongStatus::Analyzed;
        $this->publishedAt = null;
        return $this->touch();
    }

    public function markEditing(): self
    {
        $this->status = SongStatus::Editing;
        $this->publishedAt = null;
        return $this->touch();
    }

    public function getTimeSignature(): string { return $this->timeSignature; }

    public function setTimeSignature(string $timeSignature): self
    {
        if ($timeSignature !== 'auto') {
            if (!preg_match('/^(\\d{1,2})\\/(1|2|4|8|16|32)$/', $timeSignature, $matches)) {
                throw new \InvalidArgumentException(sprintf('Unsupported time signature "%s".', $timeSignature));
            }

            $numerator = (int) $matches[1];
            if ($numerator < 1 || $numerator > 32) {
                throw new \InvalidArgumentException(sprintf('Unsupported time signature "%s".', $timeSignature));
            }
        }

        $this->timeSignature = $timeSignature;
        return $this->touch();
    }

    public function getKeySignature(): ?string { return $this->keySignature; }

    public function setKeySignature(?string $keySignature): self
    {
        if ($keySignature !== null) {
            $keySignature = trim($keySignature);
            if ($keySignature !== '' && !preg_match('/^[A-G](?:#|b)?(?:m)?$/', $keySignature)) {
                throw new \InvalidArgumentException('Invalid musical key.');
            }
            if ($keySignature === '') {
                $keySignature = null;
            }
        }

        $this->keySignature = $keySignature;
        return $this->touch();
    }

    public function isChordNoiseFilterEnabled(): bool { return $this->chordNoiseFilterEnabled; }
    public function setChordNoiseFilterEnabled(bool $enabled): self { $this->chordNoiseFilterEnabled = $enabled; return $this->touch(); }

    public function getChordAnalysisLevel(): string { return $this->chordAnalysisLevel; }

    public function setChordAnalysisLevel(string $level): self
    {
        if (!in_array($level, ['beginner', 'intermediate', 'expert'], true)) {
            throw new \InvalidArgumentException('Invalid chord analysis level.');
        }

        $this->chordAnalysisLevel = $level;
        return $this->touch();
    }

    public function getCapo(): int { return $this->capo; }

    public function setCapo(int $capo): self
    {
        if ($capo < 0 || $capo > 11) {
            throw new \InvalidArgumentException('Capo must be between 0 and 11.');
        }
        $this->capo = $capo;
        return $this->touch();
    }

    public function getStrummingPrimary(): ?string { return $this->strummingPrimary; }
    public function setStrummingPrimary(?string $value): self { $this->strummingPrimary = $this->normaliseNullable($value); return $this->touch(); }
    public function getStrummingAlternate(): ?string { return $this->strummingAlternate; }
    public function setStrummingAlternate(?string $value): self { $this->strummingAlternate = $this->normaliseNullable($value); return $this->touch(); }
    public function getLyricsSourceText(): ?string { return $this->lyricsSourceText; }
    public function setLyricsSourceText(?string $value): self
    {
        $this->lyricsSourceText = $value === null ? null : str_replace(["\r\n","\r"],"\n",$value);
        return $this->touch();
    }

    public function getLyricsCurrentRevisionId(): ?int { return $this->lyricsCurrentRevisionId; }
    public function setLyricsCurrentRevisionId(?int $revisionId): self
    {
        $this->lyricsCurrentRevisionId = $revisionId;
        return $this->touch();
    }

    public function getComment(): ?string { return $this->comment; }
    public function setComment(?string $comment): self { $this->comment = $this->normaliseNullable($comment); return $this->touch(); }
    public function getCoverPath(): ?string { return $this->coverPath; }
    public function setCoverPath(?string $coverPath): self { $this->coverPath = $this->normaliseNullable($coverPath); return $this->touch(); }

    public function getAudioOriginalName(): ?string { return $this->audioOriginalName; }
    public function getAudioStoragePath(): ?string { return $this->audioStoragePath; }
    public function getAudioMimeType(): ?string { return $this->audioMimeType; }
    public function getAudioSize(): ?int { return $this->audioSize; }
    public function getAudioSha256(): ?string { return $this->audioSha256; }
    public function getImportedAt(): ?\DateTimeImmutable { return $this->importedAt; }

    public function setImportedAudio(
        string $originalName,
        string $storagePath,
        string $mimeType,
        int $size,
        string $sha256,
        ?\DateTimeImmutable $importedAt = null,
    ): self {
        if (!preg_match('/^[a-f0-9]{64}$/', $sha256)) {
            throw new \InvalidArgumentException('Audio SHA-256 must be a hexadecimal SHA-256 value.');
        }
        if ($size < 1) {
            throw new \InvalidArgumentException('Audio size must be greater than zero.');
        }

        $this->audioOriginalName = trim($originalName);
        $this->audioStoragePath = trim($storagePath);
        $this->audioMimeType = trim($mimeType);
        $this->audioSize = $size;
        $this->audioSha256 = $sha256;
        $this->importedAt = $importedAt ?? new \DateTimeImmutable();

        return $this->touch();
    }

    public function getPublishedAt(): ?\DateTimeImmutable { return $this->publishedAt; }
    public function isPublished(): bool { return $this->status === SongStatus::Published; }

    public function publish(?\DateTimeImmutable $publishedAt = null): self
    {
        $this->status = SongStatus::Published;
        $this->publishedAt = $publishedAt ?? new \DateTimeImmutable();
        return $this->touch();
    }

    public function unpublish(): self { return $this->markEditing(); }
    public function getCreatedAt(): \DateTimeImmutable { return $this->createdAt; }
    public function getUpdatedAt(): \DateTimeImmutable { return $this->updatedAt; }

    private function touch(): self
    {
        $this->updatedAt = new \DateTimeImmutable();
        return $this;
    }

    private function normaliseNullable(?string $value): ?string
    {
        if ($value === null) {
            return null;
        }
        $value = trim($value);
        return $value === '' ? null : $value;
    }
}
