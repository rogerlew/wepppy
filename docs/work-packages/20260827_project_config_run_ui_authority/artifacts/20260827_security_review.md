# Security Review - Project Config Run UI Authority (WP12D)

## Metadata

- **Package**: `docs/work-packages/20260827_project_config_run_ui_authority/`
- **Reviewer**: independent `wp12b_security_contract_review` agent
- **Date**: 2026-08-28
- **Context**: ratified amendment `PC-24/WP12D-20260827-3` at starting revision
  `5e04e0da9a23dd676e171f1857e14fa38cc9dfbe`

Initiative branch: feature/project-owned-config
Canonical branch: master
Promotion policy: merge only at the roadmap promotion gate

## Security Triage Decision

- **Security impact level**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: effective config locale and run-scoped selections choose
  executable data-provider paths; auth policy is unchanged.
- **Threat model assumptions**: locale lists, legacy config tokens, persisted
  state, stored graphs, capability deltas, acknowledgment payloads, and
  submitted stable/runtime IDs are untrusted. Existing auth, CSRF, ownership,
  locking, filesystem, and queue boundaries remain mandatory.

## Binding Checkpoint Findings

The reviewer assessed the exact ratified canonical/checkpoint diff over
`5e04e0da9a23dd676e171f1857e14fa38cc9dfbe`. No High, Medium, or Low security
findings remain. A fresh independent security review of the implementation
candidate is still required before Forest writer exposure.

## Verdict

- **Gate status**: `pass` for the standalone checkpoint and implementation start
- **Unresolved findings**: High 0; Medium 0; Low 0
- **Release recommendation**: checkpoint permitted; Forest writer exposure and
  production remain unauthorized

## Required Surface Checks

The binding review must prove that malformed locale composition in
non-flattened legacy mode and a missing required Builder registry fail closed
with exact 409/503 diagnostic transports and error IDs;
query/link/config-registry metadata cannot override `.cfg` locale;
legacy locale-bearing creation overrides fail before directory publication or
controller initialization; role/run/auth boundaries precede authority
resolution; cross-profile submissions cannot mutate NoDb, timestamps, files,
or queues; exact-current, no-capability, schema-v1, non-Builder, overlay,
Turkey, and RHEM states remain usable; stored schema-v2/v3 graphs cannot be
broadened implicitly by the live registry; schema-v2 remains permanently
frozen and refresh-unavailable; only an eligible complete schema-v3 project may
use the exact acknowledged refresh; eligibility is limited to Builder-source
manifests with exact runtime-token/graph/default/manifest locale and selection
congruence; and no new path, upload, subprocess, queue, or egress surface is
introduced.

Flattened no-capability/schema-v1 classification must precede legacy locale
validation. Those modes must not consult the live registry or acquire a new
failure for absent, empty, unknown, or valid locale state; existing malformed
present-v1-axis errors remain unchanged.

Project-local `_defaults.cfg` and `_defaults.toml` require direct hostile and
compatibility cases for missing, empty, invalid, and explicit locale values.
The global `NoDbBase.locales` property must remain unchanged. Only the named
landuse, soils, and climate domain consumers may use the effective-config
locale. RQ endpoint schema/default/error documents, aggregated operation
documents, pipeline, and readiness must resolve the same authority as their
paired mutation endpoints; generic RQ envelopes remain unchanged.

Capability refresh requires separate direct checks that read-only availability
and preview cannot mutate; only owner/Admin/Root may apply; acknowledgment is
exact, initially unchecked, preview-bound, and enforced for direct API callers;
missing, false, wrong, or stale acknowledgment fails before Redis reservation
or enqueue; locale cannot change; the current graph is complete and
same-locale; primary project selections and linked runtime selectors remain
canonical and incompatible removals fail without substitution; schema-v3
structures match an append-only known-identity allowlist rather than accepting
arbitrary self-consistent graphs; the config/manifest replacement and
reversible delta are one crash-recoverable transaction; recovery never applies
an unacknowledged graph; pre-reservation failures leave no queue history while
post-enqueue recovery is accurately reconciled through opaque preview/digest
state; and the manifest stores no personal identity. The enqueue signature may
change, but queue topology and dependency edges must not.

At least one direct unmocked test must exercise each changed boundary for valid
and hostile state. Security approval cannot replace correctness review.

## Validation Evidence

The binding review confirmed:

