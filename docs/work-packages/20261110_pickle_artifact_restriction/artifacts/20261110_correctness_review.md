# Correctness and user-experience review - Pickle artifact restriction

## Metadata

- **Reviewer**: independent `contract_review_one` / reviewer agent.
- **Reviewed**: initial 2026-11-11 04:12 UTC; reopened 04:15 UTC for the
  independently reproduced Bootstrap merge gap; renewed approval 04:17 UTC.
- **Base revision**: `991fc5e2c3f1cd2e5d74169e2d7bccb609203924`.
- **Contract ancestor**: `aeab3c3e187ef54d7cfa6f3e149b465fdc1ac7d8`
  (2026-11-11 04:08 UTC).
- **Compatibility clarification ancestor**:
  `e2b9f6b355bc7fa5390813d7a1eaa1271a3403e4`
  (2026-11-11 04:10 UTC).
- **Scope**: working-tree source/test changes following those checkpoints in
  Bootstrap pre-receive, browse preview/metadata/listing/bridge, and D-Tale
  loader/reader/stub. Unrelated working-tree edits are excluded.
- **Related security artifact**: [security review](20261110_security_review.md).

The original checkpoint precedes regression tests; the supplemental checkpoint
preserves existing archive retirement behavior and precedes production edits.
Both received independent read-only reviews. This review inspected the actual
source/test diff, surrounding dispatch and access-check ordering, current
contracts, and the retained focused test logs. The reviewer did not independently
rerun the suites or change production code.

## User outcome and error policy

Bootstrap reports `Pickle files are not allowed: <path>` for added/modified
`.pkl` and `.pickle` paths in either letter case. Rejected pushes neither advance
the receiving ref nor append the push log. Existing input validation remains.

