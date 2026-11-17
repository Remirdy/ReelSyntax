---
name: camera-inertia-rig
description: "Use for physical camera rig inertia. Drive virtual dolly, crane, and Steadicam transforms through analytical second-order mass-spring-damper dynamics."
metadata:
  category: camera
  stage: build
  status: validated
  version: "2.0.0"
  aliases: "kamera ataleti,spring damper camera,inertial camera rig,fiziksel kamera"
  requires: ""
---

# Camera Inertia Rig

## Activation
Use when designing camera translation, look-at target tracking, or focal-length transitions that must exhibit physical rig weight rather than linear or robotic keyframe snaps. Search aliases: kamera ataleti,spring damper camera,inertial camera rig,fiziksel kamera. Never activate when `camera_locked` is enabled in project constraints.

## Inputs and output
- Inputs: Shot duration in frames, rational FPS, camera start/target pose, rig preset (`crane`, `dolly`, `steadicam`, `handheld`), and active brief locks.
- Output: Per-frame deterministic camera pose samples (`position`, `target`, `fov_deg`) and velocity bounds.
- Required capability: Core `reelsyntax.camera` module or compatible 3D engine adapter.
- Evidence bundle: Camera transform curve summary, maximum angular velocity per frame, and rendered motion preview.

## Production recipe
1. Verify `constraints.camera_locked` is false; if locked, abort movement and use `locked-camera`.
2. Parameterize the second-order system $m\ddot{x} + c\dot{x} + k(x - x_{\text{target}}) = 0$ via natural frequency $\omega_n = \sqrt{k/m}$ and damping ratio $\zeta = c / (2\sqrt{mk})$:
   - Precision dolly / motion-control crane: critically damped $\zeta = 1.0$, $\omega_n \in [2.2, 4.0]\text{ rad/s}$ (zero overshoot).
   - Steadicam follow: slightly underdamped $\zeta \in [0.82, 0.92]$, $\omega_n \in [1.8, 3.2]\text{ rad/s}$ (subtle organic settle).
3. Evaluate closed-form analytical solutions directly at canonical time $t = f / \text{fps}$ so frame seeking is stateless and exact at any framerate.
4. Decouple translation damping from look-at rotational damping ($\omega_{\text{rot}} \approx 1.25\,\omega_{\text{pos}}$) so framing leads or lags intentionally without horizon roll drift.
5. Check angular pan rate against `shutter-angle-judder` limits before committing full-resolution renders.

## Acceptance criteria
- Frame $f$ evaluates identically whether rendered sequentially or sought out of order.
- Critically damped rigs exhibit zero sign-reversal overshoot; Steadicam overshoot stays $\le 3\%$ of travel distance.
- Record concrete evidence path, frame range, measured peak angular velocity (deg/frame), and status (`pass`, `fail`, `review`, `blocked`).

## Failure and repair
If the camera fails to settle before the outgoing cut hold, increase $\omega_n$ or advance target arrival by $0.35\text{ s}$ so the final $8\text{–}12$ frames read cleanly. Recheck `camera-continuity` across adjacent cuts.

## Resources (load only if needed)
- [Production quality contract](../../../QUALITY_STANDARD.md) — shared gates and review rubric.
- [Three.js PerspectiveCamera](https://threejs.org/docs/#api/en/cameras/PerspectiveCamera)
- [Blender Camera Data](https://docs.blender.org/api/current/bpy.types.Camera.html)

Original production guidance and validated runtime math.
