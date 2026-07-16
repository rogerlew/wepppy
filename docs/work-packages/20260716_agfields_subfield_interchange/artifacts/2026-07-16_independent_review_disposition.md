# Independent review disposition

Two independent review passes examined the native regression boundary, WEPPpy
publication/state contract, RQ ordering, and downstream Features Export use.
Every high- or medium-severity finding was resolved before forest restart.

## Findings and dispositions

| Severity | Finding | Disposition and regression evidence |
| --- | --- | --- |
| High | Raw WEPP freshness could make stage 4 appear complete after interchange failed. | Accepted. Added a separate persisted interchange completion signature, invalidated it before raw execution/clear, set it only after deep bundle validation, and required it in rq-engine state. Failure tests retain a prior bundle and prove no terminal success. |
| High | Features Export could read a retained stale bundle after its completion marker or mapping was invalidated. | Accepted. Added a detached, read-only `ag_fields_metrics` readiness gate before dependency/cache planning. Tests cover a cleared marker, changed mapping hash, incompatible major version, current success, and byte-for-byte no-mutation snapshots. |
| Medium | Completion validation permitted zero-row metadata for families the publisher never permits to be rowless. | Accepted. Only EBE may declare zero-row sources. Parameterized PASS/ELEMENT/LOSS/SOIL/WAT rejection tests now align completion and publication contracts. |
| Medium | Requiring all EBE identities to have output rows would invent scientific measurements for valid header-only reports. | Accepted. The manifest records the 111 independently classified header-only forest EBE sources; every other family requires row-bearing identity. |
| Medium | Pairwise PASS/WAT joins on identity would multiply temporal rows, and a field-level metric layer needs scientifically defined aggregation. | Accepted. The supported sub-field metrics layer uses geometry plus PASS joined by `sub_field_id`; WAT is excluded. The existing draft field layer ID is retained unchanged for compatibility pending an explicit area/volume aggregation contract. |
| Medium | Reopening six very large Parquet footers on every state poll would add multi-second latency. | Accepted. Completion publication performs one deep schema/footer validation; subsequent state checks validate signatures, manifest invariants, mapping hash, and file sizes without reopening all data files. |

## Final review status

The final code reviewer and QA reviewer reported no unresolved high-severity
findings after the fixes above. Their focused final runs passed the four
Features Export readiness cases, seven adjacent selection cases, seven
completion-validation cases, and the 54-test interchange/backend set. The
combined cross-layer run subsequently passed 191 tests.

Residual risk remains **low-medium**, principally because a paired native ABI
and multi-gigabyte generated bundle are shared by several long-lived process
types. Dedicated additive APIs, exact ordinary golden parity, atomic bundle
publication, importer SHA/signature verification, authenticated RQ acceptance,
and the documented paired rollback keep that risk bounded.