Existing files remain visible in listings and downloadable as exact bytes.
Metadata reports no preview, directory listings omit D-Tale actions, and direct
preview/representation requests return 415 with an instruction to download the
original file. Raw query/header modes and direct download remain available.
Browse-to-D-Tale and internal D-Tale loading reject pickle without readers or
loader side effects. These are expected unsupported-format outcomes under
[browse filesystem contract, Pickle artifacts](../../../schemas/browse-filesystem-contract.md#pickle-artifacts).

Authentication, authorization, path validation and missing-target checks remain
before the new request rejection. No auth policy is changed. Retired archive
member access retains its existing 409/404 semantics, and whole archives remain
downloadable. An absent optional archive viewer is not restored by this change.
Supported-format parse failures retain their existing behavior.

## Valid-state and input matrix

| State/input | Expected outcome | Evidence and result |
| --- | --- | --- |
| New nested Bootstrap path, both prefixes, both suffixes and mixed case | Reject push without ref/log publication | `test_pickle_push_rejected_without_ref_or_log`: eight real Git pushes pass |
| Existing receiver legacy branch adopted through either merge-parent ordering or fast-forward | Reject pickle adoption; allow ordinary text control | `test_merge_from_existing_remote_branch_admission`: six rejected pickle pushes and three accepted text controls pass |
| Existing inert protocol-shaped pickle bytes | Preview/repr 415, zero pickle reads | `test_pickle_preview_rejected`: eight variants pass |
| Existing arbitrary binary pickle bytes, root or physical NoDir root | Visible file, preview false, 415 preview, exact raw/download bytes | `test_pickle_legacy_metadata_and_bytes`: eight variants pass |
| Physical pickle D-Tale request, both suffixes and mixed case | 415 before materialization/HTTP | `test_pickle_bridge_rejects_before_downstream_work`: physical variants pass |
| Retired archive-only NoDir root | Existing 409 without materialization/HTTP | Same bridge test: archived variants pass |
| Explicit retired archive path/member | Whole-file bytes available; no virtual traversal | `test_retired_archives_are_physical_files_without_virtual_traversal` and `test_dtale_does_not_traverse_opaque_archive` pass |
| Direct D-Tale pickle loader/reader dispatch | 415 before fingerprint or pickle reader; registry has no entries | `test_pickle_loader_rejects_before_fingerprint_or_dispatch`: four variants pass |
| Allowed Bootstrap input | Existing parser and push logging work | `test_pre_receive_logs_push_for_multi_ofe_slp` and introduced-commit controls pass |
| CSV/TSV/Feather/Arrow | Internal loader succeeds and table values/dtypes match | `test_supported_eager_reader_control`: four real-file controls pass |
| Parquet/GeoParquet | Browse preview, bridge and lazy pages still work | Existing preview/filter, redirect, lazy registration/grid and freshness controls pass |
| Missing files | Normal not-found response | Existing browse/files not-found tests pass; source review confirms suffix checks follow target existence checks |
| Denied traversal/symlink/sensitive paths | Existing rejection retained | Existing files-route negative controls pass; guards precede new format checks |
| Empty pickle file | Same format rejection without reading content | Source ordering establishes content independence; no separate empty-file case was run |

The input cases use inert bytes only. No executable pickle was deserialized.
The local route fixtures supply authorized contexts; they do not establish live
identity/session/proxy behavior. No representative-user comprehension study was
performed or claimed.

## Artifact evidence chain

| Stage | Verified semantics | Evidence |
| --- | --- | --- |
| Git request/process boundary | Actual installed temporary hook rejects a real push | Real temporary source and bare repositories with child-process hook |
| Git persisted state | Receiver stays at baseline; rejected push has no log | Ref and push-log readback in Bootstrap test |
| Filesystem listing | Existing file appears without D-Tale action | Rendered directory HTML and file metadata response |
| Request dispatch | No pickle reader, materializer or HTTP forwarder | Call sentinels plus source ordering; internal load also avoids fingerprint work |
| Byte delivery | Source and response payloads match exactly | Byte equality and SHA-256 equality for direct download, browse download, raw query and Raw header |
| Supported data consumer | Table values and existing lazy generations remain valid | Actual eager file readers and existing Parquet/D-Tale grid tests |

No migration, conversion, archive writer or artifact deletion is introduced.
The failure-class scope and exclusions remain those in
[the failure-class matrix](20261110_failure_class_matrix.md).

## Focused validation receipts

- [Bootstrap log](green-bootstrap.log): **27 passed**, 4 warnings; supersedes the
  initial 18-test receipt after adding merge/ref-adoption cases.
- [Browse/files log](green-browse.log): **130 passed**, 13 warnings.
- [D-Tale bridge/loader log](green-dtale.log): **48 passed**, 6 warnings.

The first D-Tale control run exposed a test expectation mismatch: existing eager
postprocessing uses nullable `Int64`, while the new expected frame used `int64`.
The expected frame now uses `convert_dtypes()`; runtime reader behavior was not
changed to satisfy the test. The corrected focused gate passes.

Security review subsequently found that Git's default merge display omits paths
adopted from an existing receiver branch, and introduced-commit enumeration omits
fast-forwards to already reachable commits. The expanded regression produced
six forbidden pushes that unexpectedly succeeded, while three ordinary-text
controls passed; see [expanded red evidence](red-merge-expanded.log). The
correction compares the receiving ref baseline with its new tip and each
introduced intermediate commit, checking only added/modified/type-changed pickle
paths with rename detection disabled. Other merge path/parser validation remains
unchanged. This also handles reversed merge-parent order without depending on a
first-parent-only diff. Each new ref-adoption case includes an unchanged
`inherited.pkl` baseline file; the three successful text controls demonstrate
that legacy presence alone does not block an otherwise allowed merge or update.

The touched D-Tale stub was aligned with existing `DatasetMeta` fields and
`_build_instance_response` keyword arguments after the prescribed stub gate
exposed preexisting drift. Source comparison confirms those declarations match
runtime behavior; no access or dataset behavior changed. The rerun
[stubtest receipt](stubtest.log) reports no issues in two modules.

The operator explicitly waived the full Python and frontend suites. None was
required or counted as evidence here. Stub, documentation and security gates
remain separately owned and are not inferred from these pytest results.

## Findings and disposition

| ID | Severity | Concern | Disposition |
| --- | --- | --- | --- |
| COR-F2 | Medium | A broad restriction could hide or alter legacy files | Closed: real listing/metadata and four byte-delivery modes pass for both suffixes/cases, including physical NoDir roots |
| COR-F2A | Medium | Shared suffix edits could regress supported tables | Closed: real CSV/TSV/Feather/Arrow loader/readback controls and existing Parquet preview/grid/freshness controls pass |
| COR-F2B | Low | Initial eager control expected the wrong existing dtype | Closed: expected nullable dtypes corrected and focused D-Tale gate rerun green |
| COR-F2C | High | Merge/ref adoption bypassed per-commit pickle admission | Closed: suffix-only receiving-baseline checks reviewed; six real negative pushes and three allowed controls pass in the 27-test Bootstrap rerun |

No additional implementation correctness or UX blocker was found. The change
removes unsafe actions without deleting legacy artifacts or modifying unrelated
supported reader behavior. The preview error supplies a usable recovery action;
this is a source/response review, not a usability-study claim.

## Verdict and limits

**Approve local implementation correctness, renewed after merge/ref-adoption
correction.** Unresolved findings: High 0, Medium 0, Low 0. Final focused evidence
is 27 Bootstrap, 130 browse/files and 48 D-Tale tests: **205 passed**. The initial
approval and 18-test Bootstrap receipt are superseded by the reviewed bounded
fix, real positive/negative merge controls, and green rerun. Highest supported
claim: implemented and locally validated across the focused matrix, pending the
remaining independent gates.

Production rollout, real service identity/mount/proxy parity, scoped production
smoke, and deployment receipt remain pending separate authorization. This
review does not claim deployment or incident resolution. Rollback must retain
an equivalent restriction and must not restore request-time pickle loading.
