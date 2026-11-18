from array import array
from fractions import Fraction
from pathlib import Path
import sys
from typing import Any
import wave


def beat_grid_frames(
    bpm: float,
    fps: str | Fraction,
    total_frames: int,
    *,
    beats_per_bar: int = 4,
) -> dict[str, list[int]]:
    if bpm <= 0:
        raise ValueError("BPM must be positive")
    fps_val = float(Fraction(fps))
    sec_per_beat = 60.0 / float(bpm)
    beats: list[int] = []
    bars: list[int] = []
    idx = 0
    while True:
        frame = int(round(idx * sec_per_beat * fps_val))
        if frame >= total_frames:
            break
        if not beats or beats[-1] != frame:
            beats.append(frame)
            if idx % max(1, beats_per_bar) == 0:
                bars.append(frame)
        idx += 1
    return {"beats": beats, "bars": bars}


def apply_sidechain_ducking_wav(
    music_wav_path: Path | str,
    output_wav_path: Path | str,
    speech_intervals_sec: list[tuple[float, float]],
    *,
    duck_db: float = -9.0,
    attack_sec: float = 0.08,
    release_sec: float = 0.22,
) -> dict[str, Any]:
    src = Path(music_wav_path)
    dst = Path(output_wav_path)
    with wave.open(str(src), "rb") as rf:
        params = rf.getparams()
        if params.sampwidth != 2:
            raise ValueError("Sidechain ducking requires 16-bit PCM WAV")
        rate = params.framerate
        channels = params.nchannels
        nframes = params.nframes
        raw = rf.readframes(nframes)

    samples = array("h", raw)
    if sys.byteorder != "little":
        samples.byteswap()

    target_linear = 10.0 ** (duck_db / 20.0)
    attack_step = (1.0 - target_linear) / max(1.0, attack_sec * rate)
    release_step = (1.0 - target_linear) / max(1.0, release_sec * rate)

    intervals = sorted((max(0.0, float(a)), max(0.0, float(b))) for a, b in speech_intervals_sec if b > a)
    gain = 1.0
    iv_idx = 0
    iv_count = len(intervals)

    for frame_i in range(nframes):
        t = frame_i / rate
        while iv_idx < iv_count and intervals[iv_idx][1] < t:
            iv_idx += 1
        active = iv_idx < iv_count and intervals[iv_idx][0] <= t <= intervals[iv_idx][1]
        if active:
            gain = max(target_linear, gain - attack_step)
        else:
            gain = min(1.0, gain + release_step)
        base_off = frame_i * channels
        for ch in range(channels):
            samples[base_off + ch] = max(-32768, min(32767, round(samples[base_off + ch] * gain)))

    out_bytes = array("h", samples)
    if sys.byteorder != "little":
        out_bytes.byteswap()

    dst.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(dst), "wb") as wf:
        wf.setparams(params)
        wf.writeframes(out_bytes.tobytes())

    return {
        "output": str(dst),
        "sample_rate": rate,
        "frames": nframes,
        "duck_db": duck_db,
        "intervals_ducked": len(intervals),
    }
