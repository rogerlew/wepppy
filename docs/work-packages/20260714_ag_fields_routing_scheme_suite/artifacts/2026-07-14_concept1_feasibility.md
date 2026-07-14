# Concept 1 and Hybrid Feasibility Evidence

**Date**: 2026-07-14

**Project**: `/wc1/runs/sa/sacral-self-discipline`

**Planner**: `ag_fields_concept1_constrained_runs_v1`

**Outcome**: Geometry and mixed-source accounting are feasible, but the current
WEPP management limit blocks a faithful full-project implementation.

## Decision Summary

The one-dimensional planner represented every retained source on the development
project with 1-20 OFEs, positive source overlap, and exact raster-area closure.
The explicit-breakpoint slope and residual-width construction also produced a
parseable, runnable mixed hybrid parent whose source area, water, and sediment
balances closed exactly.

The package nevertheless stops before UI, API, RQ, and scheme-root wiring. After
reference-safe structural management deduplication, 141 of 1,869 Concept 1 parents
and 59 of 1,644 hybrid residual parents still require more than the native WEPP
limit of 20 referenced yearly scenarios. Those failures cover 12.21% of affected
Concept 1 area and 5.47% of hybrid residual-parent area. Silently dropping fields,
merging unlike rotations, or substituting Concept 2 would violate the requested
routing contracts.

ADR-0019 therefore remains Proposed. Continuing requires either a separate,
explicitly tested WEPP binary-limit expansion or a decision-owner revision to the
routing fidelity contract.

## Frozen Inputs

| Resource | SHA-256 |
| --- | --- |
| Parent `SUBWTA` raster | `43554eb57f941c85019be303e576218993d50b194094224b1e55ccad336e0d43` |
| Parent `DISCHA` raster | `d3e0a99bbc1e45f50b6f073228cdfe443758eaf49bc4bcc2c8d49d08f3f0734e` |
| Retained sub-field raster | `e183d707d02ee1d4c84e4372d5d1883f8df9dc6bf2b01093e322b26dd0887b77` |
| `fields.parquet` | `7adc2df6b1fa36537c784507e62a2b85ed38ddc51842712d9611cbc32e9d8c99` |
| Peridot connectivity detail | `f8856408adddb7ee0182543fe963ec53cc7eb23e3a4a1a874af0c6e453f011f1` |
| Ordered manifest of 3,543 parent slope files | `14444a6d655551552e10696274ac301a353a34a264a2851b8d4cdbda0ea5b210` |
| Ordered manifest of 3,544 parent management files | `a56f83f23d76afcb4aba7cd563691ea4414c0a8ded4fc26451cf1b6e12aaa4d3` |
| Ordered manifest of 6,626 sub-field management files | `e0da927ffb1135a6901af15b6005b3514fdd75cf22b4460bbbd90612c6ae9e58` |

Each ordered-manifest digest hashes the sorted `sha256sum` records, including
their absolute project paths.

The persistent connectivity detail is
`wepp/ag_fields/watershed/hybrid/manifest/connectivity_detail.json` within the
development project. It contains 6,626 sorted sub-field rows: 3,269 connected,
3,357 not connected, and 12,365 direct channel outlet cells.

The final census normalizes the sub-field raster's finite GDAL NoData sentinel
`-2147483648` to background source `0`. Earlier exploratory census versions that
treated the sentinel as a source were discarded; all values below are from the
corrected run.

## Planner Contract

The read-only planner uses stable descending `DISCHA` order and compares:

- one-to-four equal bands;
- generalized contiguous source runs, merged without removing a represented
  source; and
- a source-order partition that represents every source once when needed.

The current engineering hard gates are 1-20 OFEs, every actual source represented,
positive overlap for every represented field, contiguous normalized breakpoints,
and exact raster-cell area closure. Assignment agreement, field-area error,
fragmentation, ordering conflicts, and downstream-background error remain
diagnostics for Mariana's science evaluation; this study does not turn them into
hidden acceptance thresholds.

The planner census can be regenerated from repository root with these read-only
commands; the output directories are intentionally outside git:

