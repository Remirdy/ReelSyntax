import ast
from dataclasses import dataclass
import hashlib
from html.parser import HTMLParser
import io
from pathlib import Path
import tokenize
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]

EXCLUDED_DIR_NAMES = frozenset({
    ".git",
    ".venv",
    ".tools",
    "integrations",
    "build",
    "dist",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    ".reelsyntax",
    "output",
    "review",
})

UNMODIFIED_LEGACY_DIGESTS: dict[str, str] = {
    "ReelSyntax_Skills/examples/hero-fixture/render.py": "a2f73da384702a8afee446c346716e13228d93f612e1e6809d47569260c1fffd",
    "docs/stylesheets/extra.css": "cba7c0a65edc47eb28ebc288a54af81d4975be04dbb8be1682069ca64b56e3cc",
    "reelsyntax/palette.py": "81961d4ba1fd88f3beacd29119ba46feded24d4e9abf54b20df6db41673c2f29",
    "tests/test_production_features.py": "e80911969a42cd5a2500b1472949846c9ee91a46fed4de5f00b06ec533b136a1",
}

JS_EXTENSIONS = frozenset({".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx"})
HTML_EXTENSIONS = frozenset({".html", ".htm"})
SHELL_EXTENSIONS = frozenset({".sh", ".bash", ".zsh"})
SCANNED_EXTENSIONS = frozenset({".py", ".css"}) | JS_EXTENSIONS | HTML_EXTENSIONS | SHELL_EXTENSIONS

JS_REGEX_PRECEDING_KEYWORDS = frozenset({
    "return",
    "throw",
    "case",
    "typeof",
    "void",
    "delete",
    "in",
    "of",
    "instanceof",
    "new",
    "yield",
    "await",
})

JS_REGEX_PRECEDING_PUNCT = frozenset("({[=:;,!&|?+-*%<>~^")


@dataclass(frozen=True)
class StyleViolation:
    path: str
    line: int
    kind: str


def normalized_sha256(raw: bytes) -> str:
    return hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()


def scan_python_source(source: str, path: str) -> list[StyleViolation]:
    violations: list[StyleViolation] = []
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type == tokenize.COMMENT:
            if tok.start[0] == 1 and tok.string.startswith("#!"):
                continue
            violations.append(StyleViolation(path=path, line=tok.start[0], kind="python-comment"))
    tree = ast.parse(source, filename=path)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if ast.get_docstring(node, clean=False) is not None:
                line = getattr(node, "lineno", 1)
                violations.append(StyleViolation(path=path, line=line, kind="python-docstring"))
    return violations


def scan_js_ts_source(source: str, path: str, base_line: int = 1) -> list[StyleViolation]:
    violations: list[StyleViolation] = []
    n = len(source)
    i = 0
    line = base_line
    if base_line == 1 and source.startswith("#!"):
        nl = source.find("\n")
        if nl == -1:
            return violations
        i = nl + 1
        line += 1
    template_brace_stack: list[int] = []
    allows_regex = True
    while i < n:
        ch = source[i]
        if ch == "\n":
            line += 1
            i += 1
            continue
        if ch in " \t\r\f\v":
            i += 1
            continue
        if ch in ("'", '"'):
            quote = ch
            i += 1
            while i < n:
                c = source[i]
                if c == "\\":
                    if i + 1 < n and source[i + 1] == "\n":
                        line += 1
                    i += 2
                    continue
                if c == "\n":
                    line += 1
                    i += 1
                    break
                i += 1
                if c == quote:
                    break
            allows_regex = False
            continue
        if ch == "`":
            i += 1
            i, line = _consume_template_segment(source, i, line, template_brace_stack)
            allows_regex = False
            continue
        if ch == "}" and template_brace_stack and template_brace_stack[-1] == 0:
            template_brace_stack.pop()
            i += 1
            i, line = _consume_template_segment(source, i, line, template_brace_stack)
            allows_regex = False
            continue
        if ch == "{" and template_brace_stack:
            template_brace_stack[-1] += 1
            allows_regex = True
            i += 1
            continue
        if ch == "}" and template_brace_stack:
            template_brace_stack[-1] -= 1
            allows_regex = False
            i += 1
            continue
        if ch == "/" and i + 1 < n and source[i + 1] == "/":
            violations.append(StyleViolation(path=path, line=line, kind="js-line-comment"))
            nl = source.find("\n", i + 2)
            if nl == -1:
                break
            i = nl + 1
            line += 1
            continue
        if ch == "/" and i + 1 < n and source[i + 1] == "*":
            violations.append(StyleViolation(path=path, line=line, kind="js-block-comment"))
            end = source.find("*/", i + 2)
            segment = source[i + 2:] if end == -1 else source[i + 2:end]
            line += segment.count("\n")
            if end == -1:
                break
            i = end + 2
            continue
        if ch == "/" and allows_regex:
            i += 1
            in_class = False
            while i < n:
                c = source[i]
                if c == "\\":
                    i += 2
                    continue
                if c == "\n":
                    line += 1
                    i += 1
                    break
                if c == "[":
                    in_class = True
                elif c == "]":
                    in_class = False
                elif c == "/" and not in_class:
                    i += 1
                    while i < n and source[i].isalpha():
                        i += 1
                    break
                i += 1
            allows_regex = False
            continue
        if ch.isalpha() or ch in ("_", "$"):
            start = i
            i += 1
            while i < n and (source[i].isalnum() or source[i] in ("_", "$")):
                i += 1
            word = source[start:i]
            allows_regex = word in JS_REGEX_PRECEDING_KEYWORDS
            continue
        if ch.isdigit():
            i += 1
            while i < n and (source[i].isalnum() or source[i] in (".", "_")):
                i += 1
            allows_regex = False
            continue
        allows_regex = ch in JS_REGEX_PRECEDING_PUNCT
        i += 1
    return violations


