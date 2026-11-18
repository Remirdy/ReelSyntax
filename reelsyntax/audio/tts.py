import importlib.util
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any

from ReelSyntax_Skills.tools.registry import atomic_json, contained_path

from ..assets import materialize_starter_asset, record_asset_license, write_licenses_markdown
from ..lang.catalog import translate
from ..lang.profiles import list_profiles, load_profile
from ..media import executable, run
from .captions import build_scene_word_timings

DARWIN_VOICE_LANG_RE = re.compile(r"\s+([a-z]{2,3})[_-]([A-Za-z]{2,4})\s+")


def _discover_piper(environ: dict[str, str] | None = None) -> dict[str, Any]:
    env = os.environ if environ is None else environ
    explicit = env.get("REELSYNTAX_PIPER", "")
    binary = explicit if (explicit and Path(explicit).is_file()) else shutil.which("piper", path=env.get("PATH"))
    models_dir_raw = env.get("REELSYNTAX_TTS_MODELS_DIR")
    if models_dir_raw:
        models_dir = Path(models_dir_raw).expanduser()
    elif sys.platform == "win32":
        base = Path(env.get("LOCALAPPDATA") or (Path.home() / "AppData/Local"))
        models_dir = base / "reelsyntax/voices"
    elif sys.platform == "darwin":
        models_dir = Path.home() / "Library/Application Support/reelsyntax/voices"
    else:
        models_dir = Path(env.get("XDG_DATA_HOME") or (Path.home() / ".local/share")) / "reelsyntax/voices"

    installed_langs: set[str] = set()
    if models_dir.is_dir():
        for onnx in models_dir.glob("*.onnx"):
            prefix = onnx.stem.split("_", 1)[0].split("-", 1)[0].lower()
            if 2 <= len(prefix) <= 3:
                installed_langs.add(prefix)
    return {
        "available": bool(binary),
        "binary": str(binary) if binary else None,
        "models_dir": str(models_dir),
        "model_languages": sorted(installed_langs),
    }


def _discover_espeak(environ: dict[str, str] | None = None) -> dict[str, Any]:
    env = os.environ if environ is None else environ
    binary = shutil.which("espeak-ng", path=env.get("PATH")) or shutil.which("espeak", path=env.get("PATH"))
    langs: set[str] = set()
    if binary:
        try:
            proc = subprocess.run([binary, "--voices"], capture_output=True, text=True, timeout=8, check=False)
            if proc.returncode == 0:
                for line in proc.stdout.splitlines()[1:]:
                    parts = line.split()
                    if len(parts) >= 2:
                        code = parts[1].split("-", 1)[0].lower()
                        if 2 <= len(code) <= 3:
                            langs.add(code)
        except (OSError, subprocess.TimeoutExpired):
            pass
    return {
        "available": bool(binary),
        "binary": str(binary) if binary else None,
        "languages": sorted(langs),
    }


def _discover_macos_say(platform_name: str | None = None, environ: dict[str, str] | None = None) -> dict[str, Any]:
    plat = sys.platform if platform_name is None else platform_name
    env = os.environ if environ is None else environ
    if plat != "darwin":
        return {"available": False, "binary": None, "voices_by_lang": {}}
    binary = shutil.which("say", path=env.get("PATH")) or ("/usr/bin/say" if Path("/usr/bin/say").is_file() else None)
    if not binary:
        return {"available": False, "binary": None, "voices_by_lang": {}}
    voices_by_lang: dict[str, list[str]] = {}
    try:
        proc = subprocess.run([binary, "-v", "?"], capture_output=True, text=True, timeout=8, check=False)
        if proc.returncode == 0:
            for line in proc.stdout.splitlines():
                m = DARWIN_VOICE_LANG_RE.search(line)
                if m:
                    lang_code = m.group(1).lower()
                    voice_name = line[: m.start()].strip()
                    if voice_name:
                        voices_by_lang.setdefault(lang_code, []).append(voice_name)
    except (OSError, subprocess.TimeoutExpired):
        pass
    return {
        "available": bool(voices_by_lang),
        "binary": str(binary),
        "voices_by_lang": {k: sorted(set(v)) for k, v in sorted(voices_by_lang.items())},
    }


def probe_tts_status(
    *,
    languages: tuple[str, ...] | None = None,
    platform_name: str | None = None,
    environ: dict[str, str] | None = None,
) -> dict[str, Any]:
    target_langs = list(languages) if languages is not None else list_profiles()
    piper = _discover_piper(environ=environ)
    espeak = _discover_espeak(environ=environ)
    say_info = _discover_macos_say(platform_name=platform_name, environ=environ)

    per_language: dict[str, dict[str, Any]] = {}
    for lang in target_langs:
        primary = lang.split("-", 1)[0].lower()
        engines_ready: list[str] = []
        if piper["available"] and primary in piper["model_languages"]:
            engines_ready.append("piper")
        if espeak["available"] and primary in espeak["languages"]:
            engines_ready.append("espeak")
        if say_info["available"] and primary in say_info["voices_by_lang"]:
            engines_ready.append("macos_say")
        per_language[primary] = {
            "available": bool(engines_ready),
            "engines": engines_ready,
            "fallback": "captions_and_music" if not engines_ready else "none",
        }

    return {
        "measured": True,
        "runtimes": {
            "piper": piper,
            "espeak": espeak,
            "macos_say": say_info,
        },
        "languages": per_language,
    }


