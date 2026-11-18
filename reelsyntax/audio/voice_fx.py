from array import array
from fractions import Fraction
import math
from pathlib import Path
import struct
import sys
from typing import Any
import wave


def synthesize_retro_dialogue_chirps(
    output_wav_path: Path | str,
    text: str,
    *,
    duration_sec: float,
    base_pitch_hz: float = 240.0,
    seed: int = 42,
) -> dict[str, Any]:
    rate = 48000
    dur = max(0.25, min(60.0, float(duration_sec)))
    total_samples = int(round(dur * rate))
    tokens = [ch for ch in text if not ch.isspace()]
    syllable_count = max(1, min(len(tokens), int(dur * 9.5)))
    slot_sec = dur / max(1, syllable_count + 1)

    events: list[tuple[float, float, float]] = []
    state = (int(seed) or 19) & 0xFFFFFFFF
    for idx in range(syllable_count):
        state = (1664525 * state + 1013904223) & 0xFFFFFFFF
        char_ord = ord(tokens[idx % len(tokens)]) if tokens else 65
        semitone_shift = ((char_ord + (state & 0xFF)) % 9) - 4
        freq = base_pitch_hz * (2.0 ** (semitone_shift / 12.0))
        start_s = idx * slot_sec + 0.02
        len_s = min(0.085, slot_sec * 0.72)
        if start_s + len_s < dur:
            events.append((start_s, len_s, freq))

    dst = Path(output_wav_path)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(dst), "wb") as wf:
        wf.setparams((2, 2, rate, 0, "NONE", "not compressed"))
        chunk = bytearray()
        ev_idx = 0
        ev_count = len(events)
        for s_i in range(total_samples):
            t = s_i / rate
            while ev_idx < ev_count and events[ev_idx][0] + events[ev_idx][1] < t:
                ev_idx += 1
            val = 0.0
            if ev_idx < ev_count:
                st, ln, fq = events[ev_idx]
                if st <= t < st + ln:
                    loc = t - st
                    env = math.sin(math.pi * (loc / ln)) ** 0.7
                    fundamental = math.sin(math.tau * fq * loc)
                    overtone = 0.35 * math.sin(math.tau * (fq * 2.0) * loc)
                    quantized = round((fundamental + overtone) * 12.0) / 12.0
                    val = 0.24 * env * quantized
            samp = max(-32767, min(32767, round(val * 32767)))
            chunk.extend(struct.pack("<hh", samp, samp))
            if len(chunk) >= 65536:
                wf.writeframesraw(chunk)
                chunk.clear()
        wf.writeframes(chunk)

    return {
        "output": str(dst),
        "sample_rate": rate,
        "syllables": len(events),
        "duration_sec": dur,
    }


def apply_voice_fx_wav(
    input_wav_path: Path | str,
    output_wav_path: Path | str,
    *,
    preset: str = "radio_bandpass",
) -> dict[str, Any]:
    if preset not in {"radio_bandpass", "retro_crush", "warm_double"}:
        raise ValueError(f"Unsupported voice FX preset: {preset!r}")

    src = Path(input_wav_path)
    dst = Path(output_wav_path)
    with wave.open(str(src), "rb") as rf:
        params = rf.getparams()
        if params.sampwidth != 2:
            raise ValueError("Voice FX requires 16-bit PCM WAV")
        raw = rf.readframes(params.nframes)

    samples = array("h", raw)
    if sys.byteorder != "little":
        samples.byteswap()

    out = array("h", [0] * len(samples))
    lp = 0.0
    hp_prev = 0.0
    delay_samples = max(1, int(0.014 * params.framerate) * params.nchannels)

    for i, s_val in enumerate(samples):
        x = s_val / 32768.0
        if preset == "retro_crush":
            crushed = round(x * 16.0) / 16.0
            y = crushed * 0.85
        elif preset == "radio_bandpass":
            lp = lp * 0.72 + x * 0.28
            y = max(-0.95, min(0.95, (lp - hp_prev * 0.88) * 1.15))
            hp_prev = lp
        else:
            delayed = (samples[i - delay_samples] / 32768.0) if i >= delay_samples else 0.0
            y = 0.78 * x + 0.22 * delayed
        out[i] = max(-32768, min(32767, round(y * 32767)))

    if sys.byteorder != "little":
        out.byteswap()
    dst.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(dst), "wb") as wf:
        wf.setparams(params)
        wf.writeframes(out.tobytes())

    return {"output": str(dst), "preset": preset, "frames": params.nframes}


def extract_mouth_open_envelope(
    wav_path: Path | str,
    *,
    fps: str | Fraction = "30/1",
    threshold: float = 0.025,
) -> list[float]:
    fps_val = float(Fraction(fps))
    with wave.open(str(wav_path), "rb") as rf:
        rate = rf.getframerate()
        channels = rf.getnchannels()
        nframes = rf.getnframes()
        raw = rf.readframes(nframes)

    samples = array("h", raw)
    if sys.byteorder != "little":
        samples.byteswap()

    total_video_frames = max(1, int(round((nframes / rate) * fps_val)))
    envelope: list[float] = []
    for vf in range(total_video_frames):
        s0 = int(round((vf / fps_val) * rate))
        s1 = min(nframes, max(s0 + 1, int(round(((vf + 1) / fps_val) * rate))))
        sq = 0.0
        cnt = 0
        for si in range(s0, s1):
            v = samples[si * channels] / 32768.0
            sq += v * v
            cnt += 1
        rms = math.sqrt(sq / max(1, cnt))
        mouth = 0.0 if rms < threshold else min(1.0, (rms - threshold) / 0.18)
        envelope.append(round(mouth, 4))
    return envelope
