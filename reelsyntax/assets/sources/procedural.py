import importlib.util
import math
from pathlib import Path
import struct
from typing import Any
import wave
import zlib

from ReelSyntax_Skills.tools.registry import contained_path, read_json

from ...palette import hex_to_rgb, mix_oklab, rgb_to_hex
from ...sound import _voice_sample
from ..license import record_asset_license, write_licenses_markdown

PKG_DIR = Path(__file__).resolve().parents[2]
STARTER_CATALOG_PATH = PKG_DIR / "data/starter_assets/catalog.json"


def load_starter_catalog() -> dict[str, Any]:
    raw = read_json(STARTER_CATALOG_PATH, max_bytes=262_144)
    if not isinstance(raw, dict) or not isinstance(raw.get("assets"), list):
        raise ValueError("Invalid starter asset catalog")
    return raw


def list_starter_assets(kind: str | None = None) -> list[dict[str, Any]]:
    assets = load_starter_catalog()["assets"]
    if kind is None:
        return list(assets)
    return [item for item in assets if item.get("kind") == kind]


def _write_music_bed_wav(dest: Path, spec: dict[str, Any], duration_sec: float, seed: int) -> None:
    rate = 48000
    dur = max(1.0, min(180.0, float(duration_sec)))
    total_samples = int(round(dur * rate))
    bpm = max(40, int(spec.get("bpm", 100)))
    beat_sec = 60.0 / bpm
    notes = [float(n) for n in spec.get("notes_hz", [220, 277, 330, 440])]
    inst = str(spec.get("instrument", "warm_pad"))
    base_amp = 10 ** (float(spec.get("gain_db", -15.0)) / 20.0)

    events: list[tuple[float, float, float, float]] = []
    t_cursor = 0.0
    step_idx = 0
    note_dur = beat_sec * (1.8 if inst == "warm_pad" else 0.92)
    while t_cursor < dur:
        freq = notes[step_idx % len(notes)]
        pan = -0.25 if step_idx % 2 == 0 else 0.25
        events.append((t_cursor, min(note_dur, dur - t_cursor), freq, pan))
        t_cursor += beat_sec
        step_idx += 1

    dest.parent.mkdir(parents=True, exist_ok=True)
    state = (int(seed) or 1) & 0xFFFFFFFF
    filtered = 0.0
    with wave.open(str(dest), "wb") as wf:
        wf.setparams((2, 2, rate, 0, "NONE", "not compressed"))
        chunk = bytearray()
        for idx in range(total_samples):
            time_s = idx / rate
            state = (1664525 * state + 1013904223) & 0xFFFFFFFF
            noise = ((state / 2**32) * 2.0 - 1.0) * 0.04
            filtered = filtered * 0.95 + noise
            env = max(0.0, min(1.0, time_s / 0.04, (dur - time_s) / 0.08))
            left = filtered * 0.08
            right = filtered * 0.08
            for start_s, len_s, freq, pan in events:
                local = time_s - start_s
                if 0.0 <= local < len_s:
                    sig = base_amp * _voice_sample(inst, local, len_s, freq, filtered * 3.0)
                    angle = (pan + 1.0) * (math.pi * 0.25)
                    left += sig * math.cos(angle)
                    right += sig * math.sin(angle)
            s_l = max(-32767, min(32767, round(left * env * 32767)))
            s_r = max(-32767, min(32767, round(right * env * 32767)))
            chunk.extend(struct.pack("<hh", s_l, s_r))
            if len(chunk) >= 65536:
                wf.writeframesraw(chunk)
                chunk.clear()
        wf.writeframes(chunk)


def _write_sfx_wav(dest: Path, spec: dict[str, Any], seed: int) -> None:
    rate = 48000
    dur = max(0.08, min(5.0, float(spec.get("duration_sec", 0.35))))
    total_samples = int(round(dur * rate))
    inst = str(spec.get("instrument", "click_transient"))
    freq = float(spec.get("frequency_hz", 440.0))
    amp = 10 ** (float(spec.get("gain_db", -13.0)) / 20.0)
    state = (int(seed) or 7) & 0xFFFFFFFF
    filtered = 0.0

    dest.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(dest), "wb") as wf:
        wf.setparams((2, 2, rate, 0, "NONE", "not compressed"))
        chunk = bytearray()
        for idx in range(total_samples):
            time_s = idx / rate
            state = (1664525 * state + 1013904223) & 0xFFFFFFFF
            noise = (state / 2**32) * 2.0 - 1.0
            filtered = filtered * 0.90 + noise * 0.10
            val = amp * _voice_sample(inst, time_s, dur, freq, filtered * 4.0)
            samp = max(-32767, min(32767, round(val * 32767)))
            chunk.extend(struct.pack("<hh", samp, samp))
        wf.writeframes(chunk)


def _png_chunk(tag: bytes, payload: bytes) -> bytes:
    crc = zlib.crc32(tag + payload) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + tag + payload + struct.pack(">I", crc)


