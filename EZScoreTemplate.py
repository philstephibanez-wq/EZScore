from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path
import re
from typing import Any, Mapping, Sequence


class ScoreTemplateError(RuntimeError):
    """Erreur de rendu d'un template EZScore/OPUS-like."""


@dataclass(frozen=True)
class _Token:
    kind: str
    value: str


class ScoreTemplateRenderer:
    """
    Renderer SCORE volontairement petit et sans dépendance externe.

    Syntaxe supportée :
        {{ value }}
        {{{ raw_html }}}
        [[ if: condition ]]
        [[ endif ]]
        [[ foreach: items as item ]]
        [[ endforeach ]]
        [[ include: path/to/file.score ]]

    Le moteur ne connaît ni Streamlit, ni SQLite, ni la logique musicale.
    """

    _TOKEN_RE = re.compile(
        r"(\{\{\{\s*[A-Za-z_][A-Za-z0-9_.]*\s*\}\}\}"
        r"|\{\{\s*[A-Za-z_][A-Za-z0-9_.]*\s*\}\}"
        r"|\[\[\s*(?:if:\s*[A-Za-z_][A-Za-z0-9_.]*"
        r"|endif"
        r"|foreach:\s*[A-Za-z_][A-Za-z0-9_.]*\s+as\s+[A-Za-z_][A-Za-z0-9_]*"
        r"|endforeach"
        r"|include:\s*[^\]]+?)\s*\]\])"
    )

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()

    def render(self, template_name: str | Path, context: Mapping[str, Any] | None = None) -> str:
        path = self._resolve_template_path(template_name)
        source = path.read_text(encoding="utf-8")
        return self.render_string(source, context or {}, current_dir=path.parent)

    def render_string(
        self,
        source: str,
        context: Mapping[str, Any] | None = None,
        *,
        current_dir: Path | None = None,
    ) -> str:
        ctx = dict(context or {})
        tokens = self._tokenize(source)
        rendered, index = self._render_tokens(tokens, 0, ctx, current_dir or self.root, stop=None)
        if index != len(tokens):
            raise ScoreTemplateError("SCORE_UNEXPECTED_TRAILING_TOKENS")
        return rendered

    def _resolve_template_path(self, template_name: str | Path, base_dir: Path | None = None) -> Path:
        candidate = Path(template_name)
        if not candidate.is_absolute():
            candidate = (base_dir or self.root) / candidate
        resolved = candidate.resolve()

        try:
            resolved.relative_to(self.root)
        except ValueError as exc:
            raise ScoreTemplateError(f"SCORE_TEMPLATE_OUTSIDE_ROOT:{template_name}") from exc

        if resolved.suffix.lower() != ".score":
            raise ScoreTemplateError(f"SCORE_TEMPLATE_EXTENSION_FORBIDDEN:{template_name}")
        if not resolved.is_file():
            raise ScoreTemplateError(f"SCORE_TEMPLATE_MISSING:{template_name}")
        return resolved

    def _tokenize(self, source: str) -> list[_Token]:
        out: list[_Token] = []
        pos = 0
        for match in self._TOKEN_RE.finditer(source):
            if match.start() > pos:
                out.append(_Token("text", source[pos:match.start()]))
            raw = match.group(0)
            stripped = raw.strip()

            if stripped.startswith("{{{"):
                key = stripped[3:-3].strip()
                out.append(_Token("raw", key))
            elif stripped.startswith("{{"):
                key = stripped[2:-2].strip()
                out.append(_Token("escaped", key))
            else:
                directive = stripped[2:-2].strip()
                if directive.startswith("if:"):
                    out.append(_Token("if", directive[3:].strip()))
                elif directive == "endif":
                    out.append(_Token("endif", ""))
                elif directive.startswith("foreach:"):
                    spec = directive[len("foreach:"):].strip()
                    match_foreach = re.fullmatch(
                        r"([A-Za-z_][A-Za-z0-9_.]*)\s+as\s+([A-Za-z_][A-Za-z0-9_]*)",
                        spec,
                    )
                    if not match_foreach:
                        raise ScoreTemplateError(f"SCORE_FOREACH_INVALID:{spec}")
                    out.append(_Token("foreach", f"{match_foreach.group(1)}|{match_foreach.group(2)}"))
                elif directive == "endforeach":
                    out.append(_Token("endforeach", ""))
                elif directive.startswith("include:"):
                    out.append(_Token("include", directive[len("include:"):].strip()))
                else:
                    raise ScoreTemplateError(f"SCORE_DIRECTIVE_UNKNOWN:{directive}")
            pos = match.end()

        if pos < len(source):
            out.append(_Token("text", source[pos:]))
        return out

    def _render_tokens(
        self,
        tokens: Sequence[_Token],
        index: int,
        context: Mapping[str, Any],
        current_dir: Path,
        stop: str | None,
    ) -> tuple[str, int]:
        out: list[str] = []

        while index < len(tokens):
            token = tokens[index]

            if stop and token.kind == stop:
                return "".join(out), index + 1

            if token.kind in {"endif", "endforeach"}:
                raise ScoreTemplateError(f"SCORE_UNEXPECTED_{token.kind.upper()}")

            if token.kind == "text":
                out.append(token.value)
                index += 1
                continue

            if token.kind == "escaped":
                value = self._resolve(context, token.value)
                out.append(escape("" if value is None else str(value), quote=True))
                index += 1
                continue

            if token.kind == "raw":
                value = self._resolve(context, token.value)
                out.append("" if value is None else str(value))
                index += 1
                continue

            if token.kind == "include":
                include_path = self._resolve_template_path(token.value, current_dir)
                include_source = include_path.read_text(encoding="utf-8")
                out.append(self.render_string(include_source, context, current_dir=include_path.parent))
                index += 1
                continue

            if token.kind == "if":
                body_start = index + 1
                body_end = self._find_matching(tokens, body_start, "if", "endif")
                if self._truthy(self._resolve(context, token.value)):
                    body, _ = self._render_tokens(
                        tokens,
                        body_start,
                        context,
                        current_dir,
                        stop="endif",
                    )
                    out.append(body)
                index = body_end + 1
                continue

            if token.kind == "foreach":
                path, alias = token.value.split("|", 1)
                body_start = index + 1
                body_end = self._find_matching(tokens, body_start, "foreach", "endforeach")
                values = self._resolve(context, path)
                if values is None:
                    values = []
                if isinstance(values, (str, bytes, Mapping)):
                    raise ScoreTemplateError(f"SCORE_FOREACH_NOT_SEQUENCE:{path}")
                for item in values:
                    child = dict(context)
                    child[alias] = item
                    body, _ = self._render_tokens(
                        tokens,
                        body_start,
                        child,
                        current_dir,
                        stop="endforeach",
                    )
                    out.append(body)
                index = body_end + 1
                continue

            raise ScoreTemplateError(f"SCORE_TOKEN_UNKNOWN:{token.kind}")

        if stop:
            raise ScoreTemplateError(f"SCORE_MISSING_{stop.upper()}")
        return "".join(out), index

    @staticmethod
    def _find_matching(tokens: Sequence[_Token], start: int, opener: str, closer: str) -> int:
        depth = 1
        for index in range(start, len(tokens)):
            kind = tokens[index].kind
            if kind == opener:
                depth += 1
            elif kind == closer:
                depth -= 1
                if depth == 0:
                    return index
        raise ScoreTemplateError(f"SCORE_MISSING_{closer.upper()}")

    @staticmethod
    def _truthy(value: Any) -> bool:
        return bool(value)

    @staticmethod
    def _resolve(context: Mapping[str, Any], path: str) -> Any:
        value: Any = context
        for part in path.split("."):
            if isinstance(value, Mapping):
                if part not in value:
                    raise ScoreTemplateError(f"SCORE_VALUE_MISSING:{path}")
                value = value[part]
            else:
                if not hasattr(value, part):
                    raise ScoreTemplateError(f"SCORE_VALUE_MISSING:{path}")
                value = getattr(value, part)
        return value
