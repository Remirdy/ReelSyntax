from array import array
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave

from reelsyntax.assets import materialize_starter_asset
from reelsyntax.audio import (
    apply_sidechain_ducking_wav,
    apply_voice_fx_wav,
    beat_grid_frames,
    build_scene_word_timings,
    build_transition_sfx_cues,
    extract_mouth_open_envelope,
    probe_stt_status,
    probe_tts_status,
    synthesize_retro_dialogue_chirps,
    synthesize_speech_or_fallback,
    wrap_caption_lines,
)
from reelsyntax.captions import caption_events
from reelsyntax.cli import main as cli_main


class AudioPipelineTests(unittest.TestCase):
    def test_measured_tts_and_stt_probes_never_hardcode_availability(self) -> None:
        empty_env = {"PATH": "", "REELSYNTAX_TTS_MODELS_DIR": "/nonexistent"}
        tts_none = probe_tts_status(languages=("en", "tr", "de"), platform_name="linux", environ=empty_env)
        self.assertTrue(tts_none["measured"])
        for code in ("en", "tr", "de"):
            self.assertFalse(tts_none["languages"][code]["available"])
            self.assertEqual(tts_none["languages"][code]["fallback"], "captions_and_music")

        stt_none = probe_stt_status(environ=empty_env)
        self.assertTrue(stt_none["measured"])
        self.assertIn("whisper_cli", stt_none["runtimes"])

        buf = io.StringIO()
        with patch("sys.stdout", buf):
            rc = cli_main(["doctor", "--tts", "--stt", "--json"])
        self.assertEqual(rc, 0)
        res = json.loads(buf.getvalue())["result"]
        self.assertIn("tts", res)
        self.assertIn("stt", res)

    def test_tts_unavailable_falls_back_cleanly_to_captions_and_music(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "fallback-proj"
            proj.mkdir()
            scenes = [
                {"id": "s1", "duration_frames": 45, "params": {"heading": "NET ODAK", "subheading": "Sade kurgu ritmi"}},
                {"id": "s2", "duration_frames": 45, "params": {"heading": "HIZLI SONUÇ", "subheading": "Yerel doğrulama"}},
            ]
            res = synthesize_speech_or_fallback(
                proj,
                scenes,
                lang="tr",
                ui_lang="tr",
                prefer_tts=False,
                environ={"PATH": ""},
            )
            self.assertEqual(res["mode"], "captions_and_music")
            self.assertIn("altyazı ve müzik", res["notice"])
            self.assertTrue((proj / res["music_path"]).is_file())
            self.assertTrue((proj / res["words_path"]).is_file())
            self.assertTrue((proj / "LICENSES.md").is_file())

    def test_beat_grid_sidechain_ducking_and_transition_sfx(self) -> None:
        grid = beat_grid_frames(120.0, "30/1", 120, beats_per_bar=4)
        self.assertEqual(grid["beats"][:5], [0, 15, 30, 45, 60])
        self.assertEqual(grid["bars"], [0, 60])

        scenes = [
            {"id": "a", "duration_frames": 30},
            {"id": "b", "duration_frames": 30, "transition": {"type": "wipe_left", "duration_frames": 6}},
            {"id": "c", "duration_frames": 30, "transition": {"type": "glitch", "duration_frames": 4}},
        ]
        cues = build_transition_sfx_cues(scenes, include_opening_hit=True)
        self.assertEqual(cues[0]["instrument"], "sub_impact")
        self.assertEqual(cues[1]["instrument"], "whoosh")
        self.assertEqual(cues[2]["instrument"], "click_transient")

        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "duck-proj"
            proj.mkdir()
            bed = materialize_starter_asset(proj, "editorial-pulse-bed", duration_sec=2.0, seed=5)
            bed_abs = proj / bed["path"]
            ducked_abs = proj / "assets/audio/ducked.wav"

            duck_res = apply_sidechain_ducking_wav(bed_abs, ducked_abs, [(0.5, 1.5)], duck_db=-12.0)
            self.assertEqual(duck_res["intervals_ducked"], 1)

            with wave.open(str(bed_abs), "rb") as wf_orig, wave.open(str(ducked_abs), "rb") as wf_duck:
                orig_s = array("h", wf_orig.readframes(wf_orig.getnframes()))
                duck_s = array("h", wf_duck.readframes(wf_duck.getnframes()))
                if sys.byteorder != "little":
                    orig_s.byteswap()
                    duck_s.byteswap()
            mid_slice = slice(48000 * 2, int(48000 * 2.6))
            orig_energy = sum(abs(v) for v in orig_s[mid_slice])
            duck_energy = sum(abs(v) for v in duck_s[mid_slice])
            self.assertLess(duck_energy, orig_energy * 0.45)

    def test_retro_dialogue_chirps_voice_fx_and_lip_sync_envelope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            chirp_wav = root / "chirp.wav"
            info = synthesize_retro_dialogue_chirps(chirp_wav, "Hello traveler, check the signal!", duration_sec=1.5, seed=33)
            self.assertGreaterEqual(info["syllables"], 4)

            fx_wav = root / "chirp_radio.wav"
            fx_res = apply_voice_fx_wav(chirp_wav, fx_wav, preset="radio_bandpass")
            self.assertEqual(fx_res["preset"], "radio_bandpass")

            env = extract_mouth_open_envelope(chirp_wav, fps="30/1")
            self.assertEqual(len(env), 45)
            self.assertGreater(max(env), 0.1)
            self.assertIn(0.0, env)

    def test_language_aware_caption_wrapping_and_word_timing_compatibility(self) -> None:
        de_lines = wrap_caption_lines(
            "Deterministische Bildratenprüfung sichert verlässliche Ergebnisse im Schnitt",
            lang="de",
        )
        self.assertLessEqual(len(de_lines), 2)
        for line in de_lines:
            self.assertLessEqual(len(line), 38)

        scenes = [
            {"id": "one", "duration_frames": 30, "params": {"heading": "CLEAN AUDIO", "subheading": "Exact frames"}},
            {"id": "two", "duration_frames": 30, "params": {"heading": "ZERO DRIFT", "subheading": "Synced cues"}},
        ]
        words = build_scene_word_timings(scenes, fps="30/1")
        events = list(caption_events({"scenes": scenes}, words))
        self.assertEqual(len(events), len(words))
        self.assertEqual(events[0][0], 0)
        self.assertEqual(events[-1][1], 60)


if __name__ == "__main__":
    unittest.main()
