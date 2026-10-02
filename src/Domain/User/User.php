<?php

declare(strict_types=1);

namespace App\Domain\User;

use Doctrine\ORM\Mapping as ORM;
use Symfony\Component\Security\Core\User\PasswordAuthenticatedUserInterface;
use Symfony\Component\Security\Core\User\UserInterface;

#[ORM\Entity(repositoryClass: UserRepository::class)]
#[ORM\Table(name: 'users')]
#[ORM\UniqueConstraint(name: 'uniq_users_email', columns: ['email'])]
#[ORM\UniqueConstraint(name: 'uniq_users_activation_token_hash', columns: ['activation_token_hash'])]
class User implements UserInterface, PasswordAuthenticatedUserInterface
{
    public const SUPPORTED_LOCALES = ['fr', 'en'];

    #[ORM\Id]
    #[ORM\GeneratedValue]
    #[ORM\Column]
    private ?int $id = null;

    #[ORM\Column(length: 190)]
    private string $email = '';

    #[ORM\Column(length: 120)]
    private string $displayName = '';

    #[ORM\Column(nullable: true)]
    private ?string $password = null;

    #[ORM\Column(type: 'json')]
    private array $roles = ['ROLE_READER'];

    #[ORM\Column]
    private bool $active = true;

    #[ORM\Column(length: 255, nullable: true)]
    private ?string $googleSub = null;

    #[ORM\Column(length: 600, nullable: true)]
    private ?string $avatarUrl = null;

    #[ORM\Column(length: 2)]
    private string $locale = 'fr';

    #[ORM\Column(options: ['default' => true])]
    private bool $notifyNewSongs = true;

    #[ORM\Column(nullable: true)]
    private ?\DateTimeImmutable $emailVerifiedAt = null;

    #[ORM\Column(length: 64, nullable: true)]
    private ?string $activationTokenHash = null;

    #[ORM\Column(nullable: true)]
    private ?\DateTimeImmutable $activationExpiresAt = null;

    #[ORM\Column(nullable: true)]
    private ?\DateTimeImmutable $activationRequestedAt = null;

    #[ORM\Column]
    private \DateTimeImmutable $createdAt;

    public function __construct()
    {
        $this->createdAt = new \DateTimeImmutable();
    }

    public function getId(): ?int { return $this->id; }
    public function getEmail(): string { return $this->email; }
    public function setEmail(string $email): self { $this->email = mb_strtolower(trim($email)); return $this; }
    public function getDisplayName(): string { return $this->displayName; }
    public function setDisplayName(string $name): self { $this->displayName = trim($name); return $this; }
    public function getPassword(): ?string { return $this->password; }
    public function setPassword(?string $password): self { $this->password = $password; return $this; }
    public function isActive(): bool { return $this->active; }
    public function setActive(bool $active): self { $this->active = $active; return $this; }
    public function getGoogleSub(): ?string { return $this->googleSub; }
    public function setGoogleSub(?string $sub): self { $this->googleSub = $sub; return $this; }
    public function getAvatarUrl(): ?string { return $this->avatarUrl; }
    public function setAvatarUrl(?string $url): self { $this->avatarUrl = $url; return $this; }
    public function getLocale(): string { return $this->locale; }
    public function wantsNewSongNotifications(): bool { return $this->notifyNewSongs; }
    public function setNotifyNewSongs(bool $enabled): self { $this->notifyNewSongs = $enabled; return $this; }

    public function setLocale(string $locale): self
    {
        if (!in_array($locale, self::SUPPORTED_LOCALES, true)) {
            throw new \InvalidArgumentException(sprintf('Unsupported locale "%s".', $locale));
        }

        $this->locale = $locale;
        return $this;
    }

    public function getEmailVerifiedAt(): ?\DateTimeImmutable { return $this->emailVerifiedAt; }
    public function isEmailVerified(): bool { return $this->emailVerifiedAt !== null; }
    public function getActivationTokenHash(): ?string { return $this->activationTokenHash; }
    public function getActivationExpiresAt(): ?\DateTimeImmutable { return $this->activationExpiresAt; }
    public function getActivationRequestedAt(): ?\DateTimeImmutable { return $this->activationRequestedAt; }

    public function requestEmailActivation(
        string $tokenHash,
        \DateTimeImmutable $requestedAt,
        \DateTimeImmutable $expiresAt,
    ): self {
        if (!preg_match('/^[a-f0-9]{64}$/', $tokenHash)) {
            throw new \InvalidArgumentException('Activation token hash must be a SHA-256 hexadecimal value.');
        }

        if ($expiresAt <= $requestedAt) {
            throw new \InvalidArgumentException('Activation token expiry must be after request time.');
        }

        $this->activationTokenHash = $tokenHash;
        $this->activationRequestedAt = $requestedAt;
        $this->activationExpiresAt = $expiresAt;

        return $this;
    }

    public function verifyEmail(\DateTimeImmutable $verifiedAt): self
    {
        $this->emailVerifiedAt = $verifiedAt;
        $this->activationTokenHash = null;
        $this->activationRequestedAt = null;
        $this->activationExpiresAt = null;

        return $this;
    }

    public function markEmailVerifiedForManagedAccount(): self
    {
        if ($this->emailVerifiedAt === null) {
            $this->emailVerifiedAt = new \DateTimeImmutable();
        }

        return $this;
    }

    public function getCreatedAt(): \DateTimeImmutable { return $this->createdAt; }
    public function getUserIdentifier(): string { return $this->email; }
    public function eraseCredentials(): void { }

    public function getRoles(): array
    {
        $roles = $this->roles;
        $roles[] = 'ROLE_USER';

        return array_values(array_unique($roles));
    }

    public function setRoles(array $roles): self
    {
        $allowed = ['ROLE_ADMIN', 'ROLE_EDITOR', 'ROLE_READER', 'ROLE_DISPLAY'];
        $filtered = array_values(array_intersect($allowed, $roles));
        $this->roles = $filtered ?: ['ROLE_READER'];

        return $this;
    }

    public function getPrimaryRole(): string
    {
        foreach (['ROLE_ADMIN', 'ROLE_EDITOR', 'ROLE_READER', 'ROLE_DISPLAY'] as $role) {
            if (in_array($role, $this->roles, true)) {
                return $role;
            }
        }

        return 'ROLE_READER';
    }
}