- fail-closed authority ordering, authentication/run access before resolution,
  and no broad fallback;
- pre-mutation/pre-reservation rejection for cross-profile submissions,
  acknowledgment errors, stale previews, and incompatible selections;
- isolation of flattened no-capability/schema-v1 and localized legacy modes;
- append-only structural authorization that rejects unknown self-consistent
  graphs;
- selection-preserving same-locale refresh and exact manifest/config
  congruence;
- commit-point recovery, latest-preview idempotency, and absence of personal
  identity from manifest/status records; and
- reader-first rollback plus mandatory direct unmocked valid/hostile tests and
  real Forest refresh/reopen/rollback evidence before writer exposure.

`git diff --check` passed for the canonical amendment set.

## Residual Risk and Sign-off

No risk is accepted. This sign-off authorizes only the standalone checkpoint
and implementation start. Forest writer exposure requires the final
implementation security review and evidence gates. Production remains outside
WP12D.

- **Security reviewer**: independent `wp12b_security_contract_review` agent,
  READY

- **Package owner disposition**: accepted; no findings to remediate

## WP12D Writer Implementation Security Disposition

### Revision binding

- **Review completed**: 2026-08-28 03:45 UTC
- **Reader-floor base**: `80f4810b7be59d90a64b4771f587eb360987a820`
- **Candidate worktree HEAD**: `5eb451a7640fa3148a8872dd74f3756d8c88e7ce`
- **Review object**: the exact uncommitted WP12D writer candidate over that
  reader floor, excluding only the unrelated dirty paths recorded in the
  tracker and validation-generated code-quality reports

### Findings

No in-scope security findings remain: High 0; Medium 0; Low 0.

The review initially reproduced one recovery defect: a contract-permitted
preexisting manifest digest mismatch could strand an accepted update after a
crash. The final candidate closes it by treating the prior declared digest as
warning-only provenance while requiring the resulting manifest digest to match
the resulting config. Direct real-filesystem tests now recover successfully
after both the config-replacement and manifest-replacement fault points.

One preexisting Low defense-in-depth residual remains outside the ratified
WP12D changed-consumer set. `wepppy/rq/project_rq_archive.py` excludes the exact
root transaction filenames, but its helper does not exclude descendants such
as `.config-amendment.pending.json/payload`. A hostile archive can therefore
restore a directory at the journal filename and make later recovery fail
diagnostically until an operator removes it. The file is unchanged from the
reader-floor base, the WP12D writer never creates such a descendant, and the
real journal is recovered and removed under the lifecycle lock before archive
creation. This is a bounded availability-hardening follow-up, not a PC-24
conformance blocker. Changing that archive consumer requires its own contract
amendment and ratification; descendant exclusion should be added and tested in
that follow-up. No in-scope WP12D risk acceptance is required.

### Security evidence

The final review confirmed:

- JWT scope, run access, and owner/Admin/Root mutation authorization precede
  locale, registry, preview, or recovery authority resolution; the worker
  reauthorizes the captured actor before mutation;
- capability and combined requests require the exact initially unchecked,
  preview-bound acknowledgment before Redis reservation or enqueue, and stale
  preview precedence does not permit request-shape or acknowledgment bypass;
- schema-v3 refresh eligibility is fail-closed on Builder source, same-locale
  runtime/profile/default/selection/cell-size/source/runtime congruence,
  complete stored authority, and append-only reader-floor-known structural
  identity;
- the route resolves one application revision and passes that exact immutable
  value to the worker; worker environment drift cannot alter durable
  provenance;
- complete config, manifest, journal, amendment, and canonical serialization
  bounds are preflighted under the project lock before reservation, and the
  worker reuses the same serializer;
- pending-journal hashes, base64 payloads, sizes, paths, manifest schemas,
  amendment kinds/shapes/sequences, canonical JSON values, and resulting config
  digest are validated before recovery writes; malformed and unreadable
  journals leave target files unchanged;
- hostile native climate, landuse, and soils dataset/method fields are checked
  against the same run authority before controller parsing, timestamp removal,
  file mutation, or enqueue, while the bounded exact-current carveout cannot
  authorize a different hidden value;
- availability, preview, apply-accepted, and apply-recovered OpenAPI responses
  use closed typed schemas; the apply request has three closed variants for
  additive, capability-only, and combined updates;
