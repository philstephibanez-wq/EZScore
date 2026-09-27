<?php

declare(strict_types=1);

namespace App\Security\Acl;

use App\Domain\Song\Song;
use App\Domain\Song\SongStatus;
use App\Domain\User\User;
use App\Service\SongAccessPolicy;
use Symfony\Component\Security\Core\Authentication\Token\TokenInterface;
use Symfony\Component\Security\Core\Authorization\AccessDecisionManagerInterface;
use Symfony\Component\Security\Core\Authorization\Voter\Voter;

/**
 * Central song authorization resource.
 *
 * This removes song-visibility rules from playlist/group code and gives the
 * remaining song controllers a single Symfony-native policy to converge on.
 */
final class SongVoter extends Voter
{
    private const SUPPORTED = [
        AclPrivilege::SONG_VIEW,
        AclPrivilege::SONG_EDIT,
        AclPrivilege::SONG_PUBLISH,
        AclPrivilege::SONG_REPLACE_AUDIO,
    ];

    public function __construct(
        private readonly AccessDecisionManagerInterface $accessDecisionManager,
        private readonly SongAccessPolicy $songAccess,
    ) {
    }

    protected function supports(string $attribute, mixed $subject): bool
    {
        return $subject instanceof Song && in_array($attribute, self::SUPPORTED, true);
    }

    protected function voteOnAttribute(string $attribute, mixed $subject, TokenInterface $token): bool
    {
        if (!$subject instanceof Song) {
            return false;
        }

        if ($this->accessDecisionManager->decide($token, ['ROLE_ADMIN'])) {
            return true;
        }

        $user = $token->getUser();

        if ($attribute === AclPrivilege::SONG_VIEW && $subject->getStatus() === SongStatus::Published) {
            return true;
        }

        if (!$user instanceof User || !$this->accessDecisionManager->decide($token, ['ROLE_EDITOR'])) {
            return false;
        }

        $ownsSong = $this->songAccess->canEdit($subject,$user,false);

        return match ($attribute) {
            AclPrivilege::SONG_VIEW,
            AclPrivilege::SONG_EDIT,
            AclPrivilege::SONG_PUBLISH,
            AclPrivilege::SONG_REPLACE_AUDIO => $ownsSong,
            default => false,
        };
    }
}
