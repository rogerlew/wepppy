# Incident: CHRQIN Initialized-Path Source Inflation

- `incident_id`: `20261009_topanga_chrq_normalization`
- `status`: `resolved`
- `scope`: `watershed`
- `author`: Codex; scientific adjudication by Roger Lew
- `date_utc`: `2026-10-10`
- `host_scope`: `dev`
- `contract_refs`: `none` (existing sample-normalization arithmetic)

## Summary and Baseline

2026-10-10 promotion decision: Roger explicitly authorized releasing the
validated candidate as wepp_261010 and replacing undeployed wepp_261009 in
WEPPpy. This supersedes the historical promotion hold below, not the measured
event-level findings or remaining accounting limitations. Release gates must
complete before vendoring; production deployment is not authorized here.

Release/vendoring complete as wepp_261010; see
[release validation](../../../release/wepp_261010_validation.md). The captured
regression and full-period decisive Topanga result close this normalization
defect, not every legacy numerical discrepancy. The earlier promotion hold
below is historical and superseded by Roger's explicit release decision.

Topanga GridMET, January 18, 1993: the same-input undisturbed outlet peak is
27.85154 m3/s in wepp_260803 and 707.63910 m3/s in wepp_261009, while daily
volume differs by only -0.482%. Roger judged 700 m3/s physically unacceptable
at this site. This is a confirmed unrealistic output, not an accepted rare event.

Observer-only replay reproduced 293 output files byte-for-byte. It located
approximately 796 and 185 m3/s source pulses at headwater channels before
routing. Captured H101/H234 component operands reproduce the error with
unchanged production CHRQIN/EQROOT/MIXRETURN routines.

## Mechanism

The pointwise source loop accumulates samples beginning at nt0. For nt0=1,
it subtracts qin0(1) from the denominator but later adds that sample scaled
by the resulting multiplier. A small isolated rainfall component leaves a
near-zero denominator, manufacturing a large source pulse. The error existed
in legacy code but these old-version full-volume operands took another branch.

The correct accounting excludes the time-zero endpoint only when accumulated:
if nt0=0, subtract qin0(0); then multiply the remaining sum by dtchr.

## Single Behavioral Lane

L01 changes only this normalization bookkeeping in src/chrqin.for. No change
to MIXPEAK, return support, state carry, routing timestep, input parameters,
interfaces, numerical floors, or release metadata. The initial proposal to
investigate state carry was not supported as the origin of these source pulses.

The opening scientific record and version/observer evidence are maintained in
WEPPpy at docs/work-packages/20261009_topanga_jan1993_outlier/.
The mandatory regression fixture is self-contained here:
tests/fixtures/chrqin_normalization.json. No private watershed is required by
the unit gate.

## Validation

Before the fix, six tests fail: two captured cases and four rainfall-only
support durations. After the fix, all 45 focused source/return/state checks pass.
Single-precision unit-test sum tolerance concerns arithmetic rounding, not a
new watershed acceptance threshold.

All 163 maintained tests, both host smokes and 12 watchlist cases pass.
714 freshly regenerated hillslopes and four full-record watershed runs complete.
Target peak falls 707.63910 to 12.50683 m3/s; daily volume is +0.0113% versus
260803. Full-record volume differences are negligible. However, burned
Rattlesnake year 40 May 15 peak falls 44.54780 to 20.21181 m3/s, and year 41
May 28 sediment rises 140954.78 to 621811.88 kg with unchanged hillslope inputs.

Disposition: BUG_FIXED for normalization; REQUIRES_SCIENCE_REVIEW for broader
acceptance. Hold promotion for Roger. Legacy parity does not justify incorrect
arithmetic; aggregate agreement does not establish event-level acceptability.
No second candidate or adjacent repair is introduced. The standard remains
not materially worse than wepp_260803. WEPPpy's package candidate-results.md
and artifacts/candidate/ preserve full evidence. Candidate output is peak-only;
no fresh full timestep integral-versus-ledger audit or closure claim is made.

Bare repository pytest currently collects archived experiment modules with
missing dependencies/files and duplicate module names. Retain the failed log;
do not describe that invocation as passed.

## Scope and Safety

Candidate is built outside the source worktree using /usr/bin/gfortran.
No live project inputs, release binaries or vendored files are changed.
External replays are supplementary evidence. No release, vendoring or deployment.
The candidate is not yet accepted for promotion.

Known legacy short-support and flat-branch representation limitations are not
silently repaired. This is not a comprehensive conservation or routing rewrite.
Rollback is the single CHRQIN change if validation finds an unacceptable regression.

## Evidence Index

- matrix.csv: baseline and candidate lane results
- notes.md: commands and validation chronology
- artifacts/logs/: preserved red/green and broader test outputs
- artifacts/manifest.csv and checksums.sha256: generated artifact identities
