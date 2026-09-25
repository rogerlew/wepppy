# Single User-Defined landuse and soils

**Status**: Open — Builder scope approved; contract checkpoint and implementation pending
**Started**: 2026-09-25 20:17 UTC
**Owner**: Requesting operator; implementation unassigned
**Security impact**: `high` — uploads, parsers, filesystem writes, and feature-policy enforcement

## Overview

Add **Enable single landuse and soils upload** to Config Builder. Selecting it
creates a non-disturbed project where users may independently select **Single
User-Defined** landuse and soil modes. Each accepted source is replicated across
all hillslopes and OFEs. Disturbed, SBS, their dependent features, and buffer OFEs
are unavailable in this configuration. This package plans the feature; no runtime
behavior has changed.

## Confirmed requirements and rationale

The operator approved reconciliation around the Builder design on 2026-09-25 and
explicitly instructed: “disable the buffer ofe when this feature is enabled.”
This supersedes the initial per-input disturbance-bypass design. Independence now
means independent run-control choices under a separately selected project policy.

- The Builder checkbox is **Enable single landuse and soils upload**, unchecked
  by default. Unchecked retains current Builder behavior and does not expose the
  new upload modes. Checked enables both upload capabilities without forcing
  either run control to select them or requiring both uploads.
- Checked disables Disturbed and SBS for the entire project, including when both
  run controls use database modes. No Disturbed Class selectors or mixed
  uploaded/Disturbed workflows are in scope.
- Exclude direct and indirect Disturbed-dependent features from capabilities,
  menus, controls, applicable reports, activation APIs, and execution paths.
  Config refresh and automatic dependencies must not re-enable them.
- **Buffer OFEs are disabled whenever the Builder option is enabled**, not merely
  while an upload mode is selected. Resolve and persist `watershed.mofe_buffer =
  false`; disable buffer creation controls and buffer-landuse selection, and reject
  attempts to enable buffers through APIs before mutation or job submission.
  Switching either run control back to a database mode does not enable buffers.
- Multi-OFE remains supported without buffer OFEs. Replicate the uploaded source
  across every hillslope and every OFE in that non-buffer topology.
- Existing compatible non-disturbed modifiers remain functional on generated
  copies. The buffer exception above is explicit. Accepted source bytes remain
  intact; modifiers may cause final per-hillslope/OFE parameters to differ.
- Each run control offers **Single User-Defined** with the standard theme-aware
  Pure CSS upload control. Landuse accepts `.man`/`.MAN`; soil accepts `.sol`/`.SOL`.
- Validate server-side before installing accepted sources beneath the run's
  `landuse/` and `soils/` directories. Preserve existing valid input on rejection.
- Explain the file type, replication across all hillslopes/OFEs, and absence of
  disturbed parameterization. Show the accepted filename after upload and reload
  using the SBS `wc-field__label`, `wc-text-display`, and escaped `<code>` pattern.
- Apply this choice at creation. Existing projects are not migrated or stripped
  of modules, SBS, buffers, or artifacts. Unchecked/legacy workflows retain their
  current behavior, including existing BAER alternatives and buffer support.

Suggested Builder help: “Allow single landuse and soil uploads across all
hillslopes and OFEs. Disables SBS, disturbed parameterization, dependent features,
and buffer OFEs for this project. Other landuse and soil modes remain available.”

## Scope and complexity budget

Include Builder selection serialization and provenance, resolved capabilities,
config refresh, feature exclusion, buffer enforcement, additive run modes,
upload lifecycle, non-disturbed uniform build/preparation, summaries, controls,
tests, and user/operator/developer documentation. Reuse existing owned parsers,
Pure macros, NoDb locks/scoped mutation, rq-engine transport, and RQ jobs.

Exclude Disturbed Class selectors, per-domain disturbance bypass, legacy-only
`0.cfg` availability, existing-project conversion, archive/multi-file uploads,
unrelated numerical changes, deployment, and live-run repair. No new queue,
service, datastore, daemon, dependency, privilege, protocol, or deployment topology
is budgeted. Any escalation requires retained evidence of a failed simpler
acceptance test plus the smallest remedy and recovery cost.

## Configuration and feature policy

