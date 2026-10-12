# CBEXEC-01 contract decision

Starting WEPPpy revision `cf2ad6d78`; native default branch `wepp_260430_negmeltfix_comparator` at `ef1874951b4fecae774825d3dabfe6a1b3d44484`. No implementation edits precede this checkpoint.

Operator approval: “the config builder needs to have wepp_261010 as an option” and asks to remove restrictions preventing reruns with new executable versions; then “maybe the sidecars need to track mofe support?”, “make the change in /workdir/wepp-forest default branch. remint sidecars for 260803 and 261010”, and “vendor in wepppy”. Existing session commit authority is retained. An optional scope question about upload projects was unanswered after reasonable opportunity; stated assumption includes those projects with distinct native-reader certification, not an inference that MOFE alone proves native input support.

## Applicable authority and delta

Amend project-owned-config-contract sections7.2/7.2.1 and9 capability authority through the explicit binary-only CBEXEC-01 exception; new wepp-executable-selection-contract.md is normative for paired feature declarations, live choices and legacy compatibility. Amend single-user-defined-inputs-contract.md and ADR-0075 to replace the260803 pin with certified release declarations. Amend wepp-run-input-contract.md for shared save/submission behavior and binary-lifecycle.md for metadata-only remint provenance. Shared controller, CSRF, rq-response, NoDb persistence, feature governance, prepared artifacts and binary/PASS contracts remain unchanged.

The discrepancy is an operator-authorized behavior change, not a bug against the old pinning contract. Existing stored capability axes accidentally serve as lifetime executable allowlists; the requested exception separates deployment availability from project geometry. Defaults remain260803. Scientific formulas, upload formats, native max32 OFEs, no-buffer policy, feature exclusions and backend/representation pairs do not change. Sidecars are operator-owned release declarations, not browser-supplied data. Missing declarations cannot be inferred from filenames. Both roles must agree; identity mismatch/malformed declarations fail before a new selection is persisted.

## Compatibility and regression plan

No config or manifest migration. New configs record sidecar-compatible tuples; old v1/v2/v3 graphs remain readable. Runtime choice changes only existing Wepp state, under existing locks. Current unavailable/undeclared legacy values remain visible and unchanged submissions preserve prior behavior, but are not eligible new choices. Test absent/present-empty/populated/legacy/malformed saved and metadata states separately from ordinary/MOFE/upload request combinations. Test live provider additions, metadata freshness, arbitrary/path-like IDs, malformed booleans and paired/hash mismatches; prove real261010 selection persists without config changes and reaches actual prepared/native output. Preserve current default and unknown-release behavior for legacy non-flattened runs.

## Native scope and security

The default branch is already checked out at /home/workdir/wepp-forest-release-20261009; the main checkout has unrelated dirty changes and is not touched. Extend its existing generator, add deterministic capability-refresh mode and tests, and remint four release sidecars while preserving all executable hashes/build/source/validation data. Vendor identical sidecars. No new binary build, native algorithm change or production operation is included.

Security impact high because public submission ultimately selects an executable. No new arbitrary path support, auth role, network destination, subprocess syntax or queue is added. Dedicated final security and correctness reviews are required, with direct real filesystem/persistence evidence. Invalid states must not block valid newly installed releases. Reader certification and MOFE output acceptance are gates before sidecars claim support.

## Required dispositions

Both independent read-only reviews approved. Correctness findings about contradictory MOFE pins and absent MOFE support were resolved; security rechecked the final geometry exception. Commit this accepted decision and current contract amendments as a standalone ancestor before implementation. Implementation conformance remains pending.
