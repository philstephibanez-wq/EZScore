#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else r"H:\EZScore_v1").resolve()
CLIENT = ROOT / "src/Service/LyricsOvhClient.php"
CONTROLLER = ROOT / "src/Controller/LyricsOvhController.php"
ROUTES = ROOT / "config/routes.yaml"

FAST_METHOD = '    public function suggestFast(string $query, int $limit = 6): array\n    {\n        $query = trim($query);\n        if (mb_strlen($query) < 2) {\n            return [];\n        }\n\n        try {\n            $response = $this->http->request(\n                \'GET\',\n                self::BASE_URL.\'/suggest/\'.rawurlencode($query),\n                [\n                    \'timeout\' => 4.0,\n                    \'headers\' => [\'Accept\' => \'application/json\'],\n                ],\n            );\n\n            if ($response->getStatusCode() !== 200) {\n                return [];\n            }\n\n            $payload = $response->toArray(false);\n        } catch (\\Throwable) {\n            return [];\n        }\n\n        $rows = is_array($payload[\'data\'] ?? null) ? $payload[\'data\'] : [];\n        $results = [];\n        $seen = [];\n\n        foreach ($rows as $row) {\n            if (!is_array($row)) {\n                continue;\n            }\n\n            $artist = trim((string) ($row[\'artist\'][\'name\'] ?? \'\'));\n            $title = trim((string) ($row[\'title\'] ?? \'\'));\n\n            if ($artist === \'\' || $title === \'\') {\n                continue;\n            }\n\n            $key = mb_strtolower($artist."\\n".$title);\n            if (isset($seen[$key])) {\n                continue;\n            }\n            $seen[$key] = true;\n\n            $results[] = [\n                \'artist\' => $artist,\n                \'title\' => $title,\n                \'album\' => isset($row[\'album\'][\'title\']) ? trim((string) $row[\'album\'][\'title\']) : null,\n                \'cover\' => isset($row[\'album\'][\'cover_small\']) ? trim((string) $row[\'album\'][\'cover_small\']) : null,\n            ];\n\n            if (count($results) >= max(1, min(8, $limit))) {\n                break;\n            }\n        }\n\n        return $results;\n    }\n\n'
AUTOCOMPLETE_METHOD = "    #[Route('/autocomplete', name: 'app_song_lyrics_ovh_autocomplete', methods: ['POST'])]\n    public function autocomplete(\n        Song $song,\n        Request $request,\n        LyricsOvhClient $client,\n    ): JsonResponse {\n        $this->requireEditor($song);\n        $payload = $request->toArray();\n\n        if (!$this->isCsrfTokenValid(\n            'song_lyrics_ovh_'.$song->getId(),\n            (string) ($payload['_token'] ?? ''),\n        )) {\n            return $this->json(['error' => 'invalid_csrf'], Response::HTTP_FORBIDDEN);\n        }\n\n        $query = trim((string) ($payload['query'] ?? ''));\n        if (mb_strlen($query) < 2 || mb_strlen($query) > 180) {\n            return $this->json(['ok' => true, 'results' => []]);\n        }\n\n        return $this->json([\n            'ok' => true,\n            'results' => $client->suggestFast($query, 6),\n        ]);\n    }\n\n"

def main() -> int:
    for path in (CLIENT, CONTROLLER, ROUTES):
        if not path.is_file():
            raise RuntimeError(f"Missing prerequisite: {path}")

    client = CLIENT.read_text(encoding="utf-8")
    controller = CONTROLLER.read_text(encoding="utf-8")
    routes = ROUTES.read_text(encoding="utf-8")

    if "public function suggestFast(" not in client:
        anchor = "    public function fetchLyrics("
        pos = client.find(anchor)
        if pos < 0:
            raise RuntimeError("LyricsOvhClient fetchLyrics() anchor not found")
        client = client[:pos] + FAST_METHOD + client[pos:]

    if "app_song_lyrics_ovh_autocomplete" not in controller:
        anchor = "    #[Route('/search', name: 'app_song_lyrics_ovh_search', methods: ['POST'])]"
        pos = controller.find(anchor)
        if pos < 0:
            raise RuntimeError("LyricsOvhController search route anchor not found")
        controller = controller[:pos] + AUTOCOMPLETE_METHOD + controller[pos:]

    if "LyricsOvhController.php" not in routes:
        anchor = '''localized_song_labs:
    resource: ../src/Controller/SongLabController.php
    type: attribute
    prefix:
        fr: /fr
        en: /en
'''
        if anchor not in routes:
            raise RuntimeError("routes.yaml localized_song_labs anchor not found")
        routes = routes.replace(
            anchor,
            anchor + '''
localized_lyrics_ovh:
    resource: ../src/Controller/LyricsOvhController.php
    type: attribute
    prefix:
        fr: /fr
        en: /en
''',
            1,
        )

    CLIENT.write_text(client, encoding="utf-8", newline="\n")
    CONTROLLER.write_text(controller, encoding="utf-8", newline="\n")
    ROUTES.write_text(routes, encoding="utf-8", newline="\n")

    print("R38_16I1_AUTOCOMPLETE_ROUTE_REPAIR_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
