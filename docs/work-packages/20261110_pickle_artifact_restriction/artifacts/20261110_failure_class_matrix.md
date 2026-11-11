# F2 failure-class assessment

**Status**: Initial bounded assessment; validation dispositions pending  
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
| Bootstrap pre-receive | path/blob -> NUL check -> accept | NUL-free pickle admitted | Real Git rejection/no log | Confirmed defect |
| Browse tabular preview | `.pkl` -> `pd.read_pickle` | Deserializes project file | 415 and zero-call spy | Confirmed defect |
| Browse preview metadata | supported suffix tuple | Advertises pickle preview | Metadata/listing test | Confirmed defect |
| Directory D-Tale link | suffix condition -> link | Advertises unsafe action | HTML absence test | Confirmed defect |
| Browse D-Tale bridge | suffix allowlist -> materialize -> HTTP | Forwards both suffixes | Early 415/no downstream calls | Confirmed defect |
| D-Tale internal loader | `READERS` -> `_read_pickle` | Deserializes both suffixes | Direct 415/no registry entry | Confirmed defect |
| D-Tale type/docs | stub/README/AGENTS | Advertises reader | Source/docs check | Confirmed peer |
| Raw authorized download | generic bytes | No deserialization | Byte equality | Preserve |

## Variants

| Variant | Expected result | Evidence |
| --- | --- | --- |
| `.pkl` | Restricted | Pending |
| `.pickle` | Restricted | Pending |
| Mixed/upper case | Restricted | Pending |
| Nested allowed Bootstrap directory | Restricted | Pending |
| NUL-free protocol-shaped bytes | Restricted by suffix | Pending |
| Existing physical file | List/download only | Pending |
| Existing NoDir/archive member | List/download only; no materialized D-Tale | Pending |
| CSV/TSV | Existing preview/D-Tale behavior | Pending |
| Feather/Arrow | Existing D-Tale behavior | Pending |
| Parquet variants | Existing lazy behavior | Pending |

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
