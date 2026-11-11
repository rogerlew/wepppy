# Security review - Pickle artifact restriction

## Metadata

- **Package**: `docs/work-packages/20261110_pickle_artifact_restriction/`
- **Reviewer**: independent `security_reviewer`, `/root/contract_review_two`.
- **Date**: 2026-11-11 04:17 UTC.
- **Scope reviewed**: local production/test diff after contract checkpoint
  `aeab3c3e1` and compatibility clarification `e2b9f6b35`; no production rollout.
- **Related artifacts**: [decision](20261110_contract_decision.md),
  [failure-class matrix](20261110_failure_class_matrix.md),
  [correctness review](20261110_correctness_review.md).

## Findings

| ID | Severity | Exploit path and evidence | Required action | Status |
| --- | --- | --- | --- | --- |
| SEC-F2 | High | Project pickle previously reached browse `pd.read_pickle` and D-Tale `_read_pickle` | Remove both readers and dispatch entries; reject interactive requests | Closed locally: source search and zero-call tests |
| SEC-F2A | Medium | Preview tuples, directory D-Tale links, bridge, docs and stub advertised unsafe support | Remove positive capabilities consistently | Closed locally: metadata/HTML tests and source/docs review |
| SEC-F2B | Medium | Bridge materialized files before checking supported suffixes | Reject after access/existence checks and before materialization/HTTP | Closed locally: guard ordering and zero-call bridge tests |
| SEC-F2C | Medium | Existing reachable legacy Git branch can merge a pickle into main without path admission: `_diff_commit_paths` uses combined `git show --name-status`, which omits files differing from only one parent | Compare final tip and introduced commits with receiving ref baseline using suffix-only admission, independent of merge parent order and object reachability | Closed locally: six hostile and three supported real-push variants pass |

SEC-F2C reproduction used a disposable Git repository, with a preexisting
`legacy` branch containing inert `wepp/runs/legacy.pkl`, and a diverged `main`
with an allowed text file. Merging `legacy` into `main` gave empty output from
`git show --pretty=format: --name-status -z HEAD`, while
`git diff --name-status HEAD^1 HEAD` returned
`A wepp/runs/legacy.pkl`. Existing remote-reachable branch commits are excluded
by `_list_introduced_commits(... --not --all)`, leaving only the empty merge diff.
No pickle was deserialized. Reader removal still blocks server execution, but
the new admission contract requires rejection of introduced pickle paths.

The final fix adds `_validate_pickle_changes`: each ref update checks its tip
and introduced commits against its previous tip (main for a new ref), before
shared visited-commit skipping. `git diff --no-renames --diff-filter=AMT` finds
added, modified and type-changed paths without hiding renamed destinations.
Only pickle suffix admission runs on this additional inventory; ordinary
merge/parser behavior remains unchanged. Final-tip checks also cover a
fast-forward to already reachable objects, where there are no new commits to
inspect. Existing unchanged pickle content in the receiving baseline remains
valid. [Expanded red evidence](red-merge-expanded.log) had six denied-case
failures and three allowed text passes; the final Bootstrap gate passes all
27 tests, including both parent orders, fast-forward and inherited legacy files.

## Security Triage and Scope

Security impact is high because project write authority previously allowed
Python deserialization inside browse/D-Tale request processes. A legitimate
Bootstrap writer is not trusted with server code execution, and NUL absence is
not proof that a serialized object is safe. Existing artifacts may be hostile.
Authorized raw byte delivery does not deserialize their contents.

This review covers Bootstrap admission, browse preview and capability metadata,
directory links, the D-Tale bridge, loader, registry and stub. Internal RQ,
NoDb, session serialization, migration utilities and shape-converter worker
payloads are outside this bounded route remediation; they are not certified
safe globally. No new dependency, scanner, migration, auth or topology change
was introduced.

## Surface Evidence

- Bootstrap lowercases `Path.suffix` in shared `_validate_path` before mode,
  size, blob reads, parser pooling and push logging. Real temporary pushes
  reject `.pkl`, `.pickle`, `.PkL` and `.PiCkLe` under both allowed prefixes,
  retain the receiving ref and create no push log. The additional suffix-only
  ref/commit inventory closes the inherited merge/reachable-ref gap above.
- Browse rejects normal and representation previews before content reading.
  Raw/download modes stream original bytes. Existing authentication, sensitive
  path and containment checks precede the file renderer; missing paths retain
  their ordinary responses.
- Preview metadata and directory D-Tale links no longer advertise either
  suffix. The request-time `read_pickle` source search is empty in both service
  trees and Bootstrap.
- The bridge's existing supported-suffix authority excludes both pickle
  extensions. It runs after authorization/containment/existence checks and
  before materialization or HTTP. Retired archive traversal retains its prior
  409/404 behavior; whole archives remain downloadable. No archive support was
  restored.
- Direct D-Tale load verifies token and payload/path conditions first, then
  denies pickle before source fingerprinting, maps, cached dataset reuse or
  reader dispatch. `_read_pickle`, both registry entries and its stub are gone.
  `_load_dataframe` independently returns unsupported-media for either suffix.
- Errors contain an actionable format restriction, a submitted relative Git
  path, or the unsupported suffix; no content or credentials are exposed by
  the new messages.

## Validation Evidence

Reviewed retained Docker-wrapper transcripts:

- [Bootstrap](green-bootstrap.log): 27 passed, including real rejected pushes,
  merge/ref adoption variants, unchanged inherited pickle and allowed
  text/slope/parser/logging controls.
- [Browse/files](green-browse.log): 130 passed, including real physical file
  readback under ordinary and NoDir roots, metadata/links, previews,
  authorization/path controls and byte-equal raw/download responses.
- [D-Tale](green-dtale.log): 48 passed, including zero reader/fingerprint/HTTP
  call assertions, eager CSV/TSV/Feather/Arrow controls and lazy Parquet controls.
- [Test stub hygiene](test-stubs.log): passed.
- [D-Tale stubtest](stubtest.log): two modules passed. The stub also now matches
  existing runtime metadata fields and private-response keyword arguments; those
  synchronization edits do not change runtime authorization.

The payload used for raw readback includes CRLF, NUL and non-UTF-8 bytes; tests
compare exact content and SHA-256. Tests never execute a malicious pickle.
The full Python and frontend suites were intentionally waived by the operator;
these focused results do not imply a broad-suite or production pass.

## Verdict

- **Gate status**: pass for local implementation.
- **Unresolved findings**: High 0; Medium 0; Low 0.
- **Highest supported claim**: bounded pickle artifact restriction implemented
  and locally validated, including the discovered Bootstrap merge/ref gap.
- **Production evidence**: none; rollout requires separate authorization and
  retained scoped service receipts.

## Residual Risk and Recovery

Suffix restriction is not content detection. Pickle bytes renamed to another
extension are not identified, but no remaining scoped reader selects Python
pickle deserialization. Authorized clients may download and deserialize files
on their own machines; that trust decision remains outside the server boundary.
Rollback must retain equivalent Bootstrap and interactive-reader restrictions;
no flag or fallback may silently re-enable pickle loading.

## Sign-off

Independent security review approves current source and focused evidence after
rechecking SEC-F2C closure and receiving final correctness and QA reapproval
(2026-11-11 04:17 UTC). Separately authorized deployment remains an independent
gate; no production or global serialization safety claim is made.
