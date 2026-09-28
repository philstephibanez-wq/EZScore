<?php

declare(strict_types=1);

namespace App\Domain\User;

use Doctrine\Bundle\DoctrineBundle\Repository\ServiceEntityRepository;
use Doctrine\Persistence\ManagerRegistry;

final class UserRepository extends ServiceEntityRepository
{
    public function __construct(ManagerRegistry $registry)
    {
        parent::__construct($registry, User::class);
    }

    public function countAll(): int
    {
        return (int) $this->createQueryBuilder('u')
            ->select('COUNT(u.id)')
            ->getQuery()
            ->getSingleScalarResult();
    }

    public function countActiveAdmins(): int
    {
        $activeUsers = $this->findBy(['active' => true]);

        return count(array_filter(
            $activeUsers,
            static fn(User $user): bool => in_array('ROLE_ADMIN', $user->getRoles(), true),
        ));
    }

    public function findFirstCreatedAdmin(): ?User
    {
        foreach ($this->findBy([], ['id' => 'ASC']) as $user) {
            if ($user instanceof User && in_array('ROLE_ADMIN', $user->getRoles(), true)) {
                return $user;
            }
        }

        return null;
    }

    public function findByGoogleSub(string $sub): ?User
    {
        return $this->findOneBy(['googleSub' => $sub]);
    }

    public function findByActivationToken(string $rawToken): ?User
    {
        if (!preg_match('/^[a-f0-9]{64}$/', $rawToken)) {
            return null;
        }

        return $this->findOneBy([
            'activationTokenHash' => hash('sha256', $rawToken),
        ]);
    }
}
