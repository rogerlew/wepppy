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