def _consume_template_segment(
    source: str,
    index: int,
    line: int,
    stack: list[int],
) -> tuple[int, int]:
    n = len(source)
    i = index
    while i < n:
        c = source[i]
        if c == "\\":
            if i + 1 < n and source[i + 1] == "\n":
                line += 1
            i += 2
            continue
        if c == "\n":
            line += 1
            i += 1
            continue
        if c == "`":
            return i + 1, line
        if c == "$" and i + 1 < n and source[i + 1] == "{":
            stack.append(0)
            return i + 2, line
        i += 1
    return i, line


def scan_css_source(source: str, path: str, base_line: int = 1) -> list[StyleViolation]:
    violations: list[StyleViolation] = []
    n = len(source)
    i = 0
    line = base_line
    while i < n:
        ch = source[i]
        if ch == "\n":
            line += 1
            i += 1
            continue
        if ch in ("'", '"'):
            quote = ch
            i += 1
            while i < n:
                c = source[i]
                if c == "\\":
                    if i + 1 < n and source[i + 1] == "\n":
                        line += 1
                    i += 2
                    continue
                if c == "\n":
                    line += 1
                i += 1
                if c == quote:
                    break
            continue
        if source[i:i + 4].lower() == "url(":
            i += 4
            while i < n and source[i] in " \t\r\n":
                if source[i] == "\n":
                    line += 1
                i += 1
            if i < n and source[i] not in ("'", '"'):
                while i < n and source[i] != ")":
                    if source[i] == "\\" and i + 1 < n:
                        i += 2
                        continue
                    if source[i] == "\n":
                        line += 1
                    i += 1
            continue
        if ch == "/" and i + 1 < n and source[i + 1] == "*":
            violations.append(StyleViolation(path=path, line=line, kind="css-comment"))
            end = source.find("*/", i + 2)
            segment = source[i + 2:] if end == -1 else source[i + 2:end]
            line += segment.count("\n")
            if end == -1:
                break
            i = end + 2
            continue
        i += 1
    return violations


class _HtmlCommentScanner(HTMLParser):
    def __init__(self, path: str) -> None:
        super().__init__(convert_charrefs=False)
        self.path = path
        self.violations: list[StyleViolation] = []
        self._active_tag: str | None = None
        self._script_is_json = False
        self._buffer_line = 1
        self._buffer: list[str] = []

    def handle_comment(self, data: str) -> None:
        line, _ = self.getpos()
        self.violations.append(StyleViolation(path=self.path, line=line, kind="html-comment"))

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lower = tag.lower()
        if lower in {"script", "style"}:
            self._active_tag = lower
            self._buffer_line, _ = self.getpos()
            self._buffer = []
            attr_map = {k.lower(): (v or "").lower() for k, v in attrs}
            mime = attr_map.get("type", "")
            self._script_is_json = "json" in mime

    def handle_data(self, data: str) -> None:
        if self._active_tag is not None:
            self._buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        lower = tag.lower()
        if lower == self._active_tag:
            content = "".join(self._buffer)
            if lower == "script" and not self._script_is_json:
                self.violations.extend(scan_js_ts_source(content, self.path, base_line=self._buffer_line))
            elif lower == "style":
                self.violations.extend(scan_css_source(content, self.path, base_line=self._buffer_line))
            self._active_tag = None
            self._buffer = []
            self._script_is_json = False


