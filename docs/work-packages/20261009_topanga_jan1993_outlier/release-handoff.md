# WEPP 261010 Release Handoff

2026-10-10. Roger explicitly authorized release after the completed candidate
studies. WEPPpy now vendors wepp_261010 and wepp_261010_hill with paired v3
sidecars; the never-deployed wepp_261009 pair and sidecars are removed. No
general project default or production deployment is changed. Historical
results remain labeled with their actual build identities.

## Identity

Forest default branch: `wepp_260430_negmeltfix_comparator`.
Source commit: `7471bb5e981d14d0b8c1cdb88a16af305aed1b67`.

| Binary | SHA256 |
| --- | --- |
| wepp_261010 | 1dd1ca75cf53f9a0606cf5a598312d4e680e161df631156360d4a20dbcb6f17e |
| wepp_261010_hill | d8ea3a07a29ef1e754c5362bd7931cc3a93486d75faa32df5c5f2e821c22d698 |

Both rebuilt executables exactly match the studied candidate after stripping
debug information and GNU build identity. All runtime code/data remain in
that comparison. Hourly MIXPEAK, PASS v3 and channel-state continuation are
retained; the only additional physical change is CHRQIN sample normalization.
See [ADR-0084](../../adrs/ADR-0084-chrqin-source-normalization-release.md).

## Evidence

- [Topanga and Rattlesnake](candidate-results.md): target peak corrected,
  ordinary-event sediment and peak consequences retained explicitly.
- [Mutation and disturbed studies](hillslope-studies.md): exact hillslope
  parity versus 261009, including all mutation ledgers and standard outputs.
- [Cedar](cedar-results.md): unchanged yield, sampled volume +0.001008% versus
  260803; remaining integral-ledger discrepancies disclosed.
- Fresh release matrix: 96 simulations, 99 checks passed, all 768 outputs
  identical to the studied candidate. The canonical report and provenance
  were regenerated from these fresh results; previous publication archived.

Required Forest gates pass: 163 maintained tests, 12/12 watchlist cases,
both host smokes, artifact policy and system-runtime provenance. Post-vendor
host/container smokes pass; runner/interchange coverage is 114 passed with
one existing unavailable pass_pw0 fixture skip. Report/Usersum checks: 63 pass.
The full unrelated WEPPpy suite was not run for this handoff.

Supplementary exact-release integration regenerated 140 hillslopes and
completed all 45 years in plain, Roads additive and AgFields weighted
watershed cases. Native hillslope conversion rejected zero records. These
private-resource studies are not required release gates.

An optional additional committed-fixture watershed attempt was unavailable:
delicate_game_pw0 lacks three required topology/channel/impoundment files.
All 301 hills completed, but its watershed did not start. The failed attempt
is preserved and not counted as passing; no private gate or invented topology
was introduced. Early CLI/environment errors are likewise retained separately
from the successful final test and integration invocations.

## Operational Boundary

Select 261010 explicitly for local projects formerly pinned to 261009 and
regenerate every contributing hillslope PASS with the matching build. No
silent alias or automatic project migration is added. The existing paired
native v3 reader/compositors remain required. Remaining legacy accounting
and event-sediment limitations are not erased by the release decision.

The vendored [release log](../../binary-lifecycle.md) and Forest's
release/wepp_261010_validation.md record commands and validation scope.
The preexisting dirty Usersum generated index is not modified or staged by
this release; source-document rendering and its registered route were tested.
