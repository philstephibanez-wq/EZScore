<?php
declare(strict_types=1);
namespace App\Domain\Contact;
use App\Domain\Song\Song;
use App\Domain\User\User;
use Doctrine\ORM\Mapping as ORM;
#[ORM\Entity(repositoryClass: ContactMessageRepository::class)]
#[ORM\Table(name:'contact_messages')]
class ContactMessage {
 #[ORM\Id] #[ORM\GeneratedValue] #[ORM\Column] private ?int $id=null;
 #[ORM\ManyToOne(targetEntity:User::class)] #[ORM\JoinColumn(name:'user_id',nullable:false,onDelete:'CASCADE')] private User $user;
 #[ORM\ManyToOne(targetEntity:Song::class)] #[ORM\JoinColumn(name:'song_id',nullable:true,onDelete:'SET NULL')] private ?Song $song;
 #[ORM\Column(length:40)] private string $category; #[ORM\Column(length:180)] private string $subject; #[ORM\Column(type:'text')] private string $message; #[ORM\Column(length:20)] private string $status='sent'; #[ORM\Column] private \DateTimeImmutable $createdAt;
 public function __construct(User $user,?Song $song,string $category,string $subject,string $message){$this->user=$user;$this->song=$song;$this->category=$category;$this->subject=$subject;$this->message=$message;$this->createdAt=new \DateTimeImmutable();}
}
