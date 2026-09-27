<?php
declare(strict_types=1);
namespace App\Domain\Contact;
use App\Domain\User\User;
use Doctrine\Bundle\DoctrineBundle\Repository\ServiceEntityRepository;
use Doctrine\Persistence\ManagerRegistry;
final class ContactMessageRepository extends ServiceEntityRepository{
 public function __construct(ManagerRegistry $registry){parent::__construct($registry,ContactMessage::class);}
 public function hasRecent(User $user,int $seconds=60):bool{$cutoff=(new \DateTimeImmutable())->modify('-'.$seconds.' seconds');return (int)$this->createQueryBuilder('m')->select('COUNT(m.id)')->andWhere('m.user = :user')->andWhere('m.createdAt >= :cutoff')->setParameter('user',$user)->setParameter('cutoff',$cutoff)->getQuery()->getSingleScalarResult()>0;}
}
