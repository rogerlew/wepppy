# Role and runtime ablations, revision 1

Executed under `prompts/active/program_execplan.md`, 2026-10-31 UTC. This is a
selected development diagnostic panel, not a replacement for the 840-case gate.
Binary: revision 2 `wepp_261029`, SHA-256
`819b91721f67c4a86a5ecea14c5beb840e9a705025da2a2cedf2b97a5e067715`.
No withheld materials, default changes, acceptance changes or UI implementation.

## Erosion-only separation

All 111 prior diagnostic cases were run with fill-only, buffer-only or both-role
legacy `ki`, `kr`, and `shcrit` anchors: 333 runs. Generated horizons, 200 mm
breaks, restrictions, hydraulic properties and road parameters remained exact.
All 333 completed, passed physical checks and produced byte-identical WAT outputs
to their generated-soil baselines. Independent `verify_role_runtime.py` checks
actual soil files, all recorded input/output hashes and anchor provenance against
the frozen legacy-results SHA, not just the execution summary.

| Anchor roles | Recovered high misses /6 | Recovered low misses /41 | Recovered small exceedances /44 | Retained passing controls /20 |
| --- | ---: | ---: | ---: | ---: |
| Fill | 2 | 3 | 1 | 19 |
| Buffer | 3 | 5 | 0 | 19 |
| Both | 3 | 6 | 1 | 19 |

Even the both-role change recovers only 10/91 previous misses and loses the one
small-load passing control. In contrast, the previous whole-legacy-soil control
recovered 76/91. Reject these coefficient substitutions as a standalone candidate;
do not expand them to a full acceptance matrix. The remaining soil differences
include hydraulics, texture, organic matter and rock: this experiment does not
identify hydraulics alone as the cause. Nor does it justify uniform road erosion
reduction or applying legacy buffer hydraulic properties to generated soils.

## Runtime factorial

Nine distinct residual legacy-soil input sets and five passing controls were
crossed with seven alternate runtime configurations (98 executions); the exact
existing all-present cases supply the eighth cell. Bits below mean hourly mode,
PMET sidecar, snow sidecar, respectively. Removing PMET selects original Penman;
removing snow changes the fixture threshold from -2 C to the native default 0 C.
These are mechanism diagnostics, not regional parameter calibration.

| Configuration | Residual within criteria /9 | Residual physical passes /9 | Passing controls within criteria /5 |
| --- | ---: | ---: | ---: |
| 000 | 8 | 9 | 5 |
| 001 | 8 | 9 | 5 |
| 010 | 8 | 9 | 5 |
| 011 | 8 | 9 | 5 |
| 100 | 2 | 7 | 5 |
| 101 | 1 | 5 | 5 |
| 110 | 1 | 9 | 5 |
| 111, reused baseline | 0 | 9 | 5 |

Holding PMET and snow fixed, hourly-off recovers 8/9 residual comparisons. The
remaining Flagstaff loam gravel/high case exports 7.58652 kg/year against a
0.56037 kg/year reference (small-load bound 5.6037 kg/year). This supports a
hydrology-mode contribution to the legacy-soil residuals, without establishing
which mode is physically preferable or predicting generated-soil behavior.

92/98 new runs completed and passed physical checks. Six hourly-on, PMET-off
Denver clay runs stopped at `HOURLY_WATER_UNMET`; retain them as failures, never as
zero sediment or missing observations. Their negative demand is approximately
2.4e-12 to 9.7e-12 m with zero available water. The exact diagnostics and input
identities are in `runtime-ablation-v1-failures.json`; raw decks, stdout and
incomplete outputs are retained. These observations warrant a separate numerical
guard investigation before recommending that alternate runtime. No clipping,
tolerance relaxation or binary change was made in this study. Existing PMET-on
baseline cases passed; this is not evidence that every supported runtime passes.

## Decision and next study

Keep the generated-soil candidate and runtime defaults unchanged. The overall
acceptance result remains 719/766 meaningful cases and 30/74 small-load cases;
the diagnostic panels cannot be substituted for it. Keep the six withheld
materials closed and the UI specification/layout human gate intact.

The next bounded study should cross generated versus legacy soil with hourly
on/off on the same 111 cases, keeping PMET and snow present. Existing cells can
be reused after hash verification, so only 111 generated-soil hourly-off runs
are needed. Compare sediment and role-resolved runoff/infiltration changes to
measure the soil-by-runtime interaction before selecting any hydraulic changes.
This is a diagnostic contrast, not a proposal to turn hourly mode off in Roads.
Then inspect the strongest remaining paired contrasts to declare physically
supported fill compaction or buffer assumptions. Retain generated profile depth,
200 mm breaks and restriction semantics; avoid fitting buffer conductivity solely
to reproduce legacy export. Any viable candidate still needs the full development
matrix, independent validation, broader geometry/runtime coverage and an ADR.

## Reproduction and evidence

`role_runtime_ablation.py erosion --declare` and `runtime --declare` freeze cases,
input-record hashes, script/dependency hashes, binary and invariants before runs.
Execute the corresponding command without `--declare` in a fresh output root
through `wctl exec -T weppcloud /opt/venv/bin/python`. Existing roots intentionally
refuse overwrite. Source decks come from the frozen U10 matrix and
`legacy-soil-control-v2`; declarations record exact paths.

Machine summaries: `erosion-ablation-v1-summary.json` and
`runtime-ablation-v1-summary.json`. Independent verification receipt:
`role-runtime-verification-v1.json`. Raw retention:
`/wc1/runs/ro/roads-parameterization-program-20261031/role-runtime-ablation-v1.tar.gz`,
with manifest and receipt sidecars; repository receipt `role-runtime-archive-v1.json`.
The prior whole-soil control and its provenance remain in
`role-attribution-findings.md` and `role-attribution-archive-v1.json`.
