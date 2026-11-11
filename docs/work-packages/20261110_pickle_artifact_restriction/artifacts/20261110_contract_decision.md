# Contract decision - Pickle artifact restriction

**Status**: Canonical amendments prepared; independent reviews and ancestor pending  
**Remediation ID**: `PICKLE-RESTRICT-F2-20261110`  
**Starting revision**: `991fc5e2c3f1cd2e5d74169e2d7bccb609203924`  
**Prepared**: 2026-11-11 03:50 UTC

## Decision

The operator directed a narrow F2 fix: restrict pickle files rather than build a
conversion or scanning system, keep tests/validation scoped to the changes, and
do not run the full suite.

The approved durable contract is:

1. Bootstrap rejects any added or modified path whose final suffix is `.pkl` or
   `.pickle`, case-insensitively, across every introduced commit and allowed
   Bootstrap directory.
2. Browse lists existing pickle artifacts and permits authorized byte download,
   but does not preview or deserialize them and does not advertise preview or
   D-Tale actions.
3. Direct browse preview and browse-to-D-Tale requests for either suffix return
   HTTP 415 before materialization, reader invocation, or outbound loader calls.
4. The D-Tale internal loader does not register or call a pickle reader and
   returns HTTP 415 if directly asked to load either suffix.
5. There is no fallback parser, magic-byte scanner, converter, feature flag, or
   migration. Restoring interactive pickle loading requires a new approved
   security decision.
6. Internal application-owned pickle serialization is unchanged unless direct
   evidence shows it consumes project-controlled files from these routes.
7. Validation comprises focused Bootstrap, browse, files API, D-Tale, stub,
   documentation, source-search, and scoped deployment checks. The full Python
   and frontend suites are not package gates.

Existing raw query/header byte-delivery modes remain available. Representation
requests cannot bypass the preview restriction. Authentication, authorization
and containment decisions retain precedence; missing files retain normal 404.
Deletion and ref behavior at Bootstrap remain unchanged; added and modified
paths receive the suffix check, and existing rename/copy rejection is preserved.

## Rationale

Python pickle can execute code while loading. Extension-based dispatch is the
only reason these project artifacts reach `pandas.read_pickle`, so removing that
dispatch and preventing new files closes the confirmed path with minimal
compatibility impact. Existing artifact bytes need not be trusted to remain
visible or downloadable.

## Canonical Authority to Amend

- Create `docs/schemas/bootstrap-git-input-contract.md` for Bootstrap admission.
- Amend `docs/schemas/browse-filesystem-contract.md` with the list/download-only
  security exception.
- Amend `docs/schemas/file-dependency-freshness-contract.md` with a cross-linked
  exception to its supported-readers preservation rule for pickle removal.
- Align browse and D-Tale AGENTS/README capability documentation.

## Compatibility Impact

- Existing users lose interactive preview/D-Tale for `.pkl` and `.pickle`.
- Existing users retain directory visibility and raw authorized download.
- Supported text/tabular formats are unchanged.
- New Bootstrap pushes containing either suffix fail with an actionable message.

## Classification and Boundaries

This is an intended security behavior change, not conformance to a pre-existing
pickle prohibition. Security impact is high: project-controlled artifacts
currently reach Python deserialization in request processes. The amendment
uses the existing filesystem contract's security exception while preserving
legacy visibility and byte delivery. The D-Tale generation contract previously
required supported readers to remain unchanged; its bounded cross-linked pickle
exception reconciles that conflict before implementation. There is no schema,
data migration, queue, parameterization, deployment-topology or auth change.

Applicable amended canonical authorities are the new Bootstrap Git input
contract, browse filesystem contract, and file dependency freshness contract.
The existing
`docs/schemas/weppcloud-browse-auth-contract.md`,
and `docs/schemas/weppcloud-browse-parquet-filter-contract.md` remain unchanged
constraints on access and supported Parquet behavior. The freshness contract's
viewer source-consistency rules remain unchanged for supported formats.

The finite source boundary is Bootstrap pre-receive path admission, browse
preview dispatch and capability metadata, directory D-Tale links, the D-Tale
bridge, and D-Tale eager reader registry/stub. The valid-state and failure-class
matrices are in `20261110_correctness_review.md` and
`20261110_failure_class_matrix.md`. Internal serialization is excluded absent
evidence that it consumes project artifacts through these entry points.

## Required Regression Evidence

- Real Git-hook rejection for both suffixes and case variants, with no push log.
- Browse 415 and zero `read_pickle` calls.
- No preview/D-Tale capability metadata or directory link.
- D-Tale bridge/internal loader 415 before downstream work.
- Legacy raw download byte equality.
- Supported Bootstrap and tabular controls.

## Approval and Reviews

- **Operator approval**: recorded in the 2026-11-10 Pacific conversation and
  reaffirmed by the instruction to execute this plan, including its checkpoint.
- **Independent contract review 1**: approved; see `20261110_contract_reviews.md`.
- **Independent contract review 2**: approved; see `20261110_contract_reviews.md`.
- **Canonical amendments**: prepared; implementation conformance and deployment
  explicitly pending.
- **Standalone ancestor commit**: pending.

Implementation is gated until the pending checkpoint items are complete.

## Archive compatibility clarification

Red tests exposed a stale planning assumption: archive-backed runtime access is
retired. Preserve existing 409/404 member responses and whole-archive byte access.
The approved pickle rule applies to physical files, including NoDir directory
roots; it does not restore virtual archive support. Both independent reviewers
approved this clarification on 2026-11-11 04:10 UTC before production edits.
