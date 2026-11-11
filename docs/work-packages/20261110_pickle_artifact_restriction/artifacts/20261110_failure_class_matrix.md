# F2 failure-class assessment

**Status**: Locally implemented and validated; production rollout pending
**Broken shared assumption**: a project artifact is not safe to deserialize merely
because its Git blob lacks NUL bytes or its user is authorized to write/read it.

## Search Boundary

Reviewed Bootstrap Git admission, browse preview and capability metadata,
directory D-Tale links, the browse-to-D-Tale bridge, D-Tale eager-reader dispatch,
service documentation/type stubs, and focused tests. Repository searches also
identified internal pickle uses outside project artifact request paths.

## Consumer Matrix

| Consumer | Dependency path | Current state | Required evidence | Disposition |
| --- | --- | --- | --- | --- |
| Bootstrap pre-receive | path/blob -> NUL check -> accept | NUL-free pickle previously admitted | Real Git rejection/no log | Corrected; focused green receipts |
| Browse tabular preview | `.pkl` -> `pd.read_pickle` | Deserializes project file | 415 and zero-call spy | Corrected; focused green receipts |
| Browse preview metadata | supported suffix tuple | Advertises pickle preview | Metadata/listing test | Corrected; focused green receipts |
| Directory D-Tale link | suffix condition -> link | Advertises unsafe action | HTML absence test | Corrected; focused green receipts |
| Browse D-Tale bridge | path validation -> suffix admission -> materialize -> HTTP | Forwards both suffixes | Early 415/no downstream calls | Corrected; focused green receipts |
| D-Tale internal loader | `READERS` -> `_read_pickle` | Deserializes both suffixes | Direct 415/no registry entry | Corrected; focused green receipts |
| D-Tale type/docs | stub/README/AGENTS | Advertises reader | Source/docs check | Removed; source/stub checks pass |
| Raw authorized download | generic bytes | No deserialization | Byte equality | Preserved; byte/hash assertions pass |

## Variants

| Variant | Expected result | Evidence |
| --- | --- | --- |
| `.pkl` | Restricted | Focused regression passes |
| `.pickle` | Restricted | Focused regression passes |
| Mixed/upper case | Restricted | Focused regression passes |
| Nested allowed Bootstrap directory | Restricted | Focused regression passes |
| NUL-free protocol-shaped bytes | Restricted by suffix | Focused regression passes |
| Existing physical file | List/download only | Focused regression passes |
| Physical file under NoDir root | List/download only; preview 415 | Focused regression passes |
| Retired archive member | Existing retirement error; no materialization/forward | Focused regression passes |
| Whole retired archive | Download original archive bytes | Existing focused regression |
| CSV/TSV | Existing preview/D-Tale behavior | Focused regression passes |
| Feather/Arrow | Existing D-Tale behavior | Focused regression passes |
| Parquet variants | Existing lazy behavior | Focused regression passes |

## Explicit Exclusions

Redis session migration, RQ/process serialization, NoDb JSONPickle, shape-converter
worker payloads, and test-only pickle round trips do not consume project files
through the confirmed routes. They are excluded from this authorized failure
class, not certified globally safe. New evidence of project control requires a
separate assessment.

## Closure Rule

Every confirmed consumer and advertisement must be removed or reject before
deserialization/forwarding. Every control must have a named focused test. The
operator-approved focused matrix is sufficient; a full-suite pass is neither
required nor a substitute for these direct checks.

Merge/ref-adoption peer: default Git merge display and reachable-commit exclusion
missed legacy branch imports. `test_merge_from_existing_remote_branch_admission`
covers both parent orders, fast-forward adoption, unchanged inherited pickle and
allowed text controls; suffix-only baseline comparison closes this peer.
