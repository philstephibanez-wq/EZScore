<?php
declare(strict_types=1);

namespace App\Service;

use Symfony\Contracts\HttpClient\HttpClientInterface;

final class TurnstileVerifier
{
    private const VERIFY_URL = 'https://challenges.cloudflare.com/turnstile/v0/siteverify';

    public function __construct(private readonly HttpClientInterface $http)
    {
    }

    public function siteKey(): string
    {
        return trim((string) ($_ENV['TURNSTILE_SITE_KEY'] ?? $_SERVER['TURNSTILE_SITE_KEY'] ?? ''));
    }

    public function isConfigured(): bool
    {
        return $this->siteKey() !== '' && $this->secretKey() !== '';
    }

    public function verify(string $token, ?string $remoteIp): bool
    {
        $secret = $this->secretKey();
        if ($secret === '' || trim($token) === '') {
            return false;
        }

        try {
            $body = [
                'secret' => $secret,
                'response' => trim($token),
            ];
            if (is_string($remoteIp) && $remoteIp !== '') {
                $body['remoteip'] = $remoteIp;
            }

            $response = $this->http->request('POST', self::VERIFY_URL, [
                'body' => $body,
                'timeout' => 5.0,
            ]);
            $data = $response->toArray(false);

            return ($data['success'] ?? false) === true;
        } catch (\Throwable) {
            return false;
        }
    }

    private function secretKey(): string
    {
        return trim((string) ($_ENV['TURNSTILE_SECRET_KEY'] ?? $_SERVER['TURNSTILE_SECRET_KEY'] ?? ''));
    }
}
