<?php

declare(strict_types=1);

namespace App\Service;

use App\Domain\User\User;
use App\Domain\User\UserRepository;

final class AdminRecipientResolver
{
    public function __construct(
        private readonly UserRepository $users,
    ) {
    }

    public function resolve(): User
    {
        $admin = $this->users->findFirstCreatedAdmin();

        if (!$admin instanceof User || !filter_var($admin->getEmail(), FILTER_VALIDATE_EMAIL)) {
            throw new \RuntimeException('EZScore first-run administrator email is unavailable.');
        }

        return $admin;
    }

    public function email(): string
    {
        return $this->resolve()->getEmail();
    }
}
