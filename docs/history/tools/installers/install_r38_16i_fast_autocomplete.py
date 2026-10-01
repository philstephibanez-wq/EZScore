#!/usr/bin/env python3
from __future__ import annotations
import re, sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else r"H:\EZScore_v1").resolve()
CLIENT = ROOT / "src/Service/LyricsOvhClient.php"
CONTROLLER = ROOT / "src/Controller/LyricsOvhController.php"
JS = ROOT / "public/assets/js/lyrics-ovh-r38-16.js"
TEMPLATE = ROOT / "templates/song/lyricslab.html.twig"

FAST_METHOD = r'''
    /**
     * Lightweight suggestions for live autocomplete.
     * No /v1 lyrics availability checks are performed here.
     *
     * @return list<array{artist:string,title:string,album:?string,cover:?string}>
     */
    public function suggestFast(string $query, int $limit = 6): array
    {
        $query = trim($query);
        if (mb_strlen($query) < 2) {
            return [];
        }

        try {
            $response = $this->http->request(
                'GET',
                self::BASE_URL.'/suggest/'.rawurlencode($query),
                [
                    'timeout' => 4.0,
                    'headers' => ['Accept' => 'application/json'],
                ],
            );
            if ($response->getStatusCode() !== 200) {
                return [];
            }
            $payload = $response->toArray(false);
        } catch (\\Throwable) {
            return [];
        }

        $rows = is_array($payload['data'] ?? null) ? $payload['data'] : [];
        $results = [];
        $seen = [];

        foreach ($rows as $row) {
            if (!is_array($row)) {
                continue;
            }
            $artist = trim((string) ($row['artist']['name'] ?? ''));
            $title = trim((string) ($row['title'] ?? ''));
            if ($artist === '' || $title === '') {
                continue;
            }
            $key = mb_strtolower($artist."\\n".$title);
            if (isset($seen[$key])) {
                continue;
            }
            $seen[$key] = true;
            $results[] = [
                'artist' => $artist,
                'title' => $title,
                'album' => isset($row['album']['title']) ? trim((string) $row['album']['title']) : null,
                'cover' => isset($row['album']['cover_small']) ? trim((string) $row['album']['cover_small']) : null,
            ];
            if (count($results) >= max(1, min(8, $limit))) {
                break;
            }
        }
        return $results;
    }

'''

AUTOCOMPLETE_ROUTE = r'''
    #[Route('/autocomplete', name: 'app_song_lyrics_ovh_autocomplete', methods: ['POST'])]
    public function autocomplete(Song $song, Request $request, LyricsOvhClient $client): JsonResponse
    {
        $this->requireEditor($song);
        $payload = $request->toArray();

        if (!$this->isCsrfTokenValid(
            'song_lyrics_ovh_'.$song->getId(),
            (string) ($payload['_token'] ?? ''),
        )) {
            return $this->json(['error' => 'invalid_csrf'], Response::HTTP_FORBIDDEN);
        }

        $query = trim((string) ($payload['query'] ?? ''));
        if (mb_strlen($query) < 2 || mb_strlen($query) > 180) {
            return $this->json(['ok' => true, 'results' => []]);
        }

        return $this->json([
            'ok' => true,
            'results' => $client->suggestFast($query, 6),
        ]);
    }

'''