def scan_html_source(source: str, path: str) -> list[StyleViolation]:
    scanner = _HtmlCommentScanner(path)
    scanner.feed(source)
    scanner.close()
    return scanner.violations


def scan_shell_source(source: str, path: str) -> list[StyleViolation]:
    violations: list[StyleViolation] = []
    n = len(source)
    i = 0
    line = 1
    if source.startswith("#!"):
        nl = source.find("\n")
        if nl == -1:
            return violations
        i = nl + 1
        line += 1
    in_single = False
    in_double = False
    param_brace_depth = 0
    at_word_boundary = True
    while i < n:
        ch = source[i]
        if ch == "\n":
            line += 1
            i += 1
            if not in_single and not in_double:
                at_word_boundary = True
            continue
        if in_single:
            if ch == "'":
                in_single = False
            i += 1
            at_word_boundary = False
            continue
        if in_double:
            if ch == "\\":
                if i + 1 < n and source[i + 1] == "\n":
                    line += 1
                i += 2
                continue
            if ch == '"':
                in_double = False
            i += 1
            at_word_boundary = False
            continue
        if ch == "\\":
            if i + 1 < n and source[i + 1] == "\n":
                line += 1
            i += 2
            at_word_boundary = False
            continue
        if ch == "'":
            in_single = True
            at_word_boundary = False
            i += 1
            continue
        if ch == '"':
            in_double = True
            at_word_boundary = False
            i += 1
            continue
        if ch == "$" and i + 1 < n and source[i + 1] == "{":
            param_brace_depth += 1
            at_word_boundary = False
            i += 2
            continue
        if ch == "}" and param_brace_depth > 0:
            param_brace_depth -= 1
            at_word_boundary = False
            i += 1
            continue
        if ch == "#" and param_brace_depth == 0 and at_word_boundary:
            violations.append(StyleViolation(path=path, line=line, kind="shell-comment"))
            nl = source.find("\n", i + 1)
            if nl == -1:
                break
            i = nl + 1
            line += 1
            at_word_boundary = True
            continue
        at_word_boundary = ch in " \t\r;|&("
        i += 1
    return violations


def scan_file_bytes(raw: bytes, relative_path: str) -> list[StyleViolation]:
    expected_legacy = UNMODIFIED_LEGACY_DIGESTS.get(relative_path)
    if expected_legacy is not None and normalized_sha256(raw) == expected_legacy:
        return []
    text = raw.replace(b"\r\n", b"\n").decode("utf-8")
    suffix = Path(relative_path).suffix.lower()
    if suffix == ".py":
        return scan_python_source(text, relative_path)
    if suffix in JS_EXTENSIONS:
        return scan_js_ts_source(text, relative_path)
    if suffix == ".css":
        return scan_css_source(text, relative_path)
    if suffix in HTML_EXTENSIONS:
        return scan_html_source(text, relative_path)
    if suffix in SHELL_EXTENSIONS:
        return scan_shell_source(text, relative_path)
    return []


def iter_repository_source_files(root: Path) -> list[Path]:
    collected: list[Path] = []
    stack = [root]
    while stack:
        current = stack.pop()
        for entry in sorted(current.iterdir(), key=lambda p: p.name):
            if entry.is_symlink():
                continue
            if entry.is_dir():
                if entry.name in EXCLUDED_DIR_NAMES or entry.name.endswith(".egg-info"):
                    continue
                stack.append(entry)
            elif entry.is_file() and entry.suffix.lower() in SCANNED_EXTENSIONS:
                collected.append(entry)
    return sorted(collected)


def scan_repository(root: Path = REPO_ROOT) -> list[StyleViolation]:
    violations: list[StyleViolation] = []
    for file_path in iter_repository_source_files(root):
        rel = file_path.relative_to(root).as_posix()
        violations.extend(scan_file_bytes(file_path.read_bytes(), rel))
    return violations


