import hashlib
import importlib.util
from pathlib import Path
from typing import Any
import unittest

from ReelSyntax_Skills.tools.registry import read_json
from reelsyntax import drawing

HAS_PILLOW = importlib.util.find_spec("PIL") is not None

REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINES_PATH = REPO_ROOT / "tests/golden/visual_baselines.json"

GOLDEN_SHAPE_SCENE = {
    "id": "golden-shape",
    "duration_frames": 60,
    "recipe": "shape-field",
    "engine": "pillow",
    "params": {
        "background": "#2b303a",
        "shapes": [
            {
                "type": "rounded_rect",
                "x": 0.10,
                "y": 0.18,
                "w": 0.80,
                "h": 0.64,
                "radius": 0.04,
                "fill": "#3c4452",
                "stroke": "#5aa6b0",
                "stroke_width": 4,
            },
            {"type": "circle", "cx": 0.50, "cy": 0.45, "r": 0.16, "fill": "#e06246"},
            {"type": "star", "cx": 0.50, "cy": 0.45, "r": 0.07, "sides": 5, "fill": "#f4f6f9"},
        ],
    },
}

DRAFT_VERTICAL_OUTPUT = {
    "width": 540,
    "height": 960,
    "fps": "30/1",
    "original_size": (1080, 1920),
}


def compute_grid_signature(img: Any, cols: int = 8, rows: int = 8) -> list[list[int]]:
    from PIL import Image

    small = img.convert("RGB").resize((cols, rows), Image.Resampling.BOX)
    raw = small.tobytes()
    return [[raw[i], raw[i + 1], raw[i + 2]] for i in range(0, len(raw), 3)]


def grid_mae(grid_a: list[list[int]], grid_b: list[list[int]]) -> float:
    total = 0.0
    channels = 0
    for ca, cb in zip(grid_a, grid_b):
        for va, vb in zip(ca, cb):
            total += abs(va - vb)
            channels += 1
    return total / max(1, channels)


@unittest.skipUnless(HAS_PILLOW, "Pillow required for visual regression tests")
class VisualRegressionTests(unittest.TestCase):
    def test_pure_shape_field_matches_golden_baseline_and_repeats_bit_identically(self) -> None:
        baselines = read_json(BASELINES_PATH)["cases"]
        spec = baselines["pure_shape_field"]

        img1, _ = drawing.draw(GOLDEN_SHAPE_SCENE, spec["frame"], DRAFT_VERTICAL_OUTPUT, 42, supersampling=1)
        img2, _ = drawing.draw(GOLDEN_SHAPE_SCENE, spec["frame"], DRAFT_VERTICAL_OUTPUT, 42, supersampling=1)
        self.assertEqual(
            hashlib.sha256(img1.tobytes()).hexdigest(),
            hashlib.sha256(img2.tobytes()).hexdigest(),
        )

        observed = compute_grid_signature(img1)
        delta = grid_mae(observed, spec["grid_8x8_rgb"])
        self.assertLessEqual(delta, spec["max_mae"])

    def test_official_format_golden_frames_stay_within_cross_os_visual_bounds(self) -> None:
        baselines = read_json(BASELINES_PATH)["cases"]
        for fmt_id in ("kinetic-typography", "photo-slideshow", "social-hook-reel"):
            with self.subTest(format_id=fmt_id):
                key = f"format_{fmt_id}_scene0"
                spec = baselines[key]
                plan = read_json(REPO_ROOT / f"formats/{fmt_id}/examples/en/reel.json")
                scene = plan["scenes"][0]

                img_a, bounds_a = drawing.draw(scene, spec["frame"], DRAFT_VERTICAL_OUTPUT, plan["seed"], supersampling=1)
                img_b, _ = drawing.draw(scene, spec["frame"], DRAFT_VERTICAL_OUTPUT, plan["seed"], supersampling=1)
                self.assertEqual(img_a.tobytes(), img_b.tobytes())
                self.assertEqual([b["field"] for b in bounds_a], spec["text_fields"])

                for entry in bounds_a:
                    x0, y0, x1, y1 = entry["bounds"]
                    self.assertGreaterEqual(x0, DRAFT_VERTICAL_OUTPUT["width"] * 0.05)
                    self.assertLessEqual(x1, DRAFT_VERTICAL_OUTPUT["width"] * 0.52)
                    self.assertGreaterEqual(y0, DRAFT_VERTICAL_OUTPUT["height"] * 0.12)
                    self.assertLessEqual(y1, DRAFT_VERTICAL_OUTPUT["height"] * 0.82)

                delta = grid_mae(compute_grid_signature(img_a), spec["grid_8x8_rgb"])
                self.assertLessEqual(delta, spec["max_mae"])

    def test_regression_detector_flags_visual_corruption(self) -> None:
        baselines = read_json(BASELINES_PATH)["cases"]
        spec = baselines["pure_shape_field"]
        mutated = {
            **GOLDEN_SHAPE_SCENE,
            "params": {
                **GOLDEN_SHAPE_SCENE["params"],
                "background": "#f0ece4",
            },
        }
        corrupted_img, _ = drawing.draw(mutated, spec["frame"], DRAFT_VERTICAL_OUTPUT, 42, supersampling=1)
        delta = grid_mae(compute_grid_signature(corrupted_img), spec["grid_8x8_rgb"])
        self.assertGreater(delta, 80.0)


if __name__ == "__main__":
    unittest.main()
