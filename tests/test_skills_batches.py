import re
import unittest

from ReelSyntax_Skills.tools.registry import ROOT, load_index
from reelsyntax import skills
from reelsyntax.evaluation import evaluate

BATCH_SKILLS = (
    "idea-angle-framing",
    "prompt-to-storyboard",
    "open-loop-retention",
    "comedic-timing-beats",
    "microlearning-chunking",
    "procedural-broll-planner",
    "prompt-injection-guard",
    "schema-json-repair",
    "lang-detect-and-route",
    "cross-shot-grade-consistency",
    "pattern-interrupt-cadence",
    "silence-as-punctuation",
    "rhythm-density-map",
    "scene-duration-floor-ceiling",
    "eyeline-headroom-grammar",
    "depth-of-field-budget",
    "ken-burns-photo-choreography",
    "kinetic-layout-choreography",
    "color-script-progression",
    "optical-vignette-halation",
)

FORBIDDEN_TERMS_RE = re.compile(
    r"\b(ai|llm|llms|gpt|chatgpt|openai|claude|anthropic|gemini|deepmind|antigravity|copilot|ollama|whisper|piper|"
    r"assistant|tiktok|youtube|instagram|netflix|spotify|apple|adobe|capcut|canva|midjourney|sora|runway)\b",
    re.IGNORECASE,
)


class AuthoredSkillsBatchTests(unittest.TestCase):
    def test_authored_skills_are_validated_lazy_and_brand_free(self) -> None:
        rows = {r["id"]: r for r in load_index()["skills"]}
        for sid in BATCH_SKILLS:
            self.assertIn(sid, rows)
            row = rows[sid]
            self.assertEqual(row["status"], "validated")
            self.assertGreaterEqual(len(row["aliases"]), 6)
            self.assertTrue(row.get("resources"), f"Missing reference doc for {sid}")

            loaded = skills.get_skill(sid, token_budget=6000)
            self.assertIsNone(FORBIDDEN_TERMS_RE.search(loaded["instructions"]), f"Forbidden term in {sid}")

            for res in row["resources"]:
                ref_doc = skills.get_skill(sid, token_budget=6000, resource=res)
                self.assertEqual(ref_doc["skill_bodies_read"], 0)
                self.assertFalse(ref_doc["executed"])
                self.assertIsNone(FORBIDDEN_TERMS_RE.search(ref_doc["content"]), f"Forbidden term in {res}")

    def test_routing_eval_suite_meets_strict_accuracy_and_zero_violations(self) -> None:
        report = evaluate(ROOT / "tests/routing-eval.json")
        self.assertEqual(report["top1_accuracy"], 1.0)
        self.assertEqual(report["hard_constraint_violation_rate"], 0.0)
        self.assertEqual(report["no_match_error_rate"], 0.0)
        self.assertGreaterEqual(report["recall_at_k_micro"], 0.97)
        for case in report["cases"]:
            self.assertEqual(case["body_reads"], 0)


if __name__ == "__main__":
    unittest.main()
