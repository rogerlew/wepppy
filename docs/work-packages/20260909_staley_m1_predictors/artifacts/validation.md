# Local M1 validation evidence

2026-09-09. Local implementation, required checks and complete authentic-source
acceptance passed. The rebuilt Wallow assessment closes the package.

## Commands and results

- `wctl run-pytest tests/nodb/mods/test_postfire_debris_flow_integration.py --maxfail=1`:
  50 passed, 23.85 seconds. Log: `/tmp/m1-focused-final.log` on the host.
- Independent correctness: 9 boundary regressions and 4 K provenance cases
  passed. All four findings closed in [review](correctness_review.md).
- Independent security: 13 boundary regressions, final 4 mask/worldfile cases
  and direct GDAL probes passed. Both findings closed in [review](security_review.md).
- `wctl check-test-stubs`: passed; `/tmp/m1-test-stubs.log`.
- `wctl run-stubtest wepppy.nodb.mods.postfire_debris_flow.integration`: passed, one module;
  `/tmp/m1-stubtest-final.log`.
- `wctl run-pytest tests --maxfail=1`: 8,016 passed, 72 skipped, 3,106 warnings
  in 820.09 seconds; `/tmp/m1-full-suite.log`. The additional external-mask flag
  regression was added after full-suite collection and passed in the final
  50-case focused suite and independent security rerun.
- Scoped package/module/ADR documentation lint: passed; `git diff --check`: passed.
- Broad-exception enforcement: passed, two new production files scanned,
  zero broad catches. New files temporarily marked intent-to-add for tracked-file
  tooling; no content commit. Observe-only quality telemetry recorded in
  `/tmp/m1-code-quality.json`; its three-dot HEAD comparison does not include
  uncommitted file deltas, and host radon is unavailable. No changed-file
  complexity claim is made from that report.

## Reproduction and generated products

From repository root, with a fresh output directory and the existing dev mounts:

    wctl exec weppcloud python docs/work-packages/20260909_staley_m1_predictors/artifacts/reproduce.py /workdir/wepppy/docs/work-packages/20260909_staley_m1_predictors/artifacts/generated/final

The recorded destination exists; repeat with a fresh child such as `generated/repeat-1`.
[Retained initial result summary](generated_evidence.json) retains exact paths, values,
source and tool identities. Large generated TIFFs remain ignored and inspectable
under `artifacts/generated/final/`, including `synthetic-complete`,
`real-missing-dnbr` and `controlled-tool-failure`. The initial summary's missing-dNBR
limitation describes that earlier inventory; the rebuilt Wallow evidence below
supersedes it for package acceptance.

Executable: `/workdir/weppcloud-wbt/target/release/whitebox_tools`.
SHA-256: `6647d55c2d8d28680addd16adc4d9d406857a7ccb394cd4260a2d61d7d8ffc42`.
This matches the predecessor's analytical/security/terrain validation records,
not an assumed installed version. WBT source revision:
`a97abb7754a24390edf1d93f3f26a09d80b4669b` (clean checkout).
Container identity: UID 1000, GID 993, groups [993], default umask 0022.
The actual workflow used the existing `/workdir` and `/wc1` mounts; private bundle
creation uses 0700. This is local dev identity evidence, not production shipping.

Synthetic analytical field: T=1, F=0.4000000059604645 (Float32 normalized source),
S=0.3, 25 full-domain cells. Explicit accumulation scenarios 10/20/30 mm over
15/30/60 minutes produce probabilities 0.9947798745, 0.9995518794 and 0.9981113453.
These are labeled synthetic examples, not frequency estimates.

Authentic `strained-mod`: 80,949 domain cells, T=0.41419906360795067,
S=0.338206766138312, F=null (`missing_input`). All scenario probabilities remain
null. Both example domains carry the accepted study-area warning. K mode,
weights, original gap-fill summary and fragment provenance are retained.

Native project DEMs include statistics-only PAM `.aux.xml`. The reproduction
script checks that XML contains only statistics metadata, copies raw TIFF bytes
outside the project, and verifies original/copy samples, masks and grids before
calling the strict adapter. Original files and PAM hashes are checked again after
work. This explicit evidence preparation does not broaden runtime sidecar admission.