- browser diagnostics insert server details and error IDs only through
  `textContent`, and acknowledgment state resets on preview, error, modal close,
  Escape, and successful apply;
- the amendment contains no actor identity, credentials, config contents, or
  new path, upload, subprocess, network-egress, or queue-dependency surface; and
- rollback readability is anchored to the recorded reader floor. Forest
  rollback occurs only after the accepted refresh job is terminal, then proves
  the refreshed config and manifest reopen byte-for-byte unchanged.

The package records the full validation result as Python 7147 passed/63
skipped, frontend 107 suites/801 tests, with lint, stubs, broad-exception,
vulture, diff, documentation, and RQ graph gates green. The reviewer reran 73
focused security tests covering update persistence/recovery, route
authorization and reservation ordering, worker reauthorization, exact OpenAPI
schemas, hostile landuse input, and soils authority; all passed. Targeted
`git diff --check` also passed.

### Final verdict

- **Gate status**: `pass` for exact-host Forest writer exposure
- **Unresolved in-scope findings**: High 0; Medium 0; Low 0
- **Residual follow-up**: one preexisting out-of-scope Low archive descendant
  exclusion hardening item, nonblocking for PC-24 and Forest
- **Release recommendation**: READY for the contracted Forest
  refresh/reopen/reader-floor rollback acceptance only; production remains
  unauthorized by WP12D
- **Security reviewer**: independent `wp12b_security_contract_review` agent,
  READY

## WP12D Post-READY Security Delta Recheck

### Revision binding

- **Review completed**: 2026-08-28 05:41 UTC
- **Reader-floor base**: `80f4810b7be59d90a64b4771f587eb360987a820`
- **Candidate worktree HEAD**: `5eb451a7640fa3148a8872dd74f3756d8c88e7ce`
- **Delta reviewed**: the uncommitted changes after the writer disposition above,
  including terminal job diagnostics, paired soils/landuse/climate mutations,
  update reconciliation and error transport, stored runtime-locale dispatch, and
  exact endpoint/OpenAPI parity

### Findings and closure

The delta recheck found three Medium integrity defects. All are closed in the
reviewed worktree. No High, Medium, or Low in-scope finding remains.

1. Terminal `/jobinfo` success initially accepted any syntactically valid digest
   pair. A well-formed result for a different transition could therefore clear
   the reviewed acknowledgment, hide the update action, and be presented as the
   reviewed commit. The controller now requires the terminal prior/resulting
   digests to equal the retained preview's current/resulting digests exactly.
   A mismatch remains indeterminate and does not clear the open or acknowledgment
   state. The generated `controllers-gl.js` contains the same check.
2. Flask climate selection initially validated one `(catalog_id, mode)` relation
   but persisted it through two independent NoDb setter transactions. Concurrent
   authorized requests could interleave into a pair that no request validated.
   The final route-local implementation re-resolves authority and exact-current
   eligibility under one `Climate.locked()` transaction, validates the enum and
   station constraints, and writes or rolls back the complete pair. Its rollback
   snapshot is taken after lock acquisition, so a waiting request cannot capture
   an in-flight partial pair. Deterministic two-thread normal and injected
   second-field-fault tests prove serialization and complete-pair rollback.
   This closure changes only the already ratified `climate_bp.py` consumer; it
   does not broaden the exact implementation source boundary or require an
   amendment for `core/climate.py`.
3. The first terminal-result remediation still read the mutable controller
   preview after enqueue. Loading a newer preview while the earlier job was
   pending could therefore rebind terminal success or failure reconciliation to
   the wrong reviewed transition. Apply now captures a frozen object containing
   the exact submitted preview ID and current/resulting digests, and passes that
   same object through every recursive poll, terminal result, and failure
   reconciliation path. Immediate recovered HTTP results use the same exact
   congruence predicate. A later rendered preview cannot redefine the pending
   job's authority context; mismatched results remain indeterminate without
   clearing the update action or acknowledgment.

The remaining delta surfaces are security-preserving:

- authorization still precedes project-config status/recovery/registry work,
  and malformed recovery state returns diagnostic `409 config_update_unavailable`
  before Redis reservation or enqueue;
- recovery diagnostics expose bounded state classifications, not config bytes,
  paths, credentials, or actor identity;
- landuse dataset/method persistence uses one grouped NoDb transaction, soils
  and landuse aliases must agree before mutation, and unsupported native fields
  fail before controller parsing, timestamp removal, file mutation, or enqueue;