```sh
python3 -m wepppy.nodb.mods.ag_fields.concept1_planner \
  --subwta /wc1/runs/sa/sacral-self-discipline/dem/wbt/subwta.tif \
  --discha /wc1/runs/sa/sacral-self-discipline/dem/wbt/discha.tif \
  --sub-field-map /wc1/runs/sa/sacral-self-discipline/ag_fields/sub_fields/sub_field_id_map.tif \
  --fields-parquet /wc1/runs/sa/sacral-self-discipline/ag_fields/sub_fields/fields.parquet \
  --slope-dir /wc1/runs/sa/sacral-self-discipline/watershed/slope_files/hillslopes \
  --output-dir /tmp/agfields-concept1-census-v8

python3 -m wepppy.nodb.mods.ag_fields.concept1_planner \
  --subwta /wc1/runs/sa/sacral-self-discipline/dem/wbt/subwta.tif \
  --discha /wc1/runs/sa/sacral-self-discipline/dem/wbt/discha.tif \
  --sub-field-map /wc1/runs/sa/sacral-self-discipline/ag_fields/sub_fields/sub_field_id_map.tif \
  --fields-parquet /wc1/runs/sa/sacral-self-discipline/ag_fields/sub_fields/fields.parquet \
  --slope-dir /wc1/runs/sa/sacral-self-discipline/watershed/slope_files/hillslopes \
  --connectivity-detail /wc1/runs/sa/sacral-self-discipline/wepp/ag_fields/watershed/hybrid/manifest/connectivity_detail.json \
  --output-dir /tmp/agfields-hybrid-census-v8
```

### Development-project census

| Metric | Concept 1 | Hybrid residual Concept 1 |
| --- | ---: | ---: |
| Affected/residual parents | 1,869 | 1,644 |
| Retained fields represented | 6,626 | 3,357 non-connected |
| Candidate rows | 27,679 | 19,211 |
| Selected OFE rows | 26,082 | 15,767 |
| OFEs, mean / median / max | 13.955 / 19 / 20 | 9.591 / 7 / 20 |
| Overall agreement, mean / median / min | 0.9081 / 0.9817 / 0.1865 | 0.9612 / 1.0000 / 0.4927 |
| Field agreement, mean / median / min | 0.8809 / 0.9773 / 0.1839 | 0.9351 / 1.0000 / 0.2185 |
| Maximum field-area error, mean / median / max | 0.3410 / 0.0714 / 18.5000 | 0.5149 / 0.2000 / 23.7837 |
| Source-order conflicts, mean / max | 6.970 / 18 | diagnostic captured |
| Fragmented fields, mean / max | 2.932 / 17 | diagnostic captured |
| Downstream-background error, mean / max | 0.0089 / 0.4298 | diagnostic captured |
| Missing fields / zero-overlap fields | 0 / 0 | 0 / 0 |
| Maximum source-area closure residual | 0 m2 | 0 m2 |
| Runtime / peak RSS | 54.35 s / 495,236 KiB | 19.59 s / 469,832 KiB |

Concept 1 selected 1,719 generalized, 141 equal-band, and 9 source-order plans.
Hybrid selected 1,182 generalized, 461 equal-band, and 1 source-order residual
plans. Hybrid parent composition comprised 270 pure Concept 1 parents, 1,374 mixed
parents, and 225 pure Concept 2 parents.

The broad agreement ranges confirm why these metrics must remain visible science
diagnostics. They do not invalidate the geometry/accounting contract by
themselves, and no undocumented fit cutoff was applied.

## Native Management Feasibility

`ManagementMultipleOfeSynth` was exercised against the actual parent and sub-field
management graphs with opt-in structural deduplication. Equivalent plants,
operations, contours, drains, initial conditions, surfaces, and yearly scenarios
are reused while unlike rotations remain distinct. The legacy default remains
unchanged.

| Metric | Concept 1 | Hybrid residual Concept 1 |
| --- | ---: | ---: |
| Parents requiring generated management | 1,869 | 1,644 |
| Eligible at `nmscen <= 20` | 1,728 (92.46%) | 1,585 (96.41%) |
| Ineligible at `nmscen > 20` | 141 (7.54%) | 59 (3.59%) |
| Candidate parent area | 176,981,400 m2 | 169,544,700 m2 |
| Eligible parent area | 155,374,200 m2 (87.79%) | 160,271,100 m2 (94.53%) |
| Ineligible parent area | 21,607,200 m2 (12.21%) | 9,273,600 m2 (5.47%) |

