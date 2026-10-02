<?php
declare(strict_types=1);

namespace App\Security\Acl;

use App\Domain\Event\Event;
use App\Domain\Event\EventParticipant;
use App\Domain\Event\EventStatus;
use App\Domain\Group\GroupMember;
use App\Domain\User\User;
use Doctrine\ORM\EntityManagerInterface;
use Symfony\Component\Security\Core\Authentication\Token\TokenInterface;
use Symfony\Component\Security\Core\Authorization\AccessDecisionManagerInterface;
use Symfony\Component\Security\Core\Authorization\Voter\Voter;

final class EventVoter extends Voter
{
    public function __construct(
        private readonly EntityManagerInterface $em,
        private readonly AccessDecisionManagerInterface $accessDecisionManager,
    ) {}

    protected function supports(string $attribute, mixed $subject): bool
    {
        return $subject instanceof Event && in_array($attribute, [
            AclPrivilege::EVENT_VIEW,
            AclPrivilege::EVENT_MANAGE,
            AclPrivilege::EVENT_INVITE,
        ], true);
    }

    protected function voteOnAttribute(string $attribute, mixed $subject, TokenInterface $token): bool
    {
        if (!$subject instanceof Event) return false;

        $user = $token->getUser();
        if (!$user instanceof User) return false;

        if ($this->accessDecisionManager->decide($token, ['ROLE_ADMIN'])) return true;

        $creator = $subject->getCreatedBy()->getId() === $user->getId();

        if ($subject->getStatus() === EventStatus::Draft && !$creator) {
            return false;
        }

        if ($attribute === AclPrivilege::EVENT_VIEW) {
            if ($creator) return true;

            if ($this->em->getRepository(EventParticipant::class)->findOneBy([
                'event' => $subject,
                'user' => $user,
            ]) instanceof EventParticipant) {
                return true;
            }

            if ($subject->getGroup() !== null) {
                return $this->em->getRepository(GroupMember::class)->findOneBy([
                    'group' => $subject->getGroup(),
                    'user' => $user,
                ]) instanceof GroupMember;
            }

            return false;
        }

        if ($creator) return true;

        if ($subject->getGroup() !== null) {
            $membership = $this->em->getRepository(GroupMember::class)->findOneBy([
                'group' => $subject->getGroup(),
                'user' => $user,
            ]);

            if ($membership instanceof GroupMember) {
                return in_array($membership->getRole(), ['owner', 'manager'], true);
            }
        }

        return false;
    }
}
