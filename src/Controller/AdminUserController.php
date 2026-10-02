<?php

declare(strict_types=1);

namespace App\Controller;

use App\Domain\User\User;
use App\Domain\User\UserRepository;
use App\Service\ListPagination;
use App\Service\UserDeletionService;
use App\Service\UserManager;
use App\Service\Exception\ActivationMailException;
use App\Service\RegistrationMailer;
use App\Service\RegistrationService;
use Doctrine\ORM\EntityManagerInterface;
use Symfony\Contracts\Translation\TranslatorInterface;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;

#[Route('/admin/users')]
final class AdminUserController extends AbstractController
{
    #[Route('', name: 'admin_users', methods: ['GET', 'POST'])]
    public function index(
        Request $request,
        UserRepository $users,
        UserManager $manager,
        ListPagination $pagination,
    ): Response {
        if ($request->isMethod('POST')) {
            if (!$this->isCsrfTokenValid('create_user', (string) $request->request->get('_token'))) {
                throw $this->createAccessDeniedException();
            }

            $name = trim((string) $request->request->get('display_name'));
            $email = mb_strtolower(trim((string) $request->request->get('email')));
            $password = (string) $request->request->get('password');
            $role = (string) $request->request->get('role', 'ROLE_READER');
            $locale = (string) $request->request->get('locale', 'fr');

            $errors = $this->validateIdentity($name, $email);
            if ($users->findOneBy(['email' => $email]) !== null) $errors[] = 'users.error.email_used';
            if ($password !== '' && mb_strlen($password) < 10) $errors[] = 'users.error.password_length';
            if (!in_array($locale, User::SUPPORTED_LOCALES, true)) {
                throw new \InvalidArgumentException(sprintf('Unsupported locale "%s".', $locale));
            }

            if ($errors === []) {
                $manager->create($name, $email, $password !== '' ? $password : null, $role, $locale);
                $this->addFlash('success', 'users.created');
                return $this->redirectToRoute('admin_users', ['_locale' => $request->getLocale()]);
            }

            foreach ($errors as $error) $this->addFlash('error', $error);
        }

        $query = $pagination->query($request);
        $letter = $pagination->letter($request);
        $role = (string) $request->query->get('role', '');
        $active = (string) $request->query->get('active', '');
        $google = (string) $request->query->get('google', '');
        $locale = (string) $request->query->get('locale', '');

        $qb = $users->createQueryBuilder('u');

        if ($query !== '') {
            $qb->andWhere('(LOWER(u.displayName) LIKE :q OR LOWER(u.email) LIKE :q)')
                ->setParameter('q', '%'.mb_strtolower($query).'%');
        }

        if ($letter !== null) {
            $qb->andWhere('UPPER(SUBSTRING(u.displayName, 1, 1)) = :letter')
                ->setParameter('letter', $letter);
        }

        if (in_array($role, ['ROLE_READER', 'ROLE_EDITOR', 'ROLE_ADMIN', 'ROLE_DISPLAY'], true)) {
            $qb->andWhere('u.roles LIKE :role')->setParameter('role', '%'.$role.'%');
        }

        if ($active === '1') $qb->andWhere('u.active = true');
        elseif ($active === '0') $qb->andWhere('u.active = false');

        if ($google === 'linked') $qb->andWhere('u.googleSub IS NOT NULL');
        elseif ($google === 'local') $qb->andWhere('u.googleSub IS NULL');

        if (in_array($locale, User::SUPPORTED_LOCALES, true)) {
            $qb->andWhere('u.locale = :locale')->setParameter('locale', $locale);
        }

        $qb->orderBy('LOWER(u.displayName)', 'ASC')
            ->addOrderBy('LOWER(u.email)', 'ASC');

        $pager = $pagination->paginate($qb, $request, 'u', 'page', 50);

        return $this->render('admin/users.html.twig', [
            'users' => $pager['rows'],
            'pager' => $pager,
            'supported_locales' => User::SUPPORTED_LOCALES,
            'alphabet' => $pagination->alphabet(),
            'filters' => [
                'q' => $query,
                'letter' => $letter,
                'role' => $role,
                'active' => $active,
                'google' => $google,
                'locale' => $locale,
            ],
        ]);
    }