Concept 1 overflow counts were 102 parents at 21 scenarios, 29 at 22, 7 at 23,
and 3 at 24. Hybrid overflow counts were 43 at 21, 15 at 22, and 1 at 23. The
exact four-worker preflights took 688.08 seconds for Concept 1 and 354.6 seconds
for the hybrid counting pass.

This is a binary input-contract limit, not a planner heuristic. The completed
`20260422_mofe_nscen_cull_execplan.md` intentionally fails fast above 20 and
deferred changes to `pntype.inc`, `pmxpln.inc`, `infile.for`, and `readin.for` to a
separate binary work package because those fixed-array/common-block limits affect
more than management yearly scenarios.

## Mixed Hybrid Execution Proof

Parent Topaz 442 / WEPP 102 is a real mixed parent:

- non-connected sub-field 864 occupies 3,600 m2 of residual area;
- connected sub-field 818 contributes an independent 1,800 m2 PASS source;
- the parent target area is 5,400 m2;
- the residual keeps the 90 m parent profile length, uses a 40 m target width,
  and has two OFEs at normalized breakpoints `0`, `1/3`, and `1`;
- the residual management reparses with two OFEs and 19 referenced yearly
  scenarios; and
- the native `wepp_dcc52a6_hill` run succeeds.

The residual PASS header area is 3,600 m2, the connected PASS header area is
1,800 m2, and the combined header area is 5,400 m2. Across 6,210 event rows and
the complete run, the ADR-0018 `ag_fields_v1` combiner produced exactly zero
water-volume and sediment-mass residual. The disposable fixture is retained at
`/tmp/agfields-hybrid-p102-fixture-v2` for local inspection only.

The proof also exposed an existing synthesis defect: a generated description
comment before the WEPP version token caused native `verchk` failure. Generated
comments now follow the first three native header records, and a regression test
preserves `98.4` as the first line.

## Implemented and Verified Substrate

- Peridot commit `495abd5` adds deterministic per-sub-field detail output while
  preserving the aggregate CLI/API contract.
- wepppyo3 commits `9c84643` and `1dfcf35` add, test, and release explicit
  breakpoint segmentation. The Python 3.12 release artifact SHA-256 is
  `776703694245aa092f6f1972cbd539dddb2ca0f4c054afa04d7e25f863a745f6`.
- WEPPpy contains the read-only planner, explicit-breakpoint wrapper, input
  synthesis spike, opt-in management graph deduplication, and focused regression
  coverage. These components are not connected to user-facing orchestration.

Focused evidence collected during the spike:

```text
Peridot debug tests: 46 passed (2 preexisting unused-import warnings)
wepppyo3 Rust tests: 43 passed
wepppyo3 release Python tests: 9 passed
Concept 1 planner tests: 9 passed
WEPPpy slope wrapper tests: 15 passed
Concept 1 input validation tests: 3 passed
Management synthesis tests: 6 passed
Mixed parent native WEPP run: passed
```

## Stop and Next Decision

The suite cannot meet its faithful all-parent acceptance contract with the
currently supported WEPP binary. The following shortcuts were considered and
rejected because each changes the requested behavior:

- omit scenario-limited parents or fields;
- merge nonequivalent rotations to force `nmscen <= 20`;
- silently substitute Concept 2 for rejected Concept 1/hybrid parents; or
- publish planner-only schemes in the UI.

The next authorized step should be one of:

1. scaffold and execute a separate WEPP binary-limit augmentation package with
   parser/common-block audit, existing-output parity, synthetic `nmscen > 20`
   coverage, performance evidence, and synchronized binary provenance; or
2. revise ADR-0019's fidelity/coverage contract explicitly, including how the
   141 Concept 1 and 59 hybrid failures are presented and evaluated.

Until one decision is accepted, Concept 2 remains the implemented compatibility
path and this package remains blocked before Milestones 3-7 production wiring.
