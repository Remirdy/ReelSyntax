---
name: verlet-constraint-solver
description: "Use for Verlet constraint physics. Simulate deterministic ropes, cables, ribbons, and secondary pendulums from canonical frame indices using fixed-substep Verlet projection."
metadata:
  category: motion
  stage: build
  status: validated
  version: "2.0.0"
  aliases: "verlet physics,ip simülasyonu,position based dynamics,kablo fiziği"
  requires: ""
---

# Verlet Constraint Solver

## Activation
Use when animating hanging cables, banners, ribbons, tethered tags, or secondary follow-through chains that require believable gravity and tension without external physics engines. Search aliases: verlet physics,ip simülasyonu,position based dynamics,kablo fiziği.

## Inputs and output
- Inputs: Particle rest positions, pinned anchor trajectory, gravity vector, damping $d \in [0.97, 0.998]$, solver iterations, and target frame index.
- Output: Deterministic particle coordinates per frame with bounded segment stretch.
- Required capability: `reelsyntax.motion` Verlet solver or host animation script.
- Evidence bundle: Maximum constraint stretch error ($< 1\%$), seek-determinism check, and motion preview.

## Production recipe
1. Never integrate physics using wall-clock frame deltas; advance from canonical initial state $(x_0, x_{-1})$ at fixed simulation timestep $\Delta t = 1 / (S \cdot \text{fps})$ with $S \ge 4$ substeps per output frame up to requested frame $f$.
2. Apply position Verlet update: $x_i^{(n+1)} = x_i^{(n)} + d\,(x_i^{(n)} - x_i^{(n-1)}) + \mathbf{g}\,\Delta t^2$.
3. Enforce pinned anchors and segment rest lengths $L_{ij}$ across $8\text{–}16$ Gauss-Seidel relaxation sweeps per substep, splitting corrections by inverse mass ($0$ for pinned roots, $0.5/0.5$ for equal interior nodes).
4. Pre-warm $20\text{–}40$ equilibrium substeps at $t < 0$ when a scene opens on an already hanging structure so frame $0$ does not drop from horizontal T-pose.

## Acceptance criteria
- Seeking frame $f$ twice yields bit-identical coordinates; maximum rest-length error stays below $1\%$.
- No high-frequency jitter or energy explosion across full shot duration.
- Record substep count, iteration count, max stretch error, and visual continuity review.

## Failure and repair
Stretchy or vibrating chains indicate insufficient relaxation sweeps per frame or stiff impulses: double substep count $S$ rather than increasing damping until motion turns sluggish.

## Resources (load only if needed)
- [Production quality contract](../../../QUALITY_STANDARD.md) — shared gates and review rubric.

Original production guidance and validated runtime math.
