<?php
declare(strict_types=1);
namespace App\Service;
use App\Domain\Song\Song;
use App\Domain\Song\SongCollaboratorRepository;
use App\Domain\User\User;
final class SongAccessPolicy {
    public function __construct(private readonly SongCollaboratorRepository $collaborators){}
    public function isOwner(Song $song,User $user):bool{return $song->getEditor()?->getId()===$user->getId();}
    public function canEdit(Song $song,User $user,bool $isAdmin):bool{return $isAdmin||$this->isOwner($song,$user)||$this->collaborators->isCollaborator($song,$user);}
    public function canManageDelegation(Song $song,User $user,bool $isAdmin):bool{return $isAdmin||$this->isOwner($song,$user);}
}