- schema-v2/v3 runtime locale dispatch derives canonical tokens from validated
  stored locale-profile IDs and does not consult mutable flattened locale text;
- stored graphs remain the run authority independent of live registry drift;
- Flask climate alias disagreement, missing pairs, cross-profile values, and
  stale exact-current values fail before mutation; and
- apply request variants and availability, preview, accepted, and recovered
  responses remain closed and exactly represented in OpenAPI.

### Verification evidence

- 327 focused Python tests covering update routes/recovery, the worker, climate,
  landuse, soils, stored authority, operation documents, and exact OpenAPI:
  passed.
- 52 post-remediation Flask/rq-engine climate tests, including both deterministic
  concurrency regressions: passed.
- Focused project-config update controller suite: 19 passed.
- Full frontend suite: 107 suites and 808 tests passed.
- Frontend lint and `git diff --check`: passed.

### Delta verdict

- **Gate status**: `pass` for exact-host Forest writer exposure
- **Unresolved in-scope findings**: High 0; Medium 0; Low 0
- **Residual follow-up**: the preexisting out-of-scope Low archive-descendant
  exclusion item recorded above remains unchanged
- **Release recommendation**: READY for contracted Forest acceptance only;
  production remains unauthorized by WP12D
- **Security reviewer**: independent `wp12b_security_contract_review` agent,
  READY

## WP12D Forest Fresh-Worker Security Delta Recheck

### Revision binding

- **Review completed**: 2026-08-28 06:04 UTC
- **Reader-floor base**: `80f4810b7be59d90a64b4771f587eb360987a820`
- **Candidate worktree HEAD**: `5eb451a7640fa3148a8872dd74f3756d8c88e7ce`
- **Delta reviewed**: the same-name lazy authorization wrapper in
  `wepppy/rq/project_config_update_rq.py`, the real fresh-interpreter RQ task
  resolution regression, worker authorization ordering, and failed-job Redis
  reservation cleanup

### Findings and security analysis

No High or Medium security finding remains. The Forest failure occurred while a
fresh RQ process resolved the task, before task execution. The recorded config
and manifest remained byte-for-byte unchanged, and the operator removed only
the failed job's exact reservation value. The import-cycle correction does not
move authorization later in the mutation path: the worker calls the canonical
rq-engine `authorize_run_mutation` implementation before `get_wd` or
`apply_project_config_update`. A missing, malformed, stale, or no-longer-owning
captured actor therefore fails closed before any project-file mutation, while
the worker `finally` boundary still attempts reservation release on
authorization or apply failure.

The lazy wrapper contains no permissive import fallback, catches no
authorization exception, accepts no client-selected module or callable, and
does not change task arguments, actor metadata, queue topology, filesystem
paths, diagnostics, or the project transaction. A fresh-interpreter regression
resolves the task through `rq.utils.import_attribute`, which exercises the
failed RQ loading boundary without relying on modules already loaded by pytest.
An independent container check also invoked the lazy canonical binding in a
fresh process and proved that a non-user actor raises the canonical
authorization error.

The prior Low Redis reservation race is closed. Release now sends one fixed Lua
script to Redis and passes the run-scoped key and expected job ID only through
`KEYS` and `ARGV`. Redis compares the current value and deletes it in the same
server-side operation. There is no interval in which an expired reservation can
be replaced after a matching read but before deletion, and neither the run ID
nor job ID can alter the executed script. The regression proves that a
replacement reservation is preserved and the exact matching reservation is
removed.

### Verification evidence

- Worker and project-config update-route suites: 20 tests passed, including the
  real fresh-interpreter task resolution, authorization-loss/no-mutation, and
  atomic replacement-preservation and failure-path release regressions.
- Independent fresh-process lazy authorization invocation: canonical
  `AuthError` raised for a disallowed token class.
- `git diff --check`: passed.

### Delta verdict

- **Gate status**: `pass` for exact-host Forest writer exposure
- **Unresolved in-scope findings**: High 0; Medium 0; Low 0
- **Residual follow-up**: the preexisting out-of-scope Low archive-descendant
  exclusion item remains unchanged
- **Release recommendation**: READY for contracted Forest acceptance only;
  production remains unauthorized by WP12D
- **Security reviewer**: independent `wp12b_security_contract_review` agent,
  READY