def _write_minimal_rgb_png(dest: Path, width: int, height: int, bg_hex: str, acc_hex: str) -> None:
    r0, g0, b0 = hex_to_rgb(bg_hex)
    r1, g1, b1 = hex_to_rgb(acc_hex)
    top_row = b"\x00" + bytes([r0, g0, b0]) * width
    band_row = b"\x00" + bytes([r1, g1, b1]) * width
    split_y = int(height * 0.62)
    raw = top_row * split_y + band_row * (height - split_y)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png_bytes = (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", zlib.compress(raw, level=6))
        + _png_chunk(b"IEND", b"")
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(png_bytes)


def _write_graphic_plate_png(dest: Path, spec: dict[str, Any]) -> None:
    w = int(spec.get("width", 1080))
    h = int(spec.get("height", 1080))
    colors = spec.get("colors", {})
    bg = str(colors.get("background", "#2b303a"))
    fg = str(colors.get("foreground", "#f4f6f9"))
    acc = str(colors.get("accent", "#d97745"))
    if importlib.util.find_spec("PIL") is None:
        _write_minimal_rgb_png(dest, min(w, 256), min(h, 256), bg, acc)
        return

    from PIL import Image, ImageDraw

    motif = str(spec.get("motif", "horizon_sun"))

    img = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(img)
    mid_col = rgb_to_hex(mix_oklab(bg, fg, 0.16))

    if motif == "horizon_sun":
        sun_r = int(min(w, h) * 0.24)
        cx, cy = w // 2, int(h * 0.44)
        draw.ellipse((cx - sun_r, cy - sun_r, cx + sun_r, cy + sun_r), fill=acc)
        horizon_y = int(h * 0.62)
        draw.rectangle((0, horizon_y, w, h), fill=mid_col)
        for idx in range(6):
            ly = horizon_y + int((h - horizon_y) * (idx + 1) / 7)
            draw.line((int(w * 0.12), ly, int(w * 0.88), ly), fill=fg, width=max(2, w // 360))
    else:
        step = max(24, w // 12)
        for x in range(step, w, step):
            draw.line((x, int(h * 0.10), x, int(h * 0.90)), fill=mid_col, width=2)
        pts = [
            (0, int(h * 0.72)),
            (int(w * 0.28), int(h * 0.48)),
            (int(w * 0.52), int(h * 0.60)),
            (int(w * 0.78), int(h * 0.38)),
            (w, int(h * 0.66)),
            (w, h),
            (0, h),
        ]
        draw.polygon(pts, fill=mid_col, outline=acc)

    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest)


def materialize_starter_asset(
    project_dir: Path | str,
    asset_id: str,
    *,
    duration_sec: float = 8.0,
    seed: int = 42,
) -> dict[str, Any]:
    root = Path(project_dir).resolve(strict=True)
    by_id = {item["id"]: item for item in list_starter_assets()}
    if asset_id not in by_id:
        raise ValueError(f"Unknown starter asset id: {asset_id!r}")
    spec = by_id[asset_id]
    kind = spec["kind"]

    if kind == "music":
        rel = f"assets/starter/music/{asset_id}.wav"
        _write_music_bed_wav(contained_path(root, rel, must_exist=False), spec, duration_sec, seed)
    elif kind == "sfx":
        rel = f"assets/starter/sfx/{asset_id}.wav"
        _write_sfx_wav(contained_path(root, rel, must_exist=False), spec, seed)
    elif kind == "graphic":
        rel = f"assets/starter/graphics/{asset_id}.png"
        _write_graphic_plate_png(contained_path(root, rel, must_exist=False), spec)
    else:
        return {
            "id": asset_id,
            "kind": kind,
            "materialized": False,
            "metadata_only": True,
            "spec": spec,
        }

    lic = record_asset_license(
        root,
        rel,
        spdx=spec["spdx"],
        source_kind="starter_procedural",
        author=spec["author"],
        attribution=f"{spec['author']} ({spec['spdx']})",
    )
    return {
        "id": asset_id,
        "kind": kind,
        "materialized": True,
        "path": rel,
        "license": lic,
    }


def materialize_starter_pack(
    project_dir: Path | str,
    *,
    asset_ids: list[str] | None = None,
    duration_sec: float = 8.0,
    seed: int = 42,
) -> dict[str, Any]:
    root = Path(project_dir).absolute()
    root.mkdir(parents=True, exist_ok=True)
    root = root.resolve(strict=True)
    all_file_ids = [
        item["id"]
        for item in list_starter_assets()
        if item["kind"] in {"music", "sfx", "graphic"}
    ]
    targets = asset_ids if asset_ids else all_file_ids
    results = [
        materialize_starter_asset(root, aid, duration_sec=duration_sec, seed=seed)
        for aid in targets
    ]
    lic_md = write_licenses_markdown(root)
    return {
        "project": str(root),
        "materialized_count": sum(1 for r in results if r.get("materialized")),
        "assets": results,
        "licenses_markdown": lic_md.relative_to(root).as_posix(),
    }
