# MC4 retained-state reference and fixed-point review

Independent scientific/correctness review, 2026-10-21. This review covers the
isolated `mc-reference-candidate-v5` under
`/workdir/watershed-physical-water-repair-20261021/`. Production source was not
edited by this reviewer. It preserves the operator's MC storage authority;
geometric volume is not an acceptance target.

## Disposition

**Support the bounded MC4 reference carry and exact fixed-point optimization,
conditional on successful full gates.**
These address a demonstrated propagation defect and its measured floating-point
runtime consequence without changing the MC recurrence, imposing geometric
storage, or deleting small raw states. This is a scoped approval, not closure of
the signed channel/soil coupling findings in
[signed-coupling-review.md](signed-coupling-review.md).

The previous interface candidate failed the full gate: the 100-year upstream
fixture timed out at 900 seconds, after reaching year 16/day 81/channel 20;
the suite reported 409 passed and one failed. Earlier successful results for
the guard checkpoint do not discharge this gate. The isolated controls below
establish causality and parity, not full-fixture performance acceptance.

## High: a zero boundary reference prevents retained MC4 flow from propagating

WSHCHR selects a daily reference using current boundary rates and previous
exported rates, before CHRSTATE restores the retained interior profile. The
MC4 coefficient branch sets K=X=0 when `qref <= eps`, where the existing eps is
1e-8. Its recurrence coefficients then become c1=c2=1 and c3=-1. With zero
forcing, induction over the spatial cells gives:

```text
qs(j,t) = -qs(j,t-1)
```

The raw profile alternates signs each interval. An even number of intervals
restores the same midnight profile indefinitely. Executing a live interior is
necessary, but execution alone cannot transport that state under this reference.
The zero-celerity grid fallback also selects 101 cells in the tested channel.

Relevant isolated source locations are `src/wshchr.for:341` (reference),
`:349` (bounded carry), `:503` (K/X branch), and `src/chrstate.for:35`
(read-only retained-state query). The exact paths and source hashes are retained
in the external manifests.

An actual WSHCQI/WSHCHR three-day control supplies a 100 m³ late top pulse after
a dry initialization day, followed by a dry recession day. At 600-second steps:

| Reference policy on the recession day | Reference m³/s | Cells | Three-day accepted export m³ |
| --- | ---: | ---: | ---: |
| Existing boundary-only reference | 0 | 101 | 0 |
| Carry last valid positive MC4 reference | 0.0138888890 | 58 | 99.9998847 |
| Derive half the positive interior maximum | 0.0137725305 | 58 | 100.3233238 |

The last alternative changes the coefficient coordinate unnecessarily in this
control. Carrying the existing reference is the narrower choice: it reuses a
parameterization already accepted for this channel. The result is not a general
proof of geometric or physical mass closure. MC coefficient revaluation,
regridding, raw/export clipping and source quadrature remain separate accounting
terms.

## Bounded reference contract

The reviewed fallback applies only when all conditions hold:

1. The selected method is MC4.
2. The ordinary daily reference is in the existing degenerate branch,
   `qref <= eps`.
3. CHRSTATE has a nonzero retained interior profile for this channel.
4. The same channel has a previously accepted reference greater than eps.

The prior reference is initialized per channel and reset on the existing
first-call sentinel (`nt0=0`). A degenerate daily reference must not replace a
valid cached reference. The retained-state query is read-only and ignores old
state on a first call. MC5 and KW selection are unchanged.

An exact-zero-only fallback is insufficient: a boundary reference near 5e-10
with the material pulse still retained produces zero export. Extending the
predicate to the existing `<= eps` branch restores propagation in this control.
No new discharge floor or fitted threshold is introduced.

With a valid reference history, weak positive state (3e-9), negative state, and
positive/negative minimum subnormal seeds distinguish the policies further.
Half of the positive interior maximum remains degenerate or becomes zero;
carrying the valid reference continues the accepted recurrence. All-dry and
tiny-pulse controls without valid reference history remain unchanged. The
no-history degenerate path remains an explicit limitation, not a hidden fallback
to an invented reference.

## Medium: native 60-second steps retain subnormal fixed states

The fixture uses the native lower limit of 60 seconds, or 1440 steps/day.
At 600-second steps the controlled pulse eventually reaches exact zero. At
60-second steps, after carrying a positive reference, the natural pulse
recession reaches a profile whose 101 nodes are each 2.8025969e-45 and remains
there through day 12. It still executes 145440 recurrence cells each dry day.
Explicit minimum positive and negative subnormal seeds also persist under
positive K and c3 near 0.81. This was measured, not inferred from elapsed time.