def main() -> int:
    for path in (CLIENT, CONTROLLER, JS, TEMPLATE):
        if not path.is_file():
            raise RuntimeError(f"Missing prerequisite: {path}")

    client = CLIENT.read_text(encoding="utf-8")
    controller = CONTROLLER.read_text(encoding="utf-8")
    js = JS.read_text(encoding="utf-8")
    template = TEMPLATE.read_text(encoding="utf-8")

    if "public function suggestFast(" not in client:
        pos = client.find("    public function fetchLyrics(")
        if pos < 0:
            raise RuntimeError("LyricsOvhClient fetchLyrics anchor not found")
        client = client[:pos] + FAST_METHOD + client[pos:]

    if "app_song_lyrics_ovh_autocomplete" not in controller:
        pos = controller.find("    #[Route('/search', name: 'app_song_lyrics_ovh_search', methods: ['POST'])]")
        if pos < 0:
            raise RuntimeError("LyricsOvhController search route anchor not found")
        controller = controller[:pos] + AUTOCOMPLETE_ROUTE + controller[pos:]

    if "data-autocomplete-url=" not in template:
        anchor = "                 data-search-url=\"{{ path('app_song_lyrics_ovh_search', {'_locale': app.request.locale, id: song.id}) }}\"\n"
        if anchor not in template:
            raise RuntimeError("Lyrics.ovh toolbar search URL anchor not found")
        addition = anchor + "                 data-autocomplete-url=\"{{ path('app_song_lyrics_ovh_autocomplete', {'_locale': app.request.locale, id: song.id}) }}\"\n"
        template = template.replace(anchor, addition, 1)

    if "const autocompleteUrl =" not in js:
        anchor = "const searchUrl = root.dataset.searchUrl || '';\n"
        if anchor not in js:
            raise RuntimeError("Lyrics.ovh JS searchUrl anchor not found")
        js = js.replace(anchor, anchor + "const autocompleteUrl = root.dataset.autocompleteUrl || searchUrl;\nconst autocompleteCache = new Map();\n", 1)

    pattern = re.compile(r"async function autocompleteSearch\(\) \{.*?\n\}\n\nfunction scheduleAutocomplete\(\) \{.*?\n\}", re.S)
    match = pattern.search(js)
    if not match:
        raise RuntimeError("R38.16h autocomplete function block not found")

    replacement = r'''async function autocompleteSearch() {
  const query = String(input?.value || '').trim();
  const cacheKey = query.toLocaleLowerCase();

  if (query.length < 2) {
    closeAutocomplete();
    return;
  }

  if (autocompleteCache.has(cacheKey)) {
    renderAutocomplete(autocompleteCache.get(cacheKey));
    return;
  }

  if (autocompleteAbort) autocompleteAbort.abort();
  autocompleteAbort = new AbortController();

  try {
    const response = await fetch(autocompleteUrl, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {'Content-Type':'application/json', 'Accept':'application/json'},
      body: JSON.stringify({_token: token, query}),
      signal: autocompleteAbort.signal
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || `http_${response.status}`);

    const results = Array.isArray(data.results) ? data.results : [];
    autocompleteCache.set(cacheKey, results);
    if (autocompleteCache.size > 40) {
      const oldest = autocompleteCache.keys().next().value;
      autocompleteCache.delete(oldest);
    }
    renderAutocomplete(results);
  } catch (error) {
    if (error.name !== 'AbortError') {
      console.error('Lyrics.ovh autocomplete failed', error);
      closeAutocomplete();
    }
  }
}

function scheduleAutocomplete() {
  clearTimeout(autocompleteTimer);
  autocompleteTimer = setTimeout(autocompleteSearch, 140);
}'''
    js = js[:match.start()] + replacement + js[match.end():]

    js = js.replace("""  const items = (Array.isArray(results) ? results : [])
    .filter(item => item.available)
    .slice(0, 6);""", """  const items = (Array.isArray(results) ? results : [])
    .slice(0, 6);""", 1)

    template, count = re.subn(r'(/assets/js/lyrics-ovh-r38-16\.js\?v=)[^\"]+', r'\g<1>20260929r38_16i', template, count=1)
    if count != 1:
        raise RuntimeError("Lyrics.ovh JS asset reference not found")

    CLIENT.write_text(client, encoding="utf-8", newline="\n")
    CONTROLLER.write_text(controller, encoding="utf-8", newline="\n")
    JS.write_text(js, encoding="utf-8", newline="\n")
    TEMPLATE.write_text(template, encoding="utf-8", newline="\n")

    print("R38_16I_FAST_AUTOCOMPLETE_INSTALL_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
