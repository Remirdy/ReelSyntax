# Linear-Light `cos^4` Vignette and Halation Shader Reference

```glsl
vec3 applyOpticalFinish(vec3 linColor, vec3 brightBlur, vec2 uv, float k, float halGain, float hashNoise) {
    vec2 centered = (uv - 0.5) / 0.70710678;
    float r = length(centered);
    float vig = pow(cos(clamp(k * r, 0.0, 1.2)), 4.0);
    vec3 hal = brightBlur * vec3(1.0, 0.38, 0.08) * halGain;
    vec3 combined = (linColor + hal) * vig;
    vec3 srgb = pow(max(combined, vec3(0.0)), vec3(1.0 / 2.2));
    return clamp(srgb + (hashNoise - 0.5) / 255.0, 0.0, 1.0);
}
```

Keep `k ∈ [0.20, 0.42]` and `halGain ∈ [0.0, 0.14]`. Always composite sharp captions *after* `applyOpticalFinish`.