    #[Route('/{id}/update', name: 'admin_user_update', requirements: ['id' => '\\d+'], methods: ['POST'])]
    public function update(User $user, Request $request, UserRepository $users, UserManager $manager): Response
    {
        if (!$this->isCsrfTokenValid('user_'.$user->getId(), (string) $request->request->get('_token'))) {
            throw $this->createAccessDeniedException();
        }

        $name = trim((string) $request->request->get('display_name'));
        $email = mb_strtolower(trim((string) $request->request->get('email')));
        $password = (string) $request->request->get('password');
        $role = (string) $request->request->get('role', 'ROLE_READER');
        $locale = (string) $request->request->get('locale', 'fr');
        $active = $request->request->getBoolean('active');

        $errors = $this->validateIdentity($name, $email);
        $emailOwner = $users->findOneBy(['email' => $email]);
        if ($emailOwner !== null && $emailOwner->getId() !== $user->getId()) $errors[] = 'users.error.email_used';
        if ($password !== '' && mb_strlen($password) < 10) $errors[] = 'users.error.password_length_new';
        if (!in_array($locale, User::SUPPORTED_LOCALES, true)) {
            throw new \InvalidArgumentException(sprintf('Unsupported locale "%s".', $locale));
        }

        $wasActiveAdmin = $user->isActive() && $user->getPrimaryRole() === 'ROLE_ADMIN';
        $willRemainActiveAdmin = $active && $role === 'ROLE_ADMIN';
        if ($wasActiveAdmin && !$willRemainActiveAdmin && $users->countActiveAdmins() <= 1) {
            $errors[] = 'users.error.last_admin';
        }

        if ($errors !== []) {
            foreach ($errors as $error) $this->addFlash('error', $error);
            return $this->redirectToRoute('admin_users', $this->returnFilters($request));
        }

        $actor = $this->getUser();
        $manager->update(
            $user,
            $name,
            $email,
            $role,
            $active,
            $password !== '' ? $password : null,
            $locale,
        );

        if ($actor instanceof User && $actor->getId() === $user->getId()) {
            $request->getSession()->set('_locale', $locale);
            $request->setLocale($locale);
        }

        $this->addFlash('success', 'users.updated');
        return $this->redirectToRoute('admin_users', $this->returnFilters($request));
    }

    #[Route('/{id}/activation/resend', name: 'admin_user_activation_resend', requirements: ['id' => '\\d+'], methods: ['POST'])]
    public function resendActivation(
        User $user,
        Request $request,
        RegistrationService $registration,
        RegistrationMailer $mailer,
        TranslatorInterface $translator,
    ): Response {
        if (!$this->isCsrfTokenValid(
            'resend_activation_user_'.$user->getId(),
            (string) $request->request->get('_token'),
        )) {
            throw $this->createAccessDeniedException();
        }

        if ($user->isEmailVerified()) {
            $this->addFlash('success', $translator->trans('admin_users.activation.already_verified', [], 'admin_users'));
            return $this->redirectToRoute('admin_users', $this->returnFilters($request));
        }

        $result = $registration->forceRenewActivationForUser($user);

        try {
            if ($result !== null) {
                $mailer->sendActivation($result['user'], $result['token']);
            }
            $this->addFlash('success', $translator->trans('admin_users.activation.resend_sent', [], 'admin_users'));
        } catch (ActivationMailException) {
            $this->addFlash('error', $translator->trans('admin_users.activation.resend_failed', [], 'admin_users'));
        }

        return $this->redirectToRoute('admin_users', $this->returnFilters($request));
    }

    #[Route('/{id}/activation/verify', name: 'admin_user_activation_verify', requirements: ['id' => '\\d+'], methods: ['POST'])]
    public function verifyEmailManually(
        User $user,
        Request $request,
        EntityManagerInterface $em,
        TranslatorInterface $translator,
    ): Response {
        if (!$this->isCsrfTokenValid(
            'verify_email_user_'.$user->getId(),
            (string) $request->request->get('_token'),
        )) {
            throw $this->createAccessDeniedException();
        }

        if (!$user->isEmailVerified()) {
            $user->markEmailVerifiedForManagedAccount();
            $em->flush();
        }

        $this->addFlash('success', $translator->trans('admin_users.activation.manual_verified', [], 'admin_users'));
        return $this->redirectToRoute('admin_users', $this->returnFilters($request));
    }

    #[Route('/{id}/delete', name: 'admin_user_delete', requirements: ['id' => '\\d+'], methods: ['POST'])]
    public function delete(User $user, Request $request, UserDeletionService $deletion): Response
    {
        if (!$this->isCsrfTokenValid('delete_user_'.$user->getId(), (string) $request->request->get('_token'))) {
            throw $this->createAccessDeniedException();
        }

        $actor = $this->getUser();
        if (!$actor instanceof User) throw $this->createAccessDeniedException();

        try {
            $deletion->delete($user, $actor);
            $this->addFlash('success', 'users.deleted');
        } catch (\DomainException $exception) {
            $this->addFlash('error', $exception->getMessage());
        }

        return $this->redirectToRoute('admin_users', $this->returnFilters($request));
    }

    /** @return array<string,string|int> */
    private function returnFilters(Request $request): array
    {
        $params = ['_locale' => $request->getLocale()];
        foreach (['q', 'letter', 'role', 'active', 'google', 'locale', 'page'] as $key) {
            $value = trim((string) $request->request->get('filter_'.$key, ''));
            if ($value !== '') $params[$key] = $key === 'page' ? max(1, (int) $value) : $value;
        }
        return $params;
    }

    /** @return list<string> */
    private function validateIdentity(string $name, string $email): array
    {
        $errors = [];
        if ($name === '') $errors[] = 'users.error.name';
        if (!filter_var($email, FILTER_VALIDATE_EMAIL)) $errors[] = 'users.error.email';
        return $errors;
    }
}
