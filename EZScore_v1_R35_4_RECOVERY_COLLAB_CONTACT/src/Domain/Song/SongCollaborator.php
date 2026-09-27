<?php
declare(strict_types=1);
namespace App\Domain\Song;
use App\Domain\User\User;
use Doctrine\ORM\Mapping as ORM;

#[ORM\Entity(repositoryClass: SongCollaboratorRepository::class)]
#[ORM\Table(name: 'song_collaborators')]
#[ORM\UniqueConstraint(name: 'uniq_song_collaborator', columns: ['song_id','user_id'])]
class SongCollaborator {
    #[ORM\Id] #[ORM\GeneratedValue] #[ORM\Column] private ?int $id=null;
    #[ORM\ManyToOne(targetEntity: Song::class)] #[ORM\JoinColumn(name:'song_id',nullable:false,onDelete:'CASCADE')] private Song $song;
    #[ORM\ManyToOne(targetEntity: User::class)] #[ORM\JoinColumn(name:'user_id',nullable:false,onDelete:'CASCADE')] private User $user;
    #[ORM\ManyToOne(targetEntity: User::class)] #[ORM\JoinColumn(name:'granted_by',nullable:false,onDelete:'RESTRICT')] private User $grantedBy;
    #[ORM\Column] private \DateTimeImmutable $createdAt;
    public function __construct(Song $song, User $user, User $grantedBy){$this->song=$song;$this->user=$user;$this->grantedBy=$grantedBy;$this->createdAt=new \DateTimeImmutable();}
    public function getId():?int{return $this->id;} public function getSong():Song{return $this->song;} public function getUser():User{return $this->user;} public function getGrantedBy():User{return $this->grantedBy;} public function getCreatedAt():\DateTimeImmutable{return $this->createdAt;}
}
