# Periodic GLSL Phase, Circular Noise, and Seam-Ratio Verification Math

```glsl
const float TAU = 6.283185307179586;

float loopPhase(int frameIndex, int totalFrames) {
    return TAU * float(frameIndex) / float(totalFrames);
}

vec4 circularNoiseCoord(vec2 uv, float theta, float radius) {
    return vec4(uv, radius * cos(theta), radius * sin(theta));
}
```

## Seam-ratio verification rule
Let `d_wrap = mean_abs_diff(frame[N - 1], frame[0])` and `d_med = median_{i=0..N-2}(mean_abs_diff(frame[i], frame[i + 1]))`:
- If `d_med > 0.2/255` and `d_wrap < 0.05 * d_med`: **duplicate terminal frame bug** (`/(N-1)` error).
- If `d_wrap > 2.5 * d_med + 1.5/255`: **discontinuous wrap pop** (non-integer harmonic or linear `t` leak).
- Target pass band: `0.55 * d_med <= d_wrap <= 1.65 * d_med`.
