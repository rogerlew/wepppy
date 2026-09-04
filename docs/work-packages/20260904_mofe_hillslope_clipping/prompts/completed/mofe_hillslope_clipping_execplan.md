# Implement and Validate Per-OFE Hillslope Clipping

This ExecPlan is a living document maintained according to
`docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, enabling WEPP hillslope clipping has the same useful meaning
for single- and multiple-OFE hillslopes: no individual OFE exceeds the selected
length, while the representative area of each complete hillslope is preserved.
Users can see the per-OFE meaning in advanced options and verify it directly in
generated `wepp/runs/p*.slp` files.

## Progress

- [x] (2026-09-04 11:31 UTC) Scaffold package, contract decision, canonical
  contract, ADR, tracker, and ExecPlan.
- [x] (2026-09-04 12:02 UTC) Obtain and disposition two independent contract
  reviews plus the security checkpoint review; all high/medium findings closed.
- [x] (2026-09-04 12:04 UTC) Commit the standalone checkpoint ancestor as
  `8434ecb88`.
- [x] (2026-09-04 12:31 UTC) Implement the slope transform and multi-OFE
  preparation wiring with tests.
- [x] (2026-09-04 12:31 UTC) Update UI, user, operator, and developer
  documentation.
- [x] (2026-09-04 13:31 UTC) Run focused and broad validation and close all
  correctness/security findings; full suite passed with 7,348 passed and 63
  skipped.
- [x] (2026-09-04 12:34 UTC) Deploy candidate `f2dc23498` to `forest`, execute
  rq-engine root `f5121308-9c63-4e46-8bae-c41083d53199` at 60 m, and pass
  all-file generated-output acceptance.
- [x] (2026-09-04 12:34 UTC) Close package, archive this prompt, and update the
  project tracker.

## Surprises & Discoveries

- Observation: `Watershed.clip_hillslopes` currently returns false whenever
  `multi_ofe` is true, and `prep_multi_ofe_hillslope` copies `.mofe.slp`
  directly.
  Evidence: `wepppy/nodb/core/watershed.py` property implementation and
  `wepppy/nodb/core/wepp.py` multi-OFE prep helper.
- Observation: the synchronized `dainty-signature` run already contains OFEs
  shorter than 300 m, but the requested 60 m acceptance value will exercise
  clipping because its longest OFE is greater than 60 m.
- Observation: generated normalized endpoint distances may round to `0.9999`.
  Complete validation therefore uses a `1e-3` absolute endpoint tolerance while
  still requiring bounded, strictly increasing distances.
  Evidence: the local `hill_132.mofe.slp` and all-source dry-run acceptance.
- Observation: atomic replacement through `NamedTemporaryFile` defaults to mode
  `0600`; explicitly copying the source mode preserves the established generated
  artifact permissions.
  Evidence: implementation security review and direct mode regression.

## Decision Log

- Decision: interpret the threshold per OFE and preserve complete-hillslope area
  through one shared-width scale factor.
  Rationale: this matches explicit operator intent and the existing UI area
  promise within the slope-file format.
  Date/Author: 2026-09-04, Roger Lew and Codex.
- Decision: classify this as an intended parameterization change requiring a
  standalone contract checkpoint and ADR.
  Rationale: multiple-OFE generated model geometry intentionally changes.
  Date/Author: 2026-09-04, Codex.
- Decision: reject malformed headers, trailing records, non-finite computed
  geometry, and invalid normalized profiles before temporary output creation.
  Rationale: the preparation boundary must fail closed without replacing a
  prior valid generated slope.
  Date/Author: 2026-09-04, Codex.

## Outcomes & Retrospective

The feature is implemented and deployed on Forest. The 15-job rq-engine tree
finished successfully. Across 167 generated hillslope slope files, 83 changed,
all 220 source OFEs longer than 60 m were capped, the generated maximum was
60 m, structure and permissions were preserved, and maximum relative area
error was `2.19e-16`. Complete parse-before-publish validation and a real RQ
failure test were valuable review-driven hardening additions.

No source OFE in this run exceeded 300 m; the maximum was 101.56 m.

The first public rq-engine health probe immediately after recreation returned
502 while Uvicorn was still starting. A subsequent local and public probe
returned `{"status":"ok","scope":"rq-engine"}` before submission; no rollback
was required.

## Context and Orientation

`wepppy/topo/watershed_abstraction/slope_file.py` owns slope-file transforms.
`wepppy/nodb/core/wepp.py` prepares one generated `wepp/runs/p<ID>.slp` per
hillslope. A multiple-OFE slope file has one shared width and repeated pairs of
an OFE definition line (`point_count length`) and a normalized slope-profile
line. `wepppy/nodb/core/wepp_prep_service.py` selects single- or multiple-OFE
preparation. The advanced UI lives in
`wepppy/weppcloud/templates/controls/wepp_pure_advanced_options/clip_hillslopes.htm`.

The local acceptance run is `/wc1/runs/da/dainty-signature` with config token
`canada-wbt-mofe`. This checkout is already on exact host `forest`; `hostname`
must confirm that identity. Forest serves the development Compose stack from
`docker/docker-compose.dev.yml` through the installed `wctl` preset. Source is
bind-mounted, so deployment recreates only the Python services that execute this
change without an image build: `weppcloud`, `rq-engine`, `rq-worker`, and
`rq-worker-batch`. Forest1 and production are excluded.

## Plan of Work

First complete the contract checkpoint and commit it without implementation
files. Then generalize the clipping utility to parse every OFE definition,
validate the enabled limit, cap each length, and compute an area-preserving
shared width. Keep the output structure and optional header fields unchanged.

Pass the clip settings into `prep_multi_ofe_hillslope` from `_prep_multi_ofe`
and choose transform versus copy at the existing source-to-generated boundary.
Add a configured-value watershed accessor used only by WEPP prep and UI display;
retain the effective property's multi-OFE suppression for abstraction, AgFields,
and other consumers. Add narrow unit, filesystem-boundary, and preparation tests
before updating UI help and affected user/developer docs.

Run focused tests, rq-engine payload regressions, frontend gates, the full
Python suite, documentation lint, broad-exception enforcement, and code-quality
observability. Include a direct RQ dependency test proving prep failure makes
the aggregate root terminal-failed, exposes the child exception through
`jobinfo`, and prevents hillslope/downstream execution. Obtain correctness and
security review and resolve all medium/high findings.

Deploy the exact committed candidate to `forest`, discover the rq-engine
operation schema/defaults/errors, submit `run-wepp` for `dainty-signature` with
`clip_hillslopes: true` and `hillslope_clip_length: 60`, poll the returned job,
then inspect generated hillslope slope files. Compare every source/generated
pair for lengths, preserved structure, and area.

## Concrete Steps

Run from `/home/workdir/wepppy` unless otherwise noted:

    wctl run-pytest tests/topo/test_watershed_abstraction_slope_file.py
    wctl run-pytest tests/nodb <targeted multi-OFE prep module>
    wctl run-pytest tests/microservices/test_rq_engine_wepp_routes.py
    wctl run-npm lint
    wctl run-npm test
    wctl run-pytest tests --maxfail=1
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    python3 tools/code_quality_observability.py --base-ref origin/master

Use `wctl doc-lint --path <file>` for each changed Markdown file. Deployment and
rq-engine commands must be written into a Forest evidence artifact as executed;
do not place credentials in that artifact.

The bounded Forest deployment sequence is:

    hostname
    pwd
    git rev-parse HEAD
    wctl ps --format json
    wctl rq-info --detail
    wctl up -d --no-build --no-deps --force-recreate weppcloud rq-engine rq-worker rq-worker-batch
    wctl ps --format json
    wctl rq-info --detail
    curl -fsS https://wc.bearhive.duckdns.org/weppcloud/health
    curl -fsS https://wc.bearhive.duckdns.org/rq-engine/health

Record before/after container IDs and prove `wepppy.__file__` plus repository
HEAD resolve to the candidate bind-mounted checkout. Define
`MOFE_CLIP_CANDIDATE_SHA` as the one implementation commit and
`MOFE_CLIP_ROLLBACK_SHA` as its standalone checkpoint parent before deployment.
If deployment or smoke fails, stop this package's admission and use an additive
Git revert so unrelated history is preserved:

    test -z "$(git status --porcelain)"
    test "$(git rev-parse HEAD)" = "$MOFE_CLIP_CANDIDATE_SHA"
    test "$(git rev-parse "$MOFE_CLIP_CANDIDATE_SHA^")" = "$MOFE_CLIP_ROLLBACK_SHA"
    git revert --no-edit "$MOFE_CLIP_CANDIDATE_SHA"
    git rev-parse HEAD
    wctl up -d --no-build --no-deps --force-recreate weppcloud rq-engine rq-worker rq-worker-batch
    wctl exec rq-worker python -c 'import wepppy; print(wepppy.__file__)'
    curl -fsS https://wc.bearhive.duckdns.org/weppcloud/health
    curl -fsS https://wc.bearhive.duckdns.org/rq-engine/health

The revert diff must remove only changes introduced by the candidate. Never
deploy this package to forest1 or production.

Do not recreate workers until `wctl rq-info --detail` records zero started jobs
in both default and batch. If the preflight reports active work, wait for it to
drain and repeat the preflight; do not cancel unrelated jobs. After recreation,
record that both `rq-worker` and `rq-worker-batch` are running and registered
before submission.

## Validation and Acceptance

A mixed three-OFE source containing lengths 40, 90, and 120 m clipped at 60 m
must generate lengths 40, 60, and 60 m. Its shared width must increase by
`250 / 160`, preserving width times total length. Structural slope data must be
unchanged. Disabled clipping must copy source geometry unchanged.

On `forest`, the rq-engine job must reach `finished`. Parsing every generated
hillslope file matching `p<digits>.slp` must report zero OFEs greater than
60 m. At least one source OFE must have exceeded 60 m. Every source/generated
pair must preserve OFE count and structural profile/header fields, and total
area must match with relative or absolute tolerance `1e-9`.

## Idempotence and Recovery

The transformation reads a source and writes a destination deterministically;
re-preparation is safe. Tests use temporary directories. A failed Forest run
may be resubmitted only after job information identifies the failure and the
operation error catalog authorizes the recovery. Rollback uses the exact
additive revert sequence above; existing run state remains readable because no
schema changes occur.

## Artifacts and Notes

Contract, correctness, test, deployment, and generated-output evidence live
under `docs/work-packages/20260904_mofe_hillslope_clipping/artifacts/`.

## Interfaces and Dependencies

The slope utility retains
`clip_slope_file_length(src_fn, dst_fn, clip_length) -> None` and broadens its
supported input from exactly one OFE to one or more OFEs. The multi-OFE worker
tuple gains the configured clip boolean and clip length. A dedicated read-only
configured-value property supplies WEPP prep/UI without changing the existing
effective property used by other consumers. No external dependency is added.

Revision Note (2026-09-04, Codex): Initial self-contained plan created from the
operator-approved per-OFE clipping request and observed `dainty-signature`
failure mode.

Revision Note (2026-09-04, Codex): Completed implementation, reviews, full-suite
validation, bounded Forest deployment, rq-engine execution, and all-file output
acceptance.
