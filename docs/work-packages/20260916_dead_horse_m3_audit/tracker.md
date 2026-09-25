# Audit tracker

Status: Complete, 2026-09-17 UTC (2026-09-16 Pacific).

## Completed work

- [x] Scope/reference and accepted attempt captured.
- [x] 69 source/artifact hashes verified; 181 protected files unchanged.
- [x] Independent terrain/support/soil checks and all 32,535 saved rows pass.
- [x] Official SBS upload byte identity and aligned classes/mask verified.
- [x] Authenticated report, three duration payloads, 318 curve points,
  five attachments and reload pass.
- [x] Comparison with Rengers et al. (2024), Figure 5c and uncertainty documented.
- [x] Findings, retained failure diagnostics, documentation validation and closeout.

## Decisions and findings

Owner requested audit of thespian-cleanness and comparison with Rengers et al.
Read-only scope is recorded in package.md, Purpose and scope. No rerun or
parameter changes. The paper's M1/fire-wide thresholds do not constitute M3
basin calibration targets. Exact Dead Horse storm timing remains uncertain.

[Findings](artifacts/findings.md) records four limitations: simulated rainfall/
missing observed pairing, 26.83 km² basin size, 45.53% missing SBS and soil
component representativeness. These are findings delivered by the audit, not
unresolved implementation tasks. Raw storm CSV access returned 403; this limits
external validation but does not prevent completing the saved-run audit.

## Evidence and retrospective

[Final checks](artifacts/closeout_checks.json) pass; [source audit](artifacts/source_audit.json)
identifies 97,075 native class-127 cells plus 25,093 outside source extent.
Missing input does not imply unburned. Hypothetical unburned completion changes
I15 P50 from 30.12 to 36.65 mm/hour and is not an approved correction.

The TIFF omits a NoData tag while carrying nonclass value 127. Explicit category
checks were necessary in the independent audit. Initial report access required
normal login; initial NaN serialization was corrected in audit code only.
No production behavior, inputs, accepted assessment or scientific parameter changed.
