# Schema-2 calendar selection validation

## Change and authority

Roger authorized correcting schema-2 delivery on 2026-10-21. The reader now
accepts paired requested year/day arguments, finds the matching ordered directory
key, verifies its calendar year, and loads the entire record. The production
`wshred` → `hbp_mode2_read_day` path supplies current `year,sdate`. Invalid or
partial requests fail without advancing the cursor; undated inspection remains
sequential. Production dated lookup assumes consecutive simulation years from
`begin_year`, as produced by the native writer.

No writer bytes, schema, event filtering, hydrologic equations, COMMON layout or
calendar policy changed. In particular, legacy centurial day 366 remains supported.
`wepp_261010` uses ASCII PASS components version 3; its separate century issue
has not been investigated or corrected here. No release, vendoring or deployment.

## Generated-output acceptance

The single-OFE and 60/40 cases complete all 44 years. Every requested day passes
independent date-keyed surface/lateral/tile/baseflow/seepage volume readback,
including the final configured day. Candidate observations off/on are byte-exact
across all ordinary files, and every `output/H*` hillslope product is unchanged
from the pre-fix build, including HBP, WAT, EBE, loss and sediment artifacts.
The real 28-hillslope project also completes all 43 years, 1983–2025. All
requested dates through 2025-365 pass, candidate off/on matches across 388 files,
and all 196 hillslope products remain byte-identical to baseline. The real
channel ledger covers configured outlet element 39 (15,706 days), not every
internal channel. All three case ledgers fit the publication-arithmetic screen.

For 60/40 on 1982-01-01, loaded lateral volume changes from 0 to 45.785182953 m3.
For the single-OFE case it changes from 0 to 40.665725708 m3. `ebe_pw0.txt` first
differs on that same day (simulation year 3); all preceding lines are identical.
The rounded outlet runoff changes from 2.12 to 45.34 m3 for 60/40 and from 1.96
to 40.22 m3 for one OFE. These are expected downstream routing changes, not an
assertion that hillslope delivery equals outlet discharge instantaneously.
See `first-divergence.json` and per-case `*-validation.json`.

Channel ledgers remain publication-arithmetic checks only. Some published terms
are derived from balance identities; these checks cannot establish full physical
watershed conservation. Correcting dates also changes which groundwater and
sediment records route on each day. No historical outputs were regenerated.

## Regression and review gates

The new direct-reader regression fails against the pre-fix behavior (13 checks)
and passes after correction. It covers generated schema1/schema2 multiyear
records, ordinary/leap boundaries, final-day delivery, exact volume/sediment
signatures, invalid/partial dates, cursor recovery, and dated access after EOF.
A generated 1899–1901 case also verifies the existing legacy 1900-366 behavior.
This is a compatibility test, not Jackson's century-issue investigation.

Both native make targets build and pass the canonical host smoke over all 44
years of the retained single-hillslope input. Fortitude passes all three changed
free-form files; scoped diff checks pass. Mandatory primary correctness review
and subsequent source QA report no implementation blockers. Final runtime correctness review passes with the real-project receipt. The
reader suite also passes in a fresh isolated FPM build, avoiding shared-cache
ambiguity.

## Broad-suite limitations

Native pytest: **193 passed, 1 failed**. The failure requires the unavailable
external input `/wc1/runs/ca/carved-letter/wepp/runs/p136.run`; no touched file
supplies or changes that fixture. The historical binary regression also passes.

Full FPM runs report two failures from the shared build cache: WBK08 storage
reconciliation segfaults, and the hourly adapter reports nine assertions. Fresh
isolated builds using pre-fix and corrected reader sources establish the same
baseline dispositions: WBK08 cannot compile because its test still passes a
scalar where `wb_geometry_context` is required; the hourly adapter passes in
both clean builds. Only the HBP reader differs between those library source
sets (`fpm-source-delta.json`). The shared cached failures are not used as proof
of reader correctness, and the full FPM suite is not claimed green. These
unrelated test/cache issues are retained for separate maintenance.

## Reproduction and retained evidence

Work root: `/workdir/hbp-schema2-calendar-selection-20261021`. Source/binary hashes,
initial dirty-state snapshots, patch and logs are in `provenance.json`.
`reader-fix.patch` isolates this correction from prior observation probes.
The isolated binaries are `candidate-source/src/wepp` and `wepp_hill`; local
sidecars identify the actual hashes and are explicitly not released. Inherited
stale sidecars are retained as `.json.inherited` and are not identity authority.

From `/workdir/wepp-forest`:

    fpm test --target ps05_mode2_direct_reader
    fpm test
    python -m pytest -q
    fortitude check fpm-src/hillslope_binary_pass_reader.f90 src/hbp_mode2_bridge.f90 fpm-test/ps05_mode2_direct_reader_tests.f90

In isolated `candidate-source/src/`:

    make FC=/usr/bin/gfortran LDFLAGS='-mcmodel=medium -no-pie -lz' wepp wepp_hill

Host smoke runs use `RUNS_DIR=/workdir/hbp-schema2-calendar-selection-20261021/off/single/runs`
and native `tools/smoke_wepp_binary_host.sh` for each binary. No shared fixture or
live project is modified. Baseline/candidate isolated FPM failure logs retain the
minimal target manifests and build diagnostics; early setup failures are retained
separately. A generalized test fixture initially had a hard-coded year index;
`regression-test-fixture-error.log` preserves that corrected test-only mistake.

From `/workdir/wepppy`, with `PYTHONPATH=/workdir/wepppy` and
`/workdir/wepppy/.venv/bin/python`, run the scripts in this artifact directory:

    python replay_fix.py --case single --mode off
    python replay_fix.py --case single --mode on
    python audit_fix.py single

Repeat for `upper60` and `real`. Preparation refuses existing destinations; use
new attempt roots when reproducing. `replay_fix.py` uses retained controlled
inputs and the supported real-project fork from the closed investigation.
`audit_fix.py` reuses its independent HBP parser/observation joins but deliberately
omits obsolete sequential-consumption tail counters for the corrected reader.
`retain_provenance.py` refreshes exact patch, source, binary and log receipts.

Package docs use `wctl doc-lint`; native docs use `markdown-doc lint` from their
own repository. No broad WEPPpy Python/frontend suite is needed: no WEPPpy
production code changed. Release promotion requires separate release gates.
