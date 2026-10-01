#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else r"H:\\EZScore_v1").resolve()

def replace_once(path: Path, old: str, new: str, label: str):
    text = path.read_text(encoding="utf-8")
    n = text.count(old)
    if n != 1:
        raise RuntimeError(f"{label}: expected 1 anchor, found {n} in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")

def main():
    base = ROOT/"templates/base.html.twig"
    catalog = ROOT/"templates/catalog/index.html.twig"
    login = ROOT/"templates/auth/login.html.twig"
    reg = ROOT/"src/Controller/RegistrationController.php"
    contact = ROOT/"src/Controller/ContactController.php"
    css = ROOT/"public/assets/css/r38-14-public-development.css"

    for p in [base,catalog,login,reg,contact]:
        if not p.is_file():
            raise SystemExit(f"Missing: {p}")

    if "R38.14 PUBLIC DEVELOPMENT MODE" not in reg.read_text(encoding="utf-8"):
        replace_once(
            reg,
            '''        if ($this->getUser()) {
            return $this->redirectToRoute('app_dashboard');
        }

        $errors = [];
''',
            '''        if ($this->getUser()) {
            return $this->redirectToRoute('app_dashboard');
        }

        // R38.14 PUBLIC DEVELOPMENT MODE: public registrations are temporarily closed.
        $this->addFlash('info', $request->getLocale() === 'en'
            ? 'Registrations will open soon.'
            : 'Les inscriptions ouvriront prochainement.');
        return $this->redirectToRoute('app_login', ['_locale' => $request->getLocale()]);

        $errors = [];
''',
            "registration lock"
        )
        print("R38_14_REGISTRATION_LOCK_OK")

    if "app_public_contact" not in contact.read_text(encoding="utf-8"):
        text = contact.read_text(encoding="utf-8")
        anchor = "\n    #[Route('/contact-admin', name: 'app_contact_admin', methods: ['GET', 'POST'])]\n"
        method = '''
    #[Route('/contact-public', name: 'app_public_contact', methods: ['POST'])]
    public function publicContact(
        Request $request,
        AdminRecipientResolver $adminRecipient,
        MailerInterface $mailer,
        #[Autowire('%env(MAILER_FROM)%')] string $fromEmail,
    ): Response {
        $locale = $request->getLocale();

        if (!$this->isCsrfTokenValid('public_contact', (string) $request->request->get('_token'))) {
            throw $this->createAccessDeniedException();
        }

        if (trim((string) $request->request->get('website', '')) !== '') {
            return $this->redirectToRoute('app_catalog', ['_locale' => $locale]);
        }

        $session = $request->getSession();
        $now = time();
        $last = (int) $session->get('ezscore_public_contact_last', 0);
        if ($last > 0 && ($now - $last) < 60) {
            $this->addFlash('error', $locale === 'en'
                ? 'Please wait one minute before sending another message.'
                : 'Veuillez attendre une minute avant un nouvel envoi.');
            return $this->redirectToRoute('app_catalog', ['_locale' => $locale]);
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
            return $this->redirectToRoute('app_catalog', ['_locale' => $locale]);
        }

        try {
            $admin = $adminRecipient->resolve();
            $mail = (new Email())
                ->from($fromEmail)
                ->to($admin->getEmail())
                ->replyTo($email)
                ->subject('[EZScore public] '.$subject)
                ->text(
                    "Contact public EZScore / LogAndPlay\n".
                    "Nom: {$name}\n".
                    "E-mail: {$email}\n\n".
                    $body
                );

            $mailer->send($mail);
            $session->set('ezscore_public_contact_last', $now);
            $this->addFlash('success', $locale === 'en'
                ? 'Your message has been sent to LogAndPlay.'
                : 'Votre message a été transmis à LogAndPlay.');
        } catch (\\Throwable) {
            $this->addFlash('error', $locale === 'en'
                ? 'Unable to send the message right now.'
                : 'Envoi impossible pour le moment.');
        }

        return $this->redirectToRoute('app_catalog', ['_locale' => $locale]);
    }
'''
        if anchor not in text:
            raise RuntimeError("contact controller anchor not found")
        contact.write_text(text.replace(anchor, "\n"+method+anchor, 1), encoding="utf-8")
        print("R38_14_PUBLIC_CONTACT_CONTROLLER_OK")

    cat = catalog.read_text(encoding="utf-8")
    if "r38-14-public-development.css" not in cat:
        cat = cat.replace(
            '<link rel="stylesheet" href="/assets/css/catalog-r13.css?v=20260925r21">\n',
            '<link rel="stylesheet" href="/assets/css/catalog-r13.css?v=20260925r21">\n<link rel="stylesheet" href="/assets/css/r38-14-public-development.css?v=20260928r38_14">\n',
            1
        )
    if "data-public-development-banner" not in cat:
        cat = cat.replace(
            '<section class="catalog-hero">\n    <div class="catalog-hero-copy">\n',
            '''<section class="catalog-hero">
    <div class="public-development-banner" data-public-development-banner>
        <strong>{{ app.request.locale == 'en' ? 'Site under development' : 'Site en développement' }}</strong>
        <span>{{ app.request.locale == 'en'
            ? 'EZScore is currently being finalized. Existing accounts can sign in; new registrations will open soon.'
            : 'EZScore est actuellement en cours de finalisation. Les comptes existants peuvent se connecter ; les nouvelles inscriptions ouvriront prochainement.' }}</span>
    </div>
    <div class="catalog-hero-copy">
''',
            1
        )
        print("R38_14_HOME_BANNER_OK")
    cat = cat.replace(
        '''            <a class="catalog-cta primary-cta" href="{{ path('app_register', {'_locale': app.request.locale}) }}">{{ 'catalog.public.register'|trans }}</a>
''',
        '''            <span class="catalog-cta primary-cta registration-disabled" aria-disabled="true">{{ app.request.locale == 'en' ? 'Registrations coming soon' : 'Inscriptions prochainement' }}</span>
''',
        1
    )
    if "data-public-contact-form" not in cat:
        panel = '''
{% if is_public_catalog %}
<section class="public-contact-panel" id="contact-logandplay">
    <div class="public-contact-copy">
        <div class="eyebrow">LOGANDPLAY</div>
        <h2>{{ app.request.locale == 'en' ? 'Contact LogAndPlay' : 'Contacter LogAndPlay' }}</h2>
        <p>{{ app.request.locale == 'en'
            ? 'A question about EZScore or the project? Send a message directly to the administrator.'
            : 'Une question sur EZScore ou le projet ? Envoyez directement un message à l’administrateur.' }}</p>
    </div>
    <form method="post" action="{{ path('app_public_contact', {'_locale': app.request.locale}) }}" class="public-contact-form" data-public-contact-form>
        <input type="hidden" name="_token" value="{{ csrf_token('public_contact') }}">
        <label><span>{{ app.request.locale == 'en' ? 'Name' : 'Nom' }}</span><input type="text" name="name" maxlength="120" required autocomplete="name"></label>
        <label><span>E-mail</span><input type="email" name="email" maxlength="180" required autocomplete="email"></label>
        <label class="public-contact-full"><span>{{ app.request.locale == 'en' ? 'Subject' : 'Sujet' }}</span><input type="text" name="subject" maxlength="180" required></label>
        <label class="public-contact-full"><span>Message</span><textarea name="message" rows="5" maxlength="10000" required></textarea></label>
        <label class="public-contact-honeypot" aria-hidden="true"><span>Website</span><input type="text" name="website" tabindex="-1" autocomplete="off"></label>
        <div class="public-contact-actions public-contact-full"><button type="submit">{{ app.request.locale == 'en' ? 'Send message' : 'Envoyer le message' }}</button></div>
    </form>
</section>
{% endif %}
'''
        anchor = '\n<div class="catalog-song-grid">\n'
        if anchor not in cat:
            raise RuntimeError("catalog grid anchor not found")
        cat = cat.replace(anchor, "\n"+panel+anchor, 1)
        print("R38_14_PUBLIC_CONTACT_FORM_OK")
    catalog.write_text(cat, encoding="utf-8")

    base_text = base.read_text(encoding="utf-8")
    base_text = base_text.replace(
        '''                <a class="public-register-link" href="{{ path('app_register', {'_locale': app.request.locale}) }}">{{ 'registration.register_link'|trans }}</a>
''',
        '''                <span class="public-register-link registration-disabled" aria-disabled="true">{{ app.request.locale == 'en' ? 'Registrations coming soon' : 'Inscriptions prochainement' }}</span>
''',
        1
    )
    base.write_text(base_text, encoding="utf-8")

    login_text = login.read_text(encoding="utf-8")
    login_text = login_text.replace(
        '''    <div class="auth-secondary-action">
        <span>{{ 'registration.login_prompt'|trans({}, 'registration') }}</span>
        <a href="{{ path('app_register', {'_locale': app.request.locale}) }}">{{ 'registration.register_link'|trans({}, 'registration') }}</a>
    </div>
''',
        '''    <div class="auth-secondary-action">
        <span>{{ app.request.locale == 'en' ? 'Registrations coming soon' : 'Inscriptions prochainement' }}</span>
    </div>
''',
        1
    )
    login.write_text(login_text, encoding="utf-8")

    css.parent.mkdir(parents=True, exist_ok=True)
    css.write_text('''.public-development-banner{grid-column:1/-1;display:flex;gap:12px;align-items:center;padding:12px 16px;margin-bottom:4px;border:1px solid rgba(111,225,215,.42);border-radius:12px;background:rgba(15,93,87,.18);color:#d9fff9}
.public-development-banner strong{white-space:nowrap}
.public-development-banner span{color:#b9d6d4;font-size:13px}
.registration-disabled{cursor:not-allowed;opacity:.72;pointer-events:none}
.public-contact-panel{margin:18px 0 28px;padding:22px;border:1px solid #2a3c45;border-radius:16px;background:#111b21;display:grid;grid-template-columns:minmax(220px,.8fr) minmax(360px,1.4fr);gap:28px}
.public-contact-copy h2{margin:6px 0 8px;font-size:26px}
.public-contact-copy p{margin:0;color:#9fc1c0;line-height:1.5}
.public-contact-form{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.public-contact-form label{display:grid;gap:6px;color:#dce9e8;font-weight:700;font-size:13px}
.public-contact-form input,.public-contact-form textarea{width:100%;box-sizing:border-box;border:1px solid #334751;border-radius:10px;background:#0c151a;color:#f4fbfb;padding:11px 12px;font:inherit}
.public-contact-form textarea{resize:vertical;min-height:110px}
.public-contact-full{grid-column:1/-1}
.public-contact-actions{display:flex;justify-content:flex-end}
.public-contact-actions button{border:1px solid #6fe1d7;border-radius:10px;background:#126b63;color:#fff;padding:10px 18px;font-weight:800;cursor:pointer}
.public-contact-honeypot{position:absolute!important;left:-10000px!important;width:1px!important;height:1px!important;overflow:hidden!important}
@media(max-width:760px){.public-development-banner{align-items:flex-start;flex-direction:column}.public-contact-panel{grid-template-columns:1fr}.public-contact-form{grid-template-columns:1fr}}
''', encoding="utf-8")
    print("R38_14_INSTALL_OK")

if __name__ == "__main__":
    main()
