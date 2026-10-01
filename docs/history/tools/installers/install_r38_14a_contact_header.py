#!/usr/bin/env python3
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else r"H:\EZScore_v1").resolve()

def main():
    base = ROOT / "templates/base.html.twig"
    catalog = ROOT / "templates/catalog/index.html.twig"
    contact = ROOT / "src/Controller/ContactController.php"
    public_tpl = ROOT / "templates/contact/public.html.twig"

    for p in (base, catalog, contact):
        if not p.is_file():
            raise SystemExit(f"Missing: {p}")

    cat = catalog.read_text(encoding="utf-8")
    block_re = re.compile(
        r"\n\{% if is_public_catalog %\}\n<section class=\"public-contact-panel\" id=\"contact-logandplay\">.*?</section>\n\{% endif %\}\n",
        re.S,
    )
    cat2, count = block_re.subn("\n", cat, count=1)
    if count == 1:
        catalog.write_text(cat2, encoding="utf-8")
        print("R38_14A_CATALOG_PANEL_REMOVED_OK")
    elif "data-public-contact-form" not in cat:
        print("R38_14A_CATALOG_PANEL_ALREADY_REMOVED")
    else:
        raise RuntimeError("Unable to remove public contact panel cleanly")

    base_text = base.read_text(encoding="utf-8")
    if "R38.14a public contact header" not in base_text:
        anchor = """            {% if public_catalog %}
                <a class="public-login-link" href="{{ path('app_login', {'_locale': app.request.locale}) }}">{{ 'auth.login.submit'|trans }}</a>
"""
        replacement = """            {% if public_catalog %}
                {# R38.14a public contact header #}
                <a class="public-login-link" href="{{ path('app_public_contact', {'_locale': app.request.locale}) }}">{{ app.request.locale == 'en' ? 'Contact LogAndPlay' : 'Contacter LogAndPlay' }}</a>
                <a class="public-login-link" href="{{ path('app_login', {'_locale': app.request.locale}) }}">{{ 'auth.login.submit'|trans }}</a>
"""
        if anchor not in base_text:
            raise RuntimeError("Public header anchor not found")
        base.write_text(base_text.replace(anchor, replacement, 1), encoding="utf-8")
        print("R38_14A_HEADER_LINK_OK")
    else:
        print("R38_14A_HEADER_LINK_ALREADY")

    src = contact.read_text(encoding="utf-8")
    src = src.replace(
        "#[Route('/contact-public', name: 'app_public_contact', methods: ['POST'])]",
        "#[Route('/contact-public', name: 'app_public_contact', methods: ['GET', 'POST'])]",
        1,
    )

    if "render('contact/public.html.twig')" not in src:
        old = """    ): Response {
        $locale = $request->getLocale();

        if (!$this->isCsrfTokenValid('public_contact', (string) $request->request->get('_token'))) {
            throw $this->createAccessDeniedException();
        }
"""
        new = """    ): Response {
        $locale = $request->getLocale();

        if ($request->isMethod('GET')) {
            return $this->render('contact/public.html.twig');
        }

        if (!$this->isCsrfTokenValid('public_contact', (string) $request->request->get('_token'))) {
            throw $this->createAccessDeniedException();
        }
"""
        if old not in src:
            raise RuntimeError("Public contact method body anchor not found")
        src = src.replace(old, new, 1)

    start = src.find("#[Route('/contact-public'")
    end = src.find("#[Route('/contact-admin'", start)
    if start < 0 or end < 0:
        raise RuntimeError("Public contact method boundaries not found")
    block = src[start:end].replace(
        "return $this->redirectToRoute('app_catalog', ['_locale' => $locale]);",
        "return $this->redirectToRoute('app_public_contact', ['_locale' => $locale]);",
    )
    src = src[:start] + block + src[end:]
    contact.write_text(src, encoding="utf-8")
    print("R38_14A_CONTACT_PAGE_ROUTE_OK")

    public_tpl.parent.mkdir(parents=True, exist_ok=True)
    public_tpl.write_text("""{% extends 'base.html.twig' %}
{% block title %}{{ app.request.locale == 'en' ? 'Contact LogAndPlay' : 'Contacter LogAndPlay' }} — EZScore_v1{% endblock %}
{% block stylesheets %}
<link rel="stylesheet" href="/assets/css/authentication.css?v=20260925r94">
<link rel="stylesheet" href="/assets/css/r38-14-public-development.css?v=20260928r38_14a">
{% endblock %}

{% block body %}
<section class="auth-card public-contact-page">
    <div class="eyebrow">LOGANDPLAY</div>
    <h1>{{ app.request.locale == 'en' ? 'Contact LogAndPlay' : 'Contacter LogAndPlay' }}</h1>
    <p>{{ app.request.locale == 'en'
        ? 'A question about EZScore or the project? Send a message to the administrator.'
        : 'Une question sur EZScore ou le projet ? Envoyez un message à l’administrateur.' }}</p>

    <form method="post" action="{{ path('app_public_contact', {'_locale': app.request.locale}) }}" class="form-grid" data-public-contact-form>
        <input type="hidden" name="_token" value="{{ csrf_token('public_contact') }}">
        <label>{{ app.request.locale == 'en' ? 'Name' : 'Nom' }}
            <input type="text" name="name" maxlength="120" required autocomplete="name">
        </label>
        <label>E-mail
            <input type="email" name="email" maxlength="180" required autocomplete="email">
        </label>
        <label>{{ app.request.locale == 'en' ? 'Subject' : 'Sujet' }}
            <input type="text" name="subject" maxlength="180" required>
        </label>
        <label>Message
            <textarea name="message" rows="6" maxlength="10000" required></textarea>
        </label>

        <label class="public-contact-honeypot" aria-hidden="true">
            Website
            <input type="text" name="website" tabindex="-1" autocomplete="off">
        </label>

        <button class="primary" type="submit">{{ app.request.locale == 'en' ? 'Send message' : 'Envoyer le message' }}</button>
    </form>

    <div class="auth-secondary-action" style="margin-top:16px">
        <a href="{{ path('app_catalog', {'_locale': app.request.locale}) }}">← {{ app.request.locale == 'en' ? 'Back to catalogue' : 'Retour au Répertoire' }}</a>
    </div>
</section>
{% endblock %}
""", encoding="utf-8")
    print("R38_14A_CONTACT_TEMPLATE_OK")
    print("R38_14A_INSTALL_OK")

if __name__ == "__main__":
    main()