The controlled failure uses a separately labeled executable exiting 7; it leaves
logs and `incomplete.json` without `manifest.json`. It does not modify the pinned
WBT executable or any existing bundle.

## Scientific acceptance limit

The original Arizona fixtures do not overlap the initial candidate projects.
The owner subsequently supplied the Wallow archive and project below. The rebuilt Wallow assessment below resolves both authentic
dNBR availability and complete real T/F/S acceptance. No upstream rebuild or production publication
was performed.

## Wallow follow-up (historical July 1 assessment)

Owner-selected source and fixture contract: [Wallow fixture README](../../../../tests/nodb/mods/fixtures/postfire_debris_flow_wallow/README.md).
Three lossless June 23 products retain original samples, masks, grids and source
metadata. Importer parity checks passed; fixture and SBS reader tests: **10 passed**.

The owner identified `woolen-refusal` on forest. Its uploaded July 1 BARC256 is
byte-identical to the archive's original July 1 member. Use the matching July 1
dNBR with May 30 prefire imagery and scale 0.001; do not silently substitute the
June 23 final-severity assessment. This preserves the current project comparison.

[Reproduction](reproduce_wallow.py) writes only to a fresh local output directory;
[retained evidence](wallow_evidence.json) records source hashes, archive identity,
12 nonempty soil files, execution identity, normalization and actual WBT results.
All original source hashes were unchanged after execution. Command:

    wctl exec weppcloud python docs/work-packages/20260909_staley_m1_predictors/artifacts/reproduce_wallow.py /workdir/wepppy/docs/work-packages/20260909_staley_m1_predictors/artifacts/generated/wallow-final

Basin: 12,973 cells, 11.6757 km² (area applicability warning retained).
F=0.6589354043877701 and S=0.43397823632668575 have full support.
All slopes are valid; SBS covers 10,627 cells. Intersection counts are 2,438 true,
10,386 false and 149 unknown. T stays null with bounds
[0.1879287751483851, 0.19941416788715025]; all three scenario probabilities stay null.
Processing completed successfully with partial predictor availability. No filling,
source repair or watershed shrinking was used to manufacture a complete result.

## Rebuilt Wallow final assessment

The owner uploaded the final polygon TIFF and rebuilt landuse, WEPP and gridded
RUSLE. Revalidation consumes the rebuilt artifacts read-only and explicitly
selects the matching June 23 assessment; the prior July 1 result above is retained
as historical incomplete-state evidence. No project artifact was changed by
validation. The fixture provenance pins the uploaded TIFF to the archive's final
polygon components; every valid source code 1–4 maps exactly to prepared SBS 0–3,
with identical grid and masks. The June 23 continuous dNBR uses May 30 prefire
imagery and scale 0.001.

    wctl exec weppcloud python docs/work-packages/20260909_staley_m1_predictors/artifacts/reproduce_wallow.py /workdir/wepppy/docs/work-packages/20260909_staley_m1_predictors/artifacts/generated/wallow-rebuilt-final --assessment final-june23

[Retained rebuilt evidence](wallow_rebuilt_evidence.json) records the fresh source
hashes, original-source rechecks, execution identity and actual WBT outputs.
All 12,973 basin cells have slope, SBS, dNBR and K support. T=2458/12973
=0.1894704386032529, F=0.6141950971236625, S=0.43397823632668575.
Unknown intersections: zero. The 15-minute/10 mm, 30-minute/20 mm and
60-minute/30 mm example scenarios yield probabilities 0.9866102237667208,
0.998507412524049 and 0.9866885015218513 respectively. These are explicit test
storms, not observed events or frequency estimates. The 11.6757 km² watershed
retains `area_outside_study_range` on every scenario.

This closes the local authentic complete-source gate. Earlier full-suite and
focused runtime validation remain applicable: this follow-up changes only the
reproduction script, fixtures and evidence/docs, with no runtime changes.
Climate, production publication and automatic source freshness remain successor
scope. Correctness and security reviews independently verify the rebuilt evidence.
