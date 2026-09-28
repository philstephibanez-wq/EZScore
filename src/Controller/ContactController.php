<?php
declare(strict_types=1);

namespace App\Controller;

use App\Domain\Contact\ContactMessage;
use App\Domain\Contact\ContactMessageRepository;
use App\Domain\Song\SongRepository;
use App\Domain\User\User;
use App\Service\AdminRecipientResolver;
use App\Service\PublicContactRateLimiter;
use App\Service\TurnstileVerifier;
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

    #[Route('/contact-public', name: 'app_public_contact', methods: ['GET', 'POST'])]
    public function publicContact(
        Request $request,
        TurnstileVerifier $turnstile,
        PublicContactRateLimiter $rateLimiter,
        AdminRecipientResolver $adminRecipient,
        MailerInterface $mailer,
        #[Autowire('%env(MAILER_FROM)%')] string $fromEmail,
    ): Response {
        $locale = $request->getLocale();

        if ($request->isMethod('GET')) {
            return $this->render('contact/public.html.twig', [
                'turnstile_site_key' => $turnstile->siteKey(),
                'turnstile_configured' => $turnstile->isConfigured(),
            ]);
        }

        if (!$this->isCsrfTokenValid('public_contact', (string) $request->request->get('_token'))) {
            throw $this->createAccessDeniedException();
        }

        if (trim((string) $request->request->get('website', '')) !== '') {
            return $this->redirectToRoute('app_public_contact', ['_locale' => $locale]);
        }

        $clientIp = (string) ($request->getClientIp() ?? 'unknown');
        $turnstileToken = (string) $request->request->get('cf-turnstile-response', '');
        if (!$turnstile->verify($turnstileToken, $clientIp)) {
            $this->addFlash('error', $locale === 'en'
                ? 'Anti-spam verification failed. Please try again.'
                : 'La vérification anti-spam a échoué. Veuillez réessayer.');
            return $this->redirectToRoute('app_public_contact', ['_locale' => $locale]);
        }

        $session = $request->getSession();
        $now = time();
        $last = (int) $session->get('ezscore_public_contact_last', 0);
        if ($last > 0 && ($now - $last) < 60) {
            $this->addFlash('error', $locale === 'en'
                ? 'Please wait one minute before sending another message.'
                : 'Veuillez attendre une minute avant un nouvel envoi.');
            return $this->redirectToRoute('app_public_contact', ['_locale' => $locale]);
        }

        $name = trim((string) $request->request->get('name', ''));
        $email = mb_strtolower(trim((string) $request->request->get('email', '')));
        $subject = trim((string) $request->request->get('subject', ''));
        $body = trim((string) $request->request->get('message', ''));

        if (
            $name === '' || mb_strlen($name) > 120 ||
            !filter_var($email, FILTER_VALIDATE_EMAIL) ||
            $subject === '' || mb_strlen($subject) > 180 ||
            mb_strlen($body) < 3 || mb_strlen($body) > 10000
        ) {
            $this->addFlash('error', $locale === 'en' ? 'Invalid message.' : 'Message invalide.');
            return $this->redirectToRoute('app_public_contact', ['_locale' => $locale]);
        }

        if (!$rateLimiter->consume($clientIp, $email)) {
            $this->addFlash('error', $locale === 'en'
                ? 'Too many messages. Please try again later.'
                : 'Trop de messages ont été envoyés. Veuillez réessayer plus tard.');
            return $this->redirectToRoute('app_public_contact', ['_locale' => $locale]);
        }

        try {
            $admin = $adminRecipient->resolve();
            $mail = (new Email())
                ->from($fromEmail)
                ->to($admin->getEmail())
                ->replyTo($email)
                ->subject('[EZScore public] '.$subject)
                ->text(
                    "Contact public EZScore / LogAndPlay
".
                    "Nom: {$name}
".
                    "E-mail: {$email}

".
                    $body
                );

            $mailer->send($mail);
            $session->set('ezscore_public_contact_last', $now);
            $this->addFlash('success', $locale === 'en'
                ? 'Your message has been sent to LogAndPlay.'
                : 'Votre message a été transmis à LogAndPlay.');
        } catch (\Throwable) {
            $this->addFlash('error', $locale === 'en'
                ? 'Unable to send the message right now.'
                : 'Envoi impossible pour le moment.');
        }

        return $this->redirectToRoute('app_public_contact', ['_locale' => $locale]);
    }

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
