# UI Scaling Strategy

> **Status (Issue #472):** Reviewed and deemed unnecessary after token cleanup; the reported scaling issue was caused by site-specific browser zoom. This document is archived for future reference.

**Purpose**  
Define a deterministic, accessible, and hardware-agnostic UI scaling strategy suitable for desktop-first web applications. This document is intended to be both human-readable and agent-actionable, enabling automated or semi-automated implementation without reliance on browser- or OS-specific heuristics.

---

## 1. Design Goals

1. **Accessibility-first**
   - Respect browser zoom, OS scaling, and user font overrides.
   - Avoid techniques that break text scaling or assistive technologies.

2. **Hardware-agnostic**
   - Do not assume physical DPI, monitor size, or device pixel ratio.
   - Operate solely in CSS layout units (CSS pixels).

3. **Predictable scaling**
   - Preserve layout and typographic consistency on small and mid-size desktop displays.
   - Gradually increase UI scale on large displays where increased viewing distance is common.

4. **No JavaScript dependency**
   - Scaling logic must be expressible entirely in CSS.
   - JavaScript may observe layout but must not control scaling.

5. **Uniform scale**
   - Apply the same scale factor to typography, spacing, and control sizing.
   - Drive sizes through shared tokens so the scale is global and deterministic.

---

## 2. Baseline Viewport Assumptions

| Parameter | Value |
|----------|-------|
| Minimum supported desktop viewport | **1280 × 720** |
| Baseline design width | **1920px** |
| Maximum scale threshold | **2560px** |

- Layout must fully function at **1280×720** without overflow or clipping.
- The UI is visually “correct” at **1920px**, where scale = **100%**.
- Above **2560px**, scaling is capped to prevent excessive magnification.
- Below **1920px**, the scale remains at **100%** and responsive layout rules
  handle smaller viewports (including < 1280px).

---

## 3. Authoritative Measurement

### 3.1 Layout Width Source

- **CSS viewport width (`vw`) is the sole authoritative signal**
- JavaScript equivalents (reference only):
  - Layout parity: `document.documentElement.clientWidth`
  - Visual parity: `window.innerWidth` (not used for scaling)

### 3.2 Explicitly Excluded Signals

| Signal | Reason |
|------|--------|
| `window.devicePixelRatio` | Rendering density only; unstable under zoom |
| `screen.width / height` | Virtualized, non-layout |
| Physical DPI | Not reliably detectable |

### 3.3 Accessibility Baseline

- `vw` provides a multiplier only.
- Base sizes stay rooted in `rem` (or equivalent tokens) so browser font overrides
  remain effective.

---

## 4. Scaling Model

### 4.1 Scale Regions

| Viewport Width | Scale Behavior |
|---------------|----------------|
| `< 1920px` | **Fixed scale (100%)** |
| `1920px – 2560px` | **Linear interpolation from 100% → 120%** |
| `> 2560px` | **Clamped at 120%** |

### 4.2 Uniform Scaling Targets

- Apply the scale to typography, spacing, and control sizing using shared CSS tokens.
- Avoid setting the root font-size directly from `vw`; the scale multiplies the
  accessible baseline instead.

---

## 5. Validation Examples (Draft)

Expected scale values (rounded) for quick checks and tests:

| Viewport Width | Expected Scale |
|---------------|----------------|
| 1920px | 1.00 |
| 2000px | 1.03 |
| 2200px | 1.09 |
| 2240px | 1.10 |
| 2560px | 1.20 |
| 3000px | 1.20 (clamped) |

---

## 6. Implementation Plan (Agent-Ready)

1. **Token hygiene (ui-foundation.css)**
   - Define missing tokens (`--wc-font-sm`, `--wc-font-xs`, `--wc-font-weight-normal`,
     `--wc-font-weight-semibold`, `--wc-radius-xs`).
   - Replace any stray hard-coded font sizes/weights where tokens already exist.

2. **Global scale token (ui-foundation.css)**
   - Add `--wc-scale` computed from viewport width using `clamp()` and a linear
     interpolation between 1920px and 2560px (1.0 → 1.2).
   - Apply `--wc-scale` as a multiplier on the accessible baseline, not a replacement:
     `html { font-size: calc(100% * var(--wc-scale)); }`.

3. **Rem-first sizing pass**
   - Convert fixed px sizes in `ui-foundation.css` to `rem` or scale-aware tokens
     (widths, heights, spacing, radii).
   - Spot-check inline styles in templates that import `ui-foundation.css`, at least:
     - `wepppy/weppcloud/templates/base_pure.htm`
     - `wepppy/weppcloud/routes/usersum/templates/usersum/layout.j2`
     - `wepppy/weppcloud/routes/browse/templates/browse/markdown_file.htm`

4. **Validation**
   - Add a smoke check (new spec or extend existing) that asserts computed scale
     values at 1920/2200/2560 widths and a representative component size.
   - Confirm behavior at <1920px remains 1.0 and relies on responsive layout.

5. **Rollout**
   - Run through a small set of layouts (usersum markdown, pure pages, run header)
     and confirm no overflow regressions.
   - Update this document with the final formula and any tested edge cases.

---

## 7. Status

Scaling was reviewed after token cleanup and determined to be unnecessary at this time.
Current behavior is acceptable; the reported issue was traced to user-applied, site-specific
browser zoom. This strategy remains archived for future reference if display-density
requirements change.