class CodeStyleGuardTests(unittest.TestCase):
    def test_repository_sources_have_no_comments_or_docstrings(self) -> None:
        violations = scan_repository(REPO_ROOT)
        formatted = [f"{v.path}:{v.line} ({v.kind})" for v in violations]
        self.assertEqual(formatted, [])

    def test_python_scanner_flags_comments_and_docstrings_but_allows_shebang_and_strings(self) -> None:
        clean = "#!/usr/bin/env python3\nURL = 'https://example.com/#anchor'\ndef add(a: int, b: int) -> int:\n    return a + b\n"
        self.assertEqual(scan_python_source(clean, "sample.py"), [])

        with_comment = "VALUE = 1 " + "#" + " trailing note\n"
        res_comment = scan_python_source(with_comment, "sample.py")
        self.assertEqual(len(res_comment), 1)
        self.assertEqual(res_comment[0].kind, "python-comment")

        with_docstring = 'def run() -> int:\n    """Summary."""\n    return 0\n'
        res_doc = scan_python_source(with_docstring, "sample.py")
        self.assertEqual(len(res_doc), 1)
        self.assertEqual(res_doc[0].kind, "python-docstring")

    def test_js_ts_scanner_distinguishes_strings_templates_regexes_and_comments(self) -> None:
        slash_pair = "/" + "/"
        block_open = "/" + "*"
        block_close = "*" + "/"
        clean = (
            "#!/usr/bin/env node\n"
            f'const endpoint = "https:{slash_pair}example.com/a{block_open}b{block_close}";\n'
            f"const nested = `prefix ${{`http:{slash_pair}inner`}} suffix`;\n"
            "const pattern = /^https:\\/\\/example\\.com\\/[a-z]+$/i;\n"
        )
        self.assertEqual(scan_js_ts_source(clean, "app.ts"), [])

        bad_line = f"const x = 1; {slash_pair} note\n"
        self.assertEqual([v.kind for v in scan_js_ts_source(bad_line, "app.ts")], ["js-line-comment"])

        bad_block = f"{block_open} header {block_close}\nexport const y = 2;\n"
        self.assertEqual([v.kind for v in scan_js_ts_source(bad_block, "app.ts")], ["js-block-comment"])

    def test_css_and_html_scanners_ignore_urls_and_flag_comments(self) -> None:
        block_open = "/" + "*"
        block_close = "*" + "/"
        clean_css = f'.hero {{ background: url(https://example.com/bg.png); content: "{block_open}ok{block_close}"; }}\n'
        self.assertEqual(scan_css_source(clean_css, "style.css"), [])

        bad_css = f"{block_open} theme {block_close}\n.hero {{ color: #fff; }}\n"
        self.assertEqual([v.kind for v in scan_css_source(bad_css, "style.css")], ["css-comment"])

        html_open = "<!" + "--"
        html_close = "--" + ">"
        bad_html = f"<div>{html_open} hidden {html_close}</div><script>const x = 1; // bad\n</script>"
        kinds = [v.kind for v in scan_html_source(bad_html, "index.html")]
        self.assertEqual(kinds, ["html-comment", "js-line-comment"])

    def test_shell_scanner_allows_shebang_parameter_length_and_hex_values(self) -> None:
        hash_ch = "#"
        clean_sh = f"#!/usr/bin/env bash\nCOLOR={hash_ch}14171c\nCOUNT=${{{hash_ch}COLOR}}\necho \"$COLOR $COUNT\"\n"
        self.assertEqual(scan_shell_source(clean_sh, "build.sh"), [])

        bad_sh = f"#!/usr/bin/env bash\necho ok {hash_ch} inline note\n"
        self.assertEqual([v.kind for v in scan_shell_source(bad_sh, "build.sh")], ["shell-comment"])

    def test_modified_legacy_file_loses_exemption(self) -> None:
        legacy_rel = "reelsyntax/palette.py"
        original = (REPO_ROOT / legacy_rel).read_bytes()
        self.assertEqual(scan_file_bytes(original, legacy_rel), [])
        drifted = original + b"\nVALUE = 1\n"
        self.assertTrue(len(scan_file_bytes(drifted, legacy_rel)) > 0)


if __name__ == "__main__":
    unittest.main()