def probe_stt_status(environ: dict[str, str] | None = None) -> dict[str, Any]:
    env = os.environ if environ is None else environ
    whisper_cli = shutil.which("whisper-cli", path=env.get("PATH")) or shutil.which("whisper", path=env.get("PATH"))
    vosk_cli = shutil.which("vosk-transcriber", path=env.get("PATH"))
    faster_whisper_pkg = importlib.util.find_spec("faster_whisper") is not None
    vosk_pkg = importlib.util.find_spec("vosk") is not None

    runtimes = {
        "whisper_cli": {"available": bool(whisper_cli), "binary": str(whisper_cli) if whisper_cli else None},
        "faster_whisper": {"available": faster_whisper_pkg, "package_installed": faster_whisper_pkg},
        "vosk": {"available": bool(vosk_cli or vosk_pkg), "binary": str(vosk_cli) if vosk_cli else None, "package_installed": vosk_pkg},
    }
    return {
        "measured": True,
        "available": any(v["available"] for v in runtimes.values()),
        "runtimes": runtimes,
    }


def synthesize_speech_or_fallback(
    project_dir: Path | str,
    scenes: list[dict[str, Any]],
    *,
    lang: str = "en",
    ui_lang: str | None = None,
    fps: str = "30/1",
    seed: int = 42,
    prefer_tts: bool = True,
    environ: dict[str, str] | None = None,
) -> dict[str, Any]:
    root = Path(project_dir).resolve(strict=True)
    primary = lang.split("-", 1)[0].lower()
    prof = load_profile(primary)
    status = probe_tts_status(languages=(primary,), environ=environ)
    lang_info = status["languages"].get(primary, {"available": False, "engines": []})

    word_timings = build_scene_word_timings(scenes, fps=fps, max_cps=int(prof["caption"]["max_cps"]))
    words_rel = "assets/captions/words.json"
    words_abs = contained_path(root, words_rel, must_exist=False)
    atomic_json(words_abs, word_timings)
    record_asset_license(root, words_rel, spdx="CC0-1.0", source_kind="starter_procedural", author="ReelSyntax Caption Timing")

    if prefer_tts and lang_info["available"]:
        text_joined = ". ".join(
            " ".join(str(s.get("params", {}).get(k, "")) for k in ("heading", "subheading")).strip()
            for s in scenes
        ).strip()
        engine_choice = lang_info["engines"][0]
        if text_joined and engine_choice in {"espeak", "macos_say"}:
            raw_out = root / ".reelsyntax/tmp_tts_raw.aiff" if engine_choice == "macos_say" else root / ".reelsyntax/tmp_tts_raw.wav"
            raw_out.parent.mkdir(parents=True, exist_ok=True)
            if engine_choice == "macos_say":
                say_bin = status["runtimes"]["macos_say"]["binary"]
                voice = status["runtimes"]["macos_say"]["voices_by_lang"][primary][0]
                proc = subprocess.run([say_bin, "-v", voice, "-o", str(raw_out), text_joined], capture_output=True, timeout=30, check=False)
            else:
                esp_bin = status["runtimes"]["espeak"]["binary"]
                proc = subprocess.run([esp_bin, "-v", primary, "-w", str(raw_out), text_joined], capture_output=True, timeout=30, check=False)
            if proc.returncode == 0 and raw_out.is_file():
                voice_rel = "assets/audio/voice.wav"
                voice_abs = contained_path(root, voice_rel, must_exist=False)
                voice_abs.parent.mkdir(parents=True, exist_ok=True)
                run([
                    executable("ffmpeg"), "-v", "error", "-nostdin", "-y",
                    "-i", str(raw_out), "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(voice_abs),
                ])
                raw_out.unlink(missing_ok=True)
                record_asset_license(root, voice_rel, spdx="User-Provided", source_kind="local_tts", author=engine_choice)
                write_licenses_markdown(root)
                return {
                    "mode": "tts",
                    "engine": engine_choice,
                    "language": primary,
                    "voice_path": voice_rel,
                    "words_path": words_rel,
                    "word_count": len(word_timings),
                }

    bed = materialize_starter_asset(root, "ambient-focus-bed", duration_sec=max(2.0, sum(int(s["duration_frames"]) for s in scenes) / 30.0), seed=seed)
    write_licenses_markdown(root)
    notice = translate("audio.tts_fallback", locale=ui_lang or primary, lang=primary)
    return {
        "mode": "captions_and_music",
        "engine": None,
        "language": primary,
        "notice": notice,
        "music_path": bed["path"],
        "words_path": words_rel,
        "word_count": len(word_timings),
    }
