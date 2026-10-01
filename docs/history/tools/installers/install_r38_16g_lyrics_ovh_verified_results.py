#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else r"H:\EZScore_v1").resolve()
CLIENT = ROOT / "src/Service/LyricsOvhClient.php"
CONTROLLER = ROOT / "src/Controller/LyricsOvhController.php"
JS = ROOT / "public/assets/js/lyrics-ovh-r38-16.js"
TEMPLATE = ROOT / "templates/song/lyricslab.html.twig"
NEW_SEARCH = '    /**\n     * @return list<array{artist:string,title:string,album:?string,cover:?string,available:bool,score:int}>\n     */\n    public function search(\n        string $query,\n        int $limit = 8,\n        ?string $preferredArtist = null,\n        ?string $preferredTitle = null,\n    ): array {\n        $query = trim($query);\n        if ($query === \'\') {\n            return [];\n        }\n\n        try {\n            $response = $this->http->request(\n                \'GET\',\n                self::BASE_URL.\'/suggest/\'.rawurlencode($query),\n                [\n                    \'timeout\' => 8.0,\n                    \'headers\' => [\'Accept\' => \'application/json\'],\n                ],\n            );\n\n            if ($response->getStatusCode() !== 200) {\n                return [];\n            }\n\n            $payload = $response->toArray(false);\n        } catch (\\Throwable) {\n            return [];\n        }\n\n        $rows = is_array($payload[\'data\'] ?? null) ? $payload[\'data\'] : [];\n        $candidates = [];\n        $seen = [];\n\n        foreach ($rows as $row) {\n            if (!is_array($row)) {\n                continue;\n            }\n\n            $artist = trim((string) ($row[\'artist\'][\'name\'] ?? \'\'));\n            $title = trim((string) ($row[\'title\'] ?? \'\'));\n\n            if ($artist === \'\' || $title === \'\') {\n                continue;\n            }\n\n            $key = mb_strtolower($artist."\\n".$title);\n            if (isset($seen[$key])) {\n                continue;\n            }\n            $seen[$key] = true;\n\n            $candidates[] = [\n                \'artist\' => $artist,\n                \'title\' => $title,\n                \'album\' => isset($row[\'album\'][\'title\']) ? trim((string) $row[\'album\'][\'title\']) : null,\n                \'cover\' => isset($row[\'album\'][\'cover_small\']) ? trim((string) $row[\'album\'][\'cover_small\']) : null,\n                \'available\' => false,\n                \'score\' => $this->relevanceScore($artist, $title, $preferredArtist, $preferredTitle),\n            ];\n\n            if (count($candidates) >= 12) {\n                break;\n            }\n        }\n\n        usort(\n            $candidates,\n            static fn (array $a, array $b): int => ($b[\'score\'] <=> $a[\'score\'])\n                ?: strcasecmp($a[\'artist\'].\' \'.$a[\'title\'], $b[\'artist\'].\' \'.$b[\'title\']),\n        );\n\n        $candidates = array_slice($candidates, 0, max(1, min(12, $limit)));\n\n        $checks = [];\n        foreach ($candidates as $index => $candidate) {\n            try {\n                $checks[$index] = $this->http->request(\n                    \'GET\',\n                    self::BASE_URL.\'/v1/\'.\n                        rawurlencode($candidate[\'artist\']).\'/\'.\n                        rawurlencode($candidate[\'title\']),\n                    [\n                        \'timeout\' => 6.0,\n                        \'headers\' => [\'Accept\' => \'application/json\'],\n                    ],\n                );\n            } catch (\\Throwable) {\n                $checks[$index] = null;\n            }\n        }\n\n        foreach ($candidates as $index => &$candidate) {\n            $check = $checks[$index] ?? null;\n            if ($check === null) {\n                continue;\n            }\n\n            try {\n                if ($check->getStatusCode() !== 200) {\n                    continue;\n                }\n\n                $checkPayload = $check->toArray(false);\n                $lyrics = trim((string) ($checkPayload[\'lyrics\'] ?? \'\'));\n                $candidate[\'available\'] = $lyrics !== \'\';\n            } catch (\\Throwable) {\n                $candidate[\'available\'] = false;\n            }\n        }\n        unset($candidate);\n\n        usort(\n            $candidates,\n            static fn (array $a, array $b): int =>\n                ((int) $b[\'available\'] <=> (int) $a[\'available\'])\n                ?: ($b[\'score\'] <=> $a[\'score\'])\n                ?: strcasecmp($a[\'artist\'].\' \'.$a[\'title\'], $b[\'artist\'].\' \'.$b[\'title\']),\n        );\n\n        return $candidates;\n    }\n\n    private function relevanceScore(\n        string $artist,\n        string $title,\n        ?string $preferredArtist,\n        ?string $preferredTitle,\n    ): int {\n        $score = 0;\n        $artistNeedle = $this->normaliseSearchKey($preferredArtist ?? \'\');\n        $titleNeedle = $this->normaliseSearchKey($preferredTitle ?? \'\');\n        $artistKey = $this->normaliseSearchKey($artist);\n        $titleKey = $this->normaliseSearchKey($title);\n\n        if ($artistNeedle !== \'\') {\n            if ($artistKey === $artistNeedle) {\n                $score += 100;\n            } elseif (str_contains($artistKey, $artistNeedle) || str_contains($artistNeedle, $artistKey)) {\n                $score += 60;\n            } else {\n                similar_text($artistKey, $artistNeedle, $pct);\n                $score += (int) round($pct * 0.35);\n            }\n        }\n\n        if ($titleNeedle !== \'\') {\n            if ($titleKey === $titleNeedle) {\n                $score += 100;\n            } elseif (str_contains($titleKey, $titleNeedle) || str_contains($titleNeedle, $titleKey)) {\n                $score += 70;\n            } else {\n                similar_text($titleKey, $titleNeedle, $pct);\n                $score += (int) round($pct * 0.35);\n            }\n        }\n\n        return $score;\n    }\n\n    private function normaliseSearchKey(string $value): string\n    {\n        $value = mb_strtolower(trim($value));\n        $value = iconv(\'UTF-8\', \'ASCII//TRANSLIT//IGNORE\', $value) ?: $value;\n        $value = preg_replace(\'/[^a-z0-9]+/\', \' \', $value) ?? $value;\n        return trim(preg_replace(\'/\\s+/\', \' \', $value) ?? $value);\n    }\n\n'

