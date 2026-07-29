# Verify the shared disturbed CSV editor contract

This ExecPlan is maintained under `docs/prompt_templates/codex_exec_plans.md`.
Keep `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes &
Retrospective` current.

## Purpose / Big Picture

An authorized user can load a run-scoped disturbed lookup, edit it, and save
only against the exact version originally loaded. Concurrent changes lock the
old page and offer safe recovery. Missing remote spreadsheet runtime, session,
network, validation, and persistence failures appear in the status panel and
never enable an unsafe save.

## Progress

- [x] (2026-07-28 UTC) Scaffolded SURF-10 and ratified concise intent.
- [x] (2026-07-28 UTC) Traced the shared template, both producers, disturbed
  snapshot/mutation routes, lookup helpers, and prior hardening evidence.
- [x] (2026-07-28 UTC) Added actual-render and four executable
  production-inline-client regressions.
- [x] (2026-07-28 UTC) Ran focused route, client, and lookup contract evidence.
- [x] (2026-07-28 UTC) Confirmed conformance without a production patch.
- [x] (2026-07-28 UTC) Completed broad gates, security review, records, and
  closure.

## Surprises & Discoveries

- Observation: The March hardening package implemented the registered
  concurrency behavior but explicitly left browser runtime/polling automation
  as follow-up work.
  Evidence: Its QA artifact records no executable DOM/network loop coverage;
  current tests assert only template source strings.

- Observation: The template is shared with Geneva CN editing even though the
  registry names the disturbed editor.
  Evidence: Both `disturbed_bp.py` and `geneva_bp.py` render
  `controls/edit_csv.htm` with producer-specific URLs.

## Decision Log

- Decision: Ratify the observed safe concurrency behavior without changing
  lookup parameterization, schemas, or variant meaning.
  Rationale: SURF-10 is a registered conformance audit and the prior hardening
  contract already governs mutation integrity.
  Date/Author: 2026-07-28 / Codex with operator authority.

- Decision: Keep CDN failure explicit and visible in this package.
  Rationale: The register specifically calls out runtime/CDN failure, while
  dependency replacement would exceed the bounded audit and require separate
  evaluation.
  Date/Author: 2026-07-28 / Codex.

## Outcomes & Retrospective

SURF-10 closed without a production repair. The new actual-render regression
proves hostile-value escaping, producer URL identity, CSRF, status/actions, and
runtime assets. Four executable inline tests prove successful SHA-bound save,
blank-row pruning, stale polling and recovery lock retention, stale-save
mapping, and safe missing-CDN-runtime failure.

Focused route/render tests passed 195, disturbed lookup tests passed 31, and
focused Jest passed 4. Frontend lint and the full 99-suite/707-test sweep
passed. The repository-wide Python suite passed 5,541 with 58 skips. Dedicated
security review passed with no unresolved finding.

## Context and Orientation

`wepppy/weppcloud/templates/controls/edit_csv.htm` is a standalone Pure page
with an inline client. Disturbed routes in
`wepppy/weppcloud/routes/nodb_api/disturbed_bp.py` supply variant-stable URLs,
atomic snapshots, metadata polling, and preconditioned writes. The writer in
`wepppy/nodb/mods/disturbed/disturbed.py` validates the full table and replaces
the file atomically. `geneva_bp.py` supplies the same UI for its CN table.

## Plan of Work

Render the real template with ordinary and hostile values and assert its exact
config, actions, CSRF, assets, and safe escaping. Execute the production inline
client under Jest/jsdom with controlled fetches and spreadsheet runtime.
Exercise initialization, save, stale polling, recovery, and failure paths.
Retain the existing disturbed route/NoDb tests for auth, lookup variant,
no-store snapshot, lock, validation, stale rejection, atomic write, and reload.
If a regression exposes a mismatch, patch the smallest existing function and
record why the unchanged contract required it.

## Concrete Steps

From `/home/workdir/wepppy`:

    wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py \
      tests/weppcloud/routes/test_disturbed_bp.py \
      tests/weppcloud/routes/test_geneva_bp.py --maxfail=1
    wctl run-pytest tests/nodb/mods/disturbed/test_lookup_contract.py --maxfail=1
    wctl run-npm test -- edit_csv
    wctl run-npm lint
    wctl run-npm test
    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path docs/work-packages/20260728_pure_ui_disturbed_csv_editor_contract
    wctl doc-lint --path docs/work-packages/20260716_pure_ui_contract_standardization_c
    git diff --check

No controller bundle, RQ graph, stub, or ADR gate applies unless implementation
scope changes.

## Validation and Acceptance

Acceptance requires direct actual-render evidence, executable production client
evidence for successful and failing state transitions, and retained
route/NoDb evidence for authorization, variant confinement, concurrency,
validation, atomicity, and reload. Focused and broad applicable gates pass, or
a proven unrelated preexisting broad failure is recorded.

## Idempotence and Recovery

All render, Jest, pytest, and lint commands are safe to rerun. Tests use
temporary run roots and controlled browser globals. Preserve unrelated work.
On stale or failed recovery, the persisted lookup is unchanged and the page
remains locked until a successful current snapshot load.

## Interfaces and Dependencies

Preserve the config data attributes, status/action element IDs, CSRF header,
session-token POST, snapshot/meta GETs with `no-store`, 15-second poll,
`if_match_sha256` save body, response fingerprint headers, variant query, and
canonical disturbed error codes. Add no dependency, queue edge, fallback
write, schema alias, or parameter default.

## Revision Notes

2026-07-28: Created from explicit operator direction to scaffold and execute
SURF-10.
2026-07-28: Closed after complete conformance evidence; no production repair
was retained.
