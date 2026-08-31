# Deliver default-off named-preset snapshot creation

This ExecPlan is a living document maintained according to
`docs/prompt_templates/codex_exec_plans.md`. Keep `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` current.

Initiative branch: `feature/project-owned-config`. Canonical branch: `master`.
Promotion policy: merge only at the roadmap promotion gate.

## Purpose / Big Picture

After WP04, the existing Interfaces creation flow can be explicitly switched
into project-owned mode without changing its links or config tokens. A created
run receives a complete canonical copy of the effective named preset and a
manifest before any NoDb controller starts. Retrying one submission cannot
create another project, invalid or unsafe input cannot leave a ready project,
and turning the flag off restores the exact legacy path.

## Progress

- [x] (2026-08-26 20:00 UTC) Verify branch, prerequisites, contract, creation path, and checklist ownership.
- [x] (2026-08-26 20:00 UTC) Scaffold package and record data/schema compatibility plan.
- [x] (2026-08-26 20:32 UTC) Implement preset policies, typed resolution, manifest, and atomic materialization.
- [x] (2026-08-26 20:45 UTC) Implement 24-hour idempotency and default-off rq-engine integration.
- [x] (2026-08-26 20:58 UTC) Add all-preset/generated-output/route/failure/security fixtures.
- [x] (2026-08-26 21:12 UTC) Validate and complete correctness/security review; archive and commit follow this final plan update.

## Surprises & Discoveries

- Observation: the existing Interfaces flow already posts every named preset to
  rq-engine `/create/`, and that route synchronously allocates, initializes Ron,
  registers ownership, and redirects.
  Evidence: `wepppy/weppcloud/routes/run_0/run_0_bp.py:create_index` and
  `wepppy/microservices/rq_engine/project_routes.py:create`.
- Observation: the current create path converts accepted values back into a
  query suffix and gives that suffix to Ron; WP04 must materialize those values
  only on the flagged path without changing the unflagged path.
  Evidence: `_collect_overrides()` and `Ron(wd, cfg)` in `project_routes.py`.
- Observation: the shipped preset corpus includes international and specialized
  configurations that cannot safely inherit WP03's continental-US capability
  profile.
  Evidence: the 128-file policy corpus and the profile's `requires = ["continental-us"]` constraint.

## Decision Log

- Decision: add a strict, default-off
  `WEPPPY_PROJECT_CONFIG_PRESET_WRITER_ENABLED` boundary.
  Rationale: the contract requires reader-first rollout and forbids the new
  writer from changing legacy creation before enablement.
  Date/Author: 2026-08-26, Codex.
- Decision: implement reusable snapshot/idempotency primitives outside the
  route module, leaving HTTP response translation at the FastAPI boundary.
  Rationale: pure core tests can prove filesystem and Redis state transitions
  without weakening existing route authorization coverage.
  Date/Author: 2026-08-26, Codex.
- Decision: store normalized overrides as section/option/value/source records
  in the manifest while retaining the original preset as the second parent.
  Rationale: overrides are immutable selections, not parent source nodes.
  Date/Author: 2026-08-26, Codex.
- Decision: defer stable capability population to its explicit WP05 owner and
  do not infer a universal capability list during preset snapshotting.
  Rationale: inference would broaden or misstate capabilities for incompatible
  legacy presets; WP04 validates their runtime schema and policy corpus.
  Date/Author: 2026-08-26, Codex.

## Outcomes & Retrospective

WP04 delivered a dormant named-preset writer covering all 128 shipped presets,
canonical manifest-backed materialization before Ron, scoped 24-hour replay and
conflict handling, browser client keys, and contained failure cleanup. Focused,
subsystem, typing, documentation, correctness, and dedicated security checks
passed. Activation, deployed Redis/failover, mixed-reader, Forest, and stable
capability enforcement remain with WP11/WP12 and WP05 respectively.

## Context and Orientation

`wepppy/nodb/configs/_defaults.cfg` and the other top-level `.cfg` files are
canonical shared sources. `wepppy/project_config_serialization.py` parses and
serializes their typed maps; `wepppy/project_config_sanitization.py` rejects
secret and host-bound materialization. `wepppy/nodb/project_config_reader.py`
already recognizes the required flattened marker and validates manifest v1.
WP04 adds preset snapshot primitives and calls them from
`wepppy/microservices/rq_engine/project_routes.py` only when the writer flag is
true. An idempotency reservation is a bounded Redis record that ensures one
client-generated key and one normalized request create at most one run.