def main() -> int:
    for path in (CLIENT, CONTROLLER, JS, TEMPLATE):
        if not path.is_file():
            raise RuntimeError(f"Missing prerequisite: {path}")

    client = CLIENT.read_text(encoding="utf-8")
    controller = CONTROLLER.read_text(encoding="utf-8")
    js = JS.read_text(encoding="utf-8")
    template = TEMPLATE.read_text(encoding="utf-8")

    start = client.find("    public function search(")
    end = client.find("    public function fetchLyrics(", start)
    if start < 0 or end < 0:
        raise RuntimeError("LyricsOvhClient search/fetchLyrics anchors not found")
    client = client[:start] + NEW_SEARCH + client[end:]

    old_call = "            'results' => $client->search($query),\n"
    new_call = """            'results' => $client->search(
                $query,
                8,
                $song->getArtist(),
                $song->getTitle(),
            ),
"""
    if old_call in controller:
        controller = controller.replace(old_call, new_call, 1)
    elif "$song->getArtist()" not in controller or "$song->getTitle()" not in controller:
        raise RuntimeError("LyricsOvhController search call anchor not found")

    old_button = """    return `
      <article class="lyrics-ovh-result">
        ${cover}
        <div class="lyrics-ovh-result-main">
          <strong>${esc(item.title)}</strong>
          <span>${esc(item.artist)}</span>
          ${album}
        </div>
        <button type="button"
                data-lyrics-ovh-use
                data-artist="${esc(item.artist)}"
                data-title="${esc(item.title)}">Utiliser</button>
      </article>`;
"""
    new_button = """    const action = item.available
      ? `<button type="button"
                 data-lyrics-ovh-use
                 data-artist="${esc(item.artist)}"
                 data-title="${esc(item.title)}">Utiliser</button>`
      : `<button type="button" disabled class="lyrics-ovh-unavailable"
                 title="Lyrics.ovh ne fournit pas de paroles pour cette piste">Paroles indisponibles</button>`;

    return `
      <article class="lyrics-ovh-result${item.available ? '' : ' is-unavailable'}">
        ${cover}
        <div class="lyrics-ovh-result-main">
          <strong>${esc(item.title)}</strong>
          <span>${esc(item.artist)}</span>
          ${album}
        </div>
        ${action}
      </article>`;
"""
    if old_button in js:
        js = js.replace(old_button, new_button, 1)
    elif "Paroles indisponibles" not in js:
        raise RuntimeError("Lyrics.ovh JS result button anchor not found")

    template, count = re.subn(
        r'(/assets/js/lyrics-ovh-r38-16\.js\?v=)[^"]+',
        r'\g<1>20260929r38_16g',
        template,
        count=1,
    )
    if count != 1:
        raise RuntimeError("Lyrics.ovh JS asset reference not found")

    CLIENT.write_text(client, encoding="utf-8", newline="\n")
    CONTROLLER.write_text(controller, encoding="utf-8", newline="\n")
    JS.write_text(js, encoding="utf-8", newline="\n")
    TEMPLATE.write_text(template, encoding="utf-8", newline="\n")

    print("R38_16G_LYRICS_OVH_VERIFIED_RESULTS_INSTALL_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
