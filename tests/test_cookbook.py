from pathlib import Path
import re
import unittest

from reelsyntax.prompt.intent import parse_intent

REPO_ROOT = Path(__file__).resolve().parents[1]
COOKBOOK = REPO_ROOT / "docs/cookbook.md"
MKDOCS = REPO_ROOT / "mkdocs.yml"

EXPECTED_FORMATS = (
    "kinetic-typography",
    "photo-slideshow",
    "social-hook-reel",
    "explainer-slides",
    "lyric-video",
    "music-visualizer",
    "channel-intro",
    "data-story",
    "news-ticker",
    "product-promo",
    "loop-art",
    "retro-lowpoly-cutscene",
    "cinematic-3d",
    "stepped-clay-look",
    "paper-cutout",
)

FORBIDDEN_TERMS_RE = re.compile(
    r"\b(?:antigravity|gemini|claude|chatgpt|openai|codex|copilot|deepmind|"
    r"playstation|ps2|nintendo|xbox|tiktok|instagram|youtube|spotify|adobe|"
    r"disney|pixar|co-authored-by)\b",
    re.IGNORECASE,
)


def split_format_sections(text: str) -> dict[str, str]:
    pattern = re.compile(r"^## `([a-z0-9-]+)`\s*$", re.MULTILINE)
    matches = list(pattern.finditer(text))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group(1)] = text[start:end]
    return sections


class CookbookDocsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = COOKBOOK.read_text(encoding="utf-8")
        self.sections = split_format_sections(self.text)

    def test_cookbook_wired_into_mkdocs_navigation_without_broken_links(self) -> None:
        mkdocs_text = MKDOCS.read_text(encoding="utf-8")
        self.assertIn("cookbook.md", mkdocs_text)
        links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", self.text)
        self.assertTrue(links)
        for target in links:
            if target.startswith(("http://", "https://")):
                continue
            if target.startswith("#"):
                slug = target[1:]
                self.assertIn(slug, self.sections)
                continue
            path_part = target.split("#", 1)[0]
            resolved = (COOKBOOK.parent / path_part).resolve()
            self.assertTrue(resolved.is_file(), target)

    def test_all_fifteen_formats_have_trilingual_weak_and_strong_prompts(self) -> None:
        self.assertEqual(set(self.sections), set(EXPECTED_FORMATS))
        for format_id in EXPECTED_FORMATS:
            body = self.sections[format_id]
            with self.subTest(format_id=format_id):
                self.assertIn(f"[`{format_id}`](#{format_id})", self.text)
                self.assertIn("- **Diagnosis:**", body)
                self.assertIn("- **Repair tips:**", body)
                for lang in ("EN", "TR", "DE"):
                    marker = f"### {lang} — `{format_id}`"
                    self.assertIn(marker, body)
                    sub = body.split(marker, 1)[1].split("### ", 1)[0]
                    weak_match = re.search(r"- \*\*Weak prompt:\*\* `([^`]+)`", sub)
                    strong_match = re.search(r"- \*\*Strong prompt:\*\* `([^`]+)`", sub)
                    self.assertIsNotNone(weak_match, (format_id, lang))
                    self.assertIsNotNone(strong_match, (format_id, lang))
                    weak = weak_match.group(1)
                    strong = strong_match.group(1)
                    self.assertGreater(len(strong), len(weak))
                    parsed = parse_intent(strong, format_id=format_id)
                    self.assertEqual(parsed.prompt_lang, lang.lower())
                    self.assertEqual(parsed.video_lang, lang.lower())

    def test_no_forbidden_brand_or_attribution_terms(self) -> None:
        self.assertIsNone(FORBIDDEN_TERMS_RE.search(self.text))


if __name__ == "__main__":
    unittest.main()
