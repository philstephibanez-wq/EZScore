#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else r"H:\EZScore_v1").resolve()

def main() -> int:
    security = ROOT/"config/packages/security.yaml"
    controller = ROOT/"src/Controller/ContactController.php"
    template = ROOT/"templates/contact/public.html.twig"
    env_example = ROOT/".env.example"

    for path in (security, controller, template):
        if not path.is_file():
            raise SystemExit(f"Missing prerequisite: {path}. Install R38.14 + R38.14a first.")

    sec = security.read_text(encoding="utf-8")
    if "R38.14b public contact" not in sec:
        anchor = "        - { path: ^/locale/, roles: PUBLIC_ACCESS }\n"
        addition = (
            anchor +
            "        # R38.14b public contact\n"
            "        - { path: ^/contact-public$, roles: PUBLIC_ACCESS, methods: [GET, POST] }\n"
            "        - { path: ^/(fr|en)/contact-public$, roles: PUBLIC_ACCESS, methods: [GET, POST] }\n"
        )
        if anchor not in sec:
            raise RuntimeError("security anchor not found")
        security.write_text(sec.replace(anchor, addition, 1), encoding="utf-8")
        print("R38_14B_PUBLIC_ROUTE_OK")

    src = controller.read_text(encoding="utf-8")
    if "use App\\Service\\PublicContactRateLimiter;" not in src:
        src = src.replace(
            "use App\\Service\\AdminRecipientResolver;\n",
            "use App\\Service\\AdminRecipientResolver;\nuse App\\Service\\PublicContactRateLimiter;\nuse App\\Service\\TurnstileVerifier;\n",
            1,
        )

    if "TurnstileVerifier $turnstile" not in src:
        old = """    public function publicContact(
        Request $request,
        AdminRecipientResolver $adminRecipient,
"""
        new = """    public function publicContact(
        Request $request,
        TurnstileVerifier $turnstile,
        PublicContactRateLimiter $rateLimiter,
        AdminRecipientResolver $adminRecipient,
"""
        if old not in src:
            raise RuntimeError("publicContact signature anchor not found")
        src = src.replace(old, new, 1)

    if "'turnstile_site_key'" not in src:
        old = """        if ($request->isMethod('GET')) {
            return $this->render('contact/public.html.twig');
        }
"""
        new = """        if ($request->isMethod('GET')) {
            return $this->render('contact/public.html.twig', [
                'turnstile_site_key' => $turnstile->siteKey(),
                'turnstile_configured' => $turnstile->isConfigured(),
            ]);
        }
"""
        if old not in src:
            raise RuntimeError("GET render anchor not found")
        src = src.replace(old, new, 1)

    if "cf-turnstile-response" not in src:
        anchor = """        if (trim((string) $request->request->get('website', '')) !== '') {
            return $this->redirectToRoute('app_public_contact', ['_locale' => $locale]);
        }

"""
        block = anchor + """        $clientIp = (string) ($request->getClientIp() ?? 'unknown');
        $turnstileToken = (string) $request->request->get('cf-turnstile-response', '');
        if (!$turnstile->verify($turnstileToken, $clientIp)) {
            $this->addFlash('error', $locale === 'en'
                ? 'Anti-spam verification failed. Please try again.'
                : 'La vérification anti-spam a échoué. Veuillez réessayer.');
            return $this->redirectToRoute('app_public_contact', ['_locale' => $locale]);
        }

"""
        if anchor not in src:
            raise RuntimeError("honeypot anchor not found")
        src = src.replace(anchor, block, 1)

    if "$rateLimiter->consume(" not in src:
        anchor = """            return $this->redirectToRoute('app_public_contact', ['_locale' => $locale]);
        }

        try {
            $admin = $adminRecipient->resolve();
"""
        block = """            return $this->redirectToRoute('app_public_contact', ['_locale' => $locale]);
        }

        if (!$rateLimiter->consume($clientIp, $email)) {
            $this->addFlash('error', $locale === 'en'
                ? 'Too many messages. Please try again later.'
                : 'Trop de messages ont été envoyés. Veuillez réessayer plus tard.');
            return $this->redirectToRoute('app_public_contact', ['_locale' => $locale]);
        }

        try {
            $admin = $adminRecipient->resolve();
"""
        if anchor not in src:
            raise RuntimeError("rate-limit anchor not found")
        src = src.replace(anchor, block, 1)

    controller.write_text(src, encoding="utf-8")
    print("R38_14B_CONTROLLER_OK")

    tpl = template.read_text(encoding="utf-8")
    if "challenges.cloudflare.com/turnstile/v0/api.js" not in tpl:
        tpl = tpl.replace(
            "{% block stylesheets %}\n",
            "{% block stylesheets %}\n<script src=\"https://challenges.cloudflare.com/turnstile/v0/api.js\" async defer></script>\n",
            1,
        )

    if "class=\"cf-turnstile\"" not in tpl:
        anchor = """        <label class="public-contact-honeypot" aria-hidden="true">
            Website
            <input type="text" name="website" tabindex="-1" autocomplete="off">
        </label>

        <button class="primary" type="submit">"""
        block = """        <label class="public-contact-honeypot" aria-hidden="true">
            Website
            <input type="text" name="website" tabindex="-1" autocomplete="off">
        </label>

        {% if turnstile_configured %}
            <div class="cf-turnstile" data-sitekey="{{ turnstile_site_key }}" data-theme="dark"></div>
        {% else %}
            <div class="flash flash-error">{{ app.request.locale == 'en'
                ? 'Anti-spam protection is not configured yet.'
                : 'La protection anti-spam n’est pas encore configurée.' }}</div>
        {% endif %}

        <button class="primary" type="submit" {{ not turnstile_configured ? 'disabled' : '' }}>"""
        if anchor not in tpl:
            raise RuntimeError("Turnstile template anchor not found")
        tpl = tpl.replace(anchor, block, 1)

    template.write_text(tpl, encoding="utf-8")
    print("R38_14B_TURNSTILE_UI_OK")

    if env_example.is_file():
        env = env_example.read_text(encoding="utf-8")
        if "TURNSTILE_SITE_KEY" not in env:
            env += "\n# Cloudflare Turnstile - public contact form\nTURNSTILE_SITE_KEY=\nTURNSTILE_SECRET_KEY=\n"
            env_example.write_text(env, encoding="utf-8")
            print("R38_14B_ENV_EXAMPLE_OK")

    print("R38_14B_INSTALL_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