The [Builder design](notes/builder_upload_option_assessment.md) details boundaries.
The [dependency trace](artifacts/20260925_dependency_review.md) identifies required
exclusions: Treatments, Omni Scenarios/Contrasts, PATH Cost-Effective, legacy
Debris Flow, RUSLE, Post-fire debris flow, and revegetation workflows. Preserve
compatible RAP analysis, Ash, Geneva, and other independent features, with targeted
runtime checks. Correct missing registry declarations without breaking valid
legacy alternatives. Enforce a single resolved policy across UI/API/build/refresh.

## Remaining decisions before implementation

The [decision register](notes/discovery.md#decision-register) retains unresolved
format/content, source OFE count, upload timing, replacement/concurrency, storage,
and retention choices. Recommended initial formats are management 98.4/2016.3 and
soil 7778, with a one-OFE source replicated into project topology. These are
recommendations pending representative parser/serializer/executable evidence.
Finalize exact mode values, capability IDs, payload fields, metadata, and supported
configuration/binary combinations in the checkpoint. Builder policy, independent
selection, multi-OFE support, compatible modifiers, and buffer exclusion are settled.

## Compatibility and regression plan

Append unused enum identities. Do not repurpose landuse raster mode 4 or soils
database mode 2. Add optional metadata with absent-state-compatible reads and
stable summary keys; preserve existing user-visible fields and columns. Document
schema propagation before editing writers.

Test all four uploaded/database input combinations in opted-in non-disturbed
projects with both single- and multiple-OFE representations. Verify no buffer OFE
or Disturbed/SBS workflow can be enabled, including after switching run modes,
refresh, clone, and archive/restore. Test unchecked and legacy projects separately
for unchanged disturbance and buffer behavior; those projects do not gain uploads.
Trace source and metadata into summaries, parquet, consumed inputs, and reports.

## Contract and review gates

Milestone 1 must finalize the exact current-contract/source matrix under
[contract-first change](../../standards/contract-first-change-standard.md).
Amend the unconditional Builder Disturbed rule and ADR-0064 with an explicit
opt-in exception, and document the buffer exclusion and its rationale. Record
implementation conformance as pending. Add a parameterization ADR with operator
provenance for disturbance and buffer-policy changes before merge.

The [design security artifact](artifacts/20260925_security_review.md) is created
now and must receive independent design review **before the canonical contract
checkpoint**, alongside the required two independent contract reviews and their
dispositions. Finalize pending bounds/lifecycle decisions and close design findings
before that checkpoint. Record the standalone contract ancestor before editing
implementation. This package revision is not that checkpoint or commit authority.

During implementation, extend the same security artifact with real boundary
and environment evidence; complete the separate correctness/UX review from its
canonical template. Resolve all medium/high implementation findings before
closeout. A corrected review schedule is not a security approval.

## Generated artifact validation gate

Applicable to future implementation, not these documentation edits. Retain exact
request/config intent, reloaded state, accepted-source hashes, all-hillslope/OFE
assignment checks, summary semantics, and the actual `.man`/`.sol` files consumed
under `wepp/runs/`. Verify matching slope/management/soil OFE count/order and no
buffer segment, then fresh WEPP output and filename/report readback.

Exercise real parser, filesystem, builder, serializer, and consumer boundaries in
a representative production-equivalent development project with revision,
identities, groups, mounts, and config recorded. Cover repeated builds, mode
switches, publication/queue failures, clone/archive/restore, and compatible
modifiers. Accepted sources and useful failure diagnostics remain visible normal
project records. Define bounded handling of rejected hostile bytes separately.
Persisted intent or a successful job is not output correctness.

## Deliverables and readiness

The [ExecPlan](prompts/active/single_user_defined_landuse_soils_execplan.md),
[tracker](tracker.md), discovery/design notes, and review artifacts provide the
implementation handoff. WPR-01 through WPR-03 corrections are independently confirmed and closed. Format/lifecycle decisions, canonical amendments, design security
approval, contract reviews, and the ancestor checkpoint remain pending.

## References

- [Shared controller contract](../../ui-docs/controller-contract.md)
- [Project-owned configuration contract](../../schemas/project-owned-config-contract.md)
- [NoDb persistence contract](../../schemas/nodb-persistence-concurrency-contract.md)
- [RQ response contract](../../schemas/rq-response-contract.md)
- [CSRF contract](../../schemas/weppcloud-csrf-contract.md)
- [WEPP input contract](../../schemas/wepp-run-input-contract.md)
- [Artifact observability](../../standards/artifact-observability-standard.md)
- [Generated artifact validation](../../standards/generated-artifact-validation-standard.md)
