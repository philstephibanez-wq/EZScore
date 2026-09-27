<?php
declare(strict_types=1);
namespace App\Domain\Song;
use App\Domain\User\User;
use Doctrine\Bundle\DoctrineBundle\Repository\ServiceEntityRepository;
use Doctrine\Persistence\ManagerRegistry;
final class SongCollaboratorRepository extends ServiceEntityRepository {
    public function __construct(ManagerRegistry $registry){parent::__construct($registry,SongCollaborator::class);}
    public function isCollaborator(Song $song,User $user):bool{return (int)$this->createQueryBuilder('c')->select('COUNT(c.id)')->andWhere('c.song = :song')->andWhere('c.user = :user')->setParameter('song',$song)->setParameter('user',$user)->getQuery()->getSingleScalarResult()>0;}
    public function findForSong(Song $song):array{return $this->createQueryBuilder('c')->leftJoin('c.user','u')->addSelect('u')->andWhere('c.song = :song')->setParameter('song',$song)->orderBy('u.displayName','ASC')->getQuery()->getResult();}
}
