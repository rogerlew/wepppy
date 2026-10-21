# Audit tracker

## Status

Complete as diagnostic audit, 2026-10-21. Four native defects remain unresolved;
watershed correctness is not certified. Ash excluded by operator instruction.

## Progress

- M1: exact 261021 source/binary identities, geometry, input/output manifests retained.
- M2: eighteen full 44-year watershed configurations complete; three additional
  hillslope initial-groundwater variants complete.
- M3: ten OFE/mode cases pass transfer/PASS precision checks; independent native
  rates expose channel volume discrepancies. Hourly probes identify infiltration
  remainder; groundwater test isolates terminal-area initialization.
- M4: five corruption controls pass. Actual CHRQIN harness runs ten controls/
  observed-case probes and reproduces flat-branch deficits. Findings and
  reproduction scripts retained. Observations preserve scientific outputs.

## Findings

WPA-01: channel-local net volume can be absent from lateral rate construction.
WPA-02: flat CHRQIN branch drops partial intervals and under-delivers when
requested volume exceeds peak × duration.
WPA-03: hourly infiltration discards the distribution-loop remainder.
WPA-04: nonzero initial groundwater uses the terminal OFE area.

Exact numbers, source paths, evidence receipts, proposed repair targets and
limitations are in [findings](artifacts/findings.md). No native production source
or vendored binary changed. Original donor/project outputs remain unchanged.

## Decisions and validation

2026-10-21: Execute a successor physical audit; preserve completed consumer and
calendar work as history. Do not infer current ASCII QOFE semantics from HBP
branch aliases. Unknown stores remain unknown; a published zero balance is
not independent conservation evidence.

Comprehensive baseline/off/on byte parity passes for ten watershed configurations;
H1 output parity passes for three hourly probe layouts. Native harness positive
control passes and four defect cases reproduce on both initialization paths.
Transfer tolerances derive from actual writer formats and native precision.
Development-tool failures and corrections remain documented in commands.md.

No deployment, release, historical attribution or universal physical closure is
claimed. Repair and post-repair replay are separate work. Contour/variable-width,
positive tile flow, impoundments and independent calibration remain untested.

Final handoff checks: six package Markdown files and PROJECT_TRACKER lint with
zero warnings/errors; audit scripts compile; root size and whitespace checks
pass. Frozen release hashes remain unchanged and the native release checkout
is clean. All receipt parity assertions pass.