Implemented means all shipped presets validate, candidate bytes/manifests are
canonical and safe, atomic writes occur before Ron, and idempotency state is
correct. Wired means the actual `/create/` path uses those primitives behind
the default-off flag. Generated-output evidence is required and uses temporary
run directories; deployed `/wc1/runs` and Forest evidence remain WP11 scope.

## Plan of Work

Create a preset policy module with the complete deployment-owned preset ID set
and explicit durable override declarations. A resolver loads canonical shared
defaults and the named preset, overlays typed values, validates every accepted
override by section/option/type, writes flattened marker fields, serializes
through WP00B, scans through WP00A, and builds deterministic provenance plus a
timestamped manifest whose digest matches the exact bytes.

Create an initial materializer that refuses existing final files, writes each
candidate to a unique temporary sibling, flushes and fsyncs it, atomically
replaces the config then manifest, fsyncs the directory, and cleans temporary
files on failure. The route must resolve candidates before run allocation,
materialize after allocation, and only then construct Ron with the stable
`<preset>.cfg` token. Any later initialization or ownership failure uses the
existing scoped run-directory cleanup.

Create a Redis-backed idempotency service using `SET NX EX 86400`. Validate a
cryptographically random client key of at most 200 characters before reserve.
Fingerprint only creation mode, preset, normalized overrides, and registry
revision; scope authenticated records to actor and anonymous records to their
unguessable key boundary. Store only safe hashes/result metadata. A completed
match returns its original redirect, a different fingerprint returns canonical
409 conflict, a matching reservation returns 409 in progress with Retry-After,
and initialization/ownership failure releases the reservation.

Tests exercise every preset, exact canonical bytes, source independence,
manifest validation, stable tokens, allowed/unknown/credential overrides,
filesystem crash points, Ron ordering, replay/conflict/concurrency/release,
strict flags, Interfaces rendering, and the unchanged off path. Security review
checks path containment, secret scanning, log/response redaction, actor scope,
CAPTCHA/auth ordering, and cleanup containment.

## Concrete Steps

From `/home/workdir/wepppy` run:

    wctl run-pytest tests/nodb/test_project_config_preset_snapshot.py --maxfail=1
    wctl run-pytest tests/microservices/test_rq_engine_project_routes.py --maxfail=1
    wctl run-pytest tests/nodb --maxfail=1
    wctl run-pytest tests/microservices --maxfail=1
    wctl run-stubtest wepppy.nodb.project_config_snapshot
    wctl check-test-stubs
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path docs/work-packages/20260804_project_config_preset_snapshot
    git diff --check

## Validation and Acceptance

Every shared preset except `_defaults` must appear in the policy registry and
resolve without guessed types. Repeating one resolution produces identical
config bytes; only the manifest timestamp is time-derived. The generated pair
must reopen through the WP02 reader with no shared fallback. Removing or editing
shared files after creation must not affect that pair.

With the writer flag off, existing tests must observe the same Ron argument and
redirect. With it on, a spy Ron must observe both final files and a valid
manifest before construction. Same-key/same-fingerprint replay returns the
first redirect; mismatched input and concurrent duplicates return 409 with
canonical codes; failed initialization releases the key and removes the run.
Neither candidates, manifests, responses, logs, nor Redis values may contain a
credential, raw authentication token, CAPTCHA response, or config contents.

## Idempotence and Recovery

Resolution is read-only and repeatable. Initial materialization refuses to
overwrite final paths. Temporary siblings are uniquely named and removed on
handled failure. A route failure after allocation invokes the existing scoped
cleanup for only its newly allocated run. Idempotency reservations expire after
24 hours and are explicitly released on failed initialization/ownership, so an
intentional retry can allocate a fresh run. Disabling the writer restores the
legacy behavior without modifying existing projects.

## Artifacts and Notes

Closeout retains generated-pair evidence, a correctness review, a dedicated
security review, exact feature flag/upstream state, and WP05/WP06/WP10/WP11
handoffs. Do not record configuration contents, tokens, credentials, Redis
passwords, user emails, or production run identifiers.

## Interfaces and Dependencies

Use only standard-library config/JSON/hash/path/tempfile/time utilities,
existing WP00A/WP00B/WP02 primitives, and the repository Redis connection
factory. Add no dependency. Export the strict flag reader, policy/resolution
records, preset candidate resolver/materializer, and idempotency service with
matching stubs. Keep route response bodies on the canonical rq-engine error
contract and do not add queue wiring.

Plan revision note (2026-08-26): initial plan created from the ratified
contract, roadmap, normative checklist, prerequisite handoffs, and current
synchronous Interfaces/rq-engine creation implementation.
