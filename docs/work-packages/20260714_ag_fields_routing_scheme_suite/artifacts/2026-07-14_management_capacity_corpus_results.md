# Management Capacity and Corpus Results

## Disposition

Milestone 2B passes for the designated development project. The synchronized
hillslope management capacity is 32, the exact Concept 1 and hybrid parent
corpora complete under the released binary family, and no invalid AgFields
management source value requires ingest normalization.

The one runtime failure was a finite-input WEPP model-state fault. It was fixed
at the forest model boundary with an ablation-backed zero-disturbance branch,
not by coercing the AgFields management database.

## Capacity Decision

The management serializer structurally deduplicated and reparsed every generated
parent management before the capacity was selected.

| Bounded section | Concept 1 maximum | Hybrid maximum |
| --- | ---: | ---: |
| Yearly scenarios | 24 | 23 |
| Surface-effect scenarios | 24 | 23 |
| Operation scenarios | 21 | 21 |
| Plant scenarios | 9 | 9 |
| Initial scenarios | 5 | 4 |
| OFEs | 20 | 20 |
| Rotation years | 17 | 17 |
| Nested cut/graze cycles | 0 | 0 |

The accepted capacity is 32: the measured maximum of 24 plus eight yearly
scenario slots of headroom. Forest `mxplan`, `ntype`, and `ntype2` are all 32 in
the hillslope include family; the WEPPpy final-write guard is also 32. The
Concept 1 planner retains its independent 20-OFE limit.

Boundary controls passed:

- the historical 20-scenario case remains accepted;
- the measured 24-scenario Concept 1 maximum is accepted and completes;
- a 33-scenario management is rejected explicitly with
  `Must be between 1 and 32` and does not emit a success marker.

## Complete Corpus Results

The exact release hillslope binary executed one generated parent run for every
affected Concept 1 parent and every hybrid residual parent. Each passing result
has return code zero, a non-empty PASS file, the WEPP success marker, all 17
configured simulation years, and no tokenized NaN, infinity, invalid producer,
capacity, parse, signal, or timeout classification.

| Corpus | Parents | Management sources | Serialize/reparse | Native execution | Failures |
| --- | ---: | ---: | ---: | ---: | ---: |
| Concept 1 | 1,869 | 8,013 | 1,869/1,869 | 1,869/1,869 | 0 |
| Hybrid residual | 1,644 | 4,744 | 1,644/1,644 | 1,644/1,644 | 0 |

Durable summaries:

- [Concept 1 management inventory](2026-07-14_concept1_management_corpus_summary.json)
- [Hybrid management inventory](2026-07-14_hybrid_management_corpus_summary.json)
- [Concept 1 execution summary](2026-07-14_concept1_parent_execution_summary.json)
- [Hybrid execution summary](2026-07-14_hybrid_parent_execution_summary.json)

The exact-release execution-summary hashes are
`f3342d285ba594e96b07be35a9aa0357489c9b6d0b45059c9a57f2769dd4f935`
for Concept 1 and
`adf44880bba2b03fccc64bf95e5c639347c7c049052a47efada309b27ce3ccda`
for hybrid. The corresponding complete Parquet ledger hashes are
`b88be58f6d35c4179736ee792a829e552b1a10d19ade1fde4c650db7ac8f6c29`
and
`6c794677e7f85a1da113e6f3708903e81e2dc5e208d7ff7700a9a02fed96b2d3`.
Candidate-to-release PASS comparison found zero hash mismatches across both
corpora.

## Numerical Fault and Patch Boundary

Concept 1 parent 1857 exposed a `SIGFPE` in `frcfac.for`. OFE 10, sourced from
sub-field 4023, uses operation `000_HERB` with `surdis=0` and nominal `rro=0`.
The existing soil update correctly gives nominal roughness zero weight and
retains initialized roughness, but `frcfac` later divided by the raw zero
nominal value.

The forest G1 branch uses initialized roughness only when `surdis=0`. Positive-
disturbance operations continue to use their declared roughness so invalid
producer values are not hidden. The incident, observation lanes, control,
permanent watchlist, and release evidence are under
`/workdir/wepp-forest_260430_baseline/docs/ablation/20260714_sacral-self-discipline_p1857_hillslope_sigfpe-frcfac/`.

## Release and Regression Evidence

The uniquely named release artifacts are `wepp_260714` and
`wepp_260714_hill`. They were built with `/usr/bin/gfortran` and
`-mcmodel=medium -no-pie` and request
`/lib64/ld-linux-x86-64.so.2`.

`wepppy/nodb/configs/ag-fields.cfg` selects `wepp_260714` for new AgFields
projects. Existing persisted projects require an explicit AgFields binary
selection before Concept 1 or hybrid execution; baseline WEPP state and outputs
are not rewritten by that selection.

| Binary | SHA-256 |
| --- | --- |
| Watershed | `a7e1a5152fe9097c08685eee98853ffd6ab8fe52cb835e239a972d12f6ee6e36` |
| Hillslope | `cf70d059116b8f1d68d850761e1a12c0a1eca4f1467488ce377e27065bddc76d` |

Completed gates:

- p1857 decisive replay and p94 control: 17/17 years;
- permanent hillslope watchlist: 13/13;
- forest test suite: 83 passed, 2 warnings;
- legacy `delicate_game_pw0` watershed replay: 301/301 hillslopes;
- forest ablation artifact policy: pass;
- vendored-binary provenance and p94 host smoke for both binaries: pass; and
- WEPPpy runner/output regressions: 8 passed, 2 warnings.

The forest worktree began detached at `dac3c950` and dirty. The isolated build
source deliberately includes the preexisting, uncommitted p1 soil-layer cursor
patch recorded by the forest 2026-06-25 incident and changelog entry. The
AgFields capacity/G1 source delta and its `260714` binaries remain separately
named; unrelated dirty `260430` source/release artifacts were not overwritten.

## Remaining Gate

This result clears the management-capacity/corpus gate for implementation. It
does not by itself accept ADR-0019 or expose Concept 1/hybrid to users. The
scheme-aware NoDb, hybrid composition, RQ/API, UI, protected-tree, and generated
three-scheme validation milestones remain required.