Dropping all state below eps would introduce a new storage-loss rule. The
reviewed correction instead recognizes an exact fixed point in the existing
finite-precision recurrence and retains every state value.

## Exact fixed-point contract and proof

MC4 coefficients are fixed within one routing day. The implementation records
the final adjacent change in the assembled qin and normalized qlat arrays. At
an interval strictly after that index, the preceding, current, and all future
forcing values are identical. It then requires both:

- The entire raw spatial profile, including its upstream node, is bit-identical
  to the preceding interval's profile.
- The accepted outlet value is bit-identical to its preceding value. This
  includes the prior exported rate used by the recurrence eligibility guard.

The following interval therefore has identical forcing, coefficients, raw
state and guard inputs. Deterministic evaluation repeats the same raw profile
and exported rate. Induction permits copying those values through the remaining
intervals. The ordinary final-state save, publication and downstream handoff
then consume exactly the same arrays. This optimization does not resolve the
K=0 period-two material profile; the bounded reference correction is still
needed.

The actual v5 implementation compares the forcing, raw profile and exported
guard through `TRANSFER` to integer storage and is explicitly MC4-only
(`src/wshchr.for:539` and `:612`). The harness verifies 32-bit default REAL and
INTEGER storage, matching the native build contract. It uses no tolerance and
retains subnormal values. Copying is limited to the current day; a later forcing
change or a new day must be handled normally.

The preceding v4 implementation used numeric equality, which treats positive
and negative zero as equal. An explicit signed-zero boundary control reproduced
a raw-array mismatch at both 600 and 60 seconds. v5's bit comparisons close that
finding. The signed-zero control is an isolated representation test after source
assembly, not a claim that a supplied production source generated this endpoint.

## Independent verification

External retained receipts and scripts use the common root
`/workdir/watershed-physical-water-repair-20261021/`:

- `reviewer-reference-v1/receipt.json`: original, carry, and interior-derived
  references; ordinary early-pulse MC4 and MC5 controls unchanged.
- `reviewer-reference-v2/receipt.json`: zero versus small positive boundary
  reference, weak/negative/subnormal state, all-dry and no-history tiny input.
- `reviewer-reference-v3/receipt.json`: 12-day 600/60-second state persistence.
- `reviewer-reference-v4/receipt.json`: prototype fixed-point parity.
- `reviewer-reference-v6/receipt.json`: actual v4 versus the same source with
  only the shortcut removed; 24 controls pass, two signed-zero controls fail.
- `reviewer-reference-v7/receipt.json`: actual v5 versus the same source with
  only the shortcut removed; all 26 controls pass.
- `reviewer_actual_fixedpoint_probe.py`: reproducible actual-source pairing,
  with compiler/source hashes in the v7 manifest.

Each final pair compares SHA256 hashes of **every raw spatial/time qs value and
every exported q1 value**, plus daily publication. The 26 pairs cover MC4 and
unchanged MC5, 600/60-second resolution, material pulse, weak/negative/subnormal
state, all-dry state, tiny no-history input, steady source, later source change,
and signed-zero boundary values. Seeded states are explicitly distinguished
from the unmodified pulse recession. The tests use point-mode lateral forcing;
the proof's constant-qlat condition is sufficient for both native lateral modes,
but does not substitute for the broader production regression matrix.

For the 12-day native-resolution late-pulse control, recurrence cell evaluations
fall from 1460561 to 203010. Day-12 subnormal state remains unchanged; a fixed
day executes 101 cells before copying the remainder. These counts are portable
evidence of reduced work. Small-harness elapsed times are not a production
speedup claim.

The compact repository receipt is
[mc-reference-control-summary.json](mc-reference-control-summary.json).
Independent QA also retained 26 passing lifecycle checks at
`mc-reference-lifecycle-qa-v1/receipt.json`: fresh/reset/read-only state queries,
negative/subnormal/signed-zero cases, boundary-only state, per-channel cache
isolation, valid-history/degenerate-reference selection, and MC3/MC5 exclusion.
These exercise the actual ENTRY and cache block; the cache test uses prescribed
reference inputs and does not replace the full routing controls above.

Before promotion, rerun the exact previously failing 100-year gate and required
full gates with the candidate identity explicit. Signed
loss acceptance, raw/export clipping, coefficient changes and grid transitions
remain open scientific accounting boundaries.
