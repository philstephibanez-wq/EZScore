<?php
declare(strict_types=1);

namespace App\Controller;

use App\Domain\Contact\ContactMessage;
use App\Domain\Contact\ContactMessageRepository;
use App\Domain\Song\SongRepository;
use App\Domain\User\User;
use App\Service\AdminRecipientResolver;
use Doctrine\ORM\EntityManagerInterface;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\DependencyInjection\Attribute\Autowire;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Mailer\MailerInterface;
use Symfony\Component\Mime\Email;
use Symfony\Component\Routing\Attribute\Route;

final class ContactController extends AbstractController
{
    #[Route('/contact-admin', name: 'app_contact_admin', methods: ['GET', 'POST'])]
    public function contact(
        Request $request,
        SongRepository $songs,
        ContactMessageRepository $messages,
        AdminRecipientResolver $adminRecipient,
        EntityManagerInterface $em,
        MailerInterface $mailer,
        #[Autowire('%env(MAILER_FROM)%')] string $fromEmail,
    ): Response {
        $user = $this->getUser();
        if (!$user instanceof User) {
            throw $this->createAccessDeniedException();
        }

        $songId = (int) $request->query->get('song', $request->request->get('song_id', 0));
        $song = $songId > 0 ? $songs->find($songId) : null;

        if ($request->isMethod('POST')) {
            if (!$this->isCsrfTokenValid('contact_admin', (string) $request->request->get('_token'))) {
                throw $this->createAccessDeniedException();
            }

            if ($messages->hasRecent($user, 60)) {
                $this->addFlash('error', 'Veuillez attendre une minute avant un nouvel envoi.');
            } else {
                $category = trim((string) $request->request->get('category', 'Autre'));
                $subject = trim((string) $request->request->get('subject', ''));
                $body = trim((string) $request->request->get('message', ''));

                if ($subject === '' || mb_strlen($subject) > 180 || mb_strlen($body) < 3 || mb_strlen($body) > 10000) {
                    $this->addFlash('error', 'Message invalide.');
                } else {
                    $record = new ContactMessage($user, $song, $category, $subject, $body);
                    $em->persist($record);
                    $em->flush();

                    try {
                        $admin = $adminRecipient->resolve();

                        $mail = (new Email())
                            ->from($fromEmail)
                            ->to($admin->getEmail())
                            ->replyTo($user->getEmail())
                            ->subject('[EZScore] '.$category.' — '.$subject)
                            ->text(
                                "Utilisateur: {$user->getDisplayName()} <{$user->getEmail()}>\n".
                                ($song ? "Chanson: {$song->getArtist()} — {$song->getTitle()} (#{$song->getId()})\n" : '').
                                "\n".$body
                            );

                        $mailer->send($mail);
                        $record->markSent();
                        $em->flush();

                        $this->addFlash('success', 'Message transmis à l’administrateur.');
                        return $this->redirectToRoute('app_contact_admin', ['_locale' => $request->getLocale()]);
                    } catch (\Throwable) {
                        $record->markFailed();
                        $em->flush();
                        $this->addFlash('error', 'Envoi impossible. Vérifiez MAILER_DSN puis réessayez.');
                    }
                }
            }
        }

        return $this->render('contact/admin.html.twig', ['song' => $song]);
    }
}
