<?php
declare(strict_types=1);
namespace App\Controller;
use App\Domain\Song\Song;
use App\Domain\Song\SongCollaborator;
use App\Domain\Song\SongCollaboratorRepository;
use App\Domain\User\User;
use App\Domain\User\UserRepository;
use App\Service\SongAccessPolicy;
use Doctrine\ORM\EntityManagerInterface;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;
#[Route('/song/{id}/collaborators',requirements:['id'=>'\d+'])]
final class SongCollaborationController extends AbstractController{
 #[Route('',name:'app_song_collaborators',methods:['GET'])]
 public function index(Song $song,SongCollaboratorRepository $repo,SongAccessPolicy $policy,UserRepository $users):Response{$me=$this->getUser();if(!$me instanceof User||!$policy->canEdit($song,$me,$this->isGranted('ROLE_ADMIN')))throw $this->createAccessDeniedException();$editors=$users->createQueryBuilder('u')->andWhere('u.active = :active')->andWhere('u.roles LIKE :editor')->setParameter('active',true)->setParameter('editor','%ROLE_EDITOR%')->orderBy('u.displayName','ASC')->getQuery()->getResult();return $this->render('song/collaborators.html.twig',['song'=>$song,'collaborators'=>$repo->findForSong($song),'editors'=>$editors,'can_manage'=>$policy->canManageDelegation($song,$me,$this->isGranted('ROLE_ADMIN'))]);}
 #[Route('/add',name:'app_song_collaborator_add',methods:['POST'])]
 public function add(Song $song,Request $request,UserRepository $users,SongCollaboratorRepository $repo,SongAccessPolicy $policy,EntityManagerInterface $em):Response{$me=$this->getUser();if(!$me instanceof User||!$policy->canManageDelegation($song,$me,$this->isGranted('ROLE_ADMIN')))throw $this->createAccessDeniedException();if(!$this->isCsrfTokenValid('song_collaborators_'.$song->getId(),(string)$request->request->get('_token')))throw $this->createAccessDeniedException();$target=$users->find((int)$request->request->get('user_id'));if(!$target instanceof User||!in_array('ROLE_EDITOR',$target->getRoles(),true))throw $this->createNotFoundException();if($song->getEditor()?->getId()!==$target->getId()&&!$repo->isCollaborator($song,$target)){$em->persist(new SongCollaborator($song,$target,$me));$em->flush();}return $this->redirectToRoute('app_song_collaborators',['_locale'=>$request->getLocale(),'id'=>$song->getId()]);}
 #[Route('/{userId}/remove',name:'app_song_collaborator_remove',requirements:['userId'=>'\d+'],methods:['POST'])]
 public function remove(Song $song,int $userId,Request $request,SongCollaboratorRepository $repo,SongAccessPolicy $policy,EntityManagerInterface $em):Response{$me=$this->getUser();if(!$me instanceof User||!$policy->canManageDelegation($song,$me,$this->isGranted('ROLE_ADMIN')))throw $this->createAccessDeniedException();if(!$this->isCsrfTokenValid('song_collaborators_'.$song->getId(),(string)$request->request->get('_token')))throw $this->createAccessDeniedException();$row=$repo->findOneBy(['song'=>$song,'user'=>$userId]);if($row){$em->remove($row);$em->flush();}return $this->redirectToRoute('app_song_collaborators',['_locale'=>$request->getLocale(),'id'=>$song->getId()]);}
}
