# Correctness Review — WMesque Catalog Synchronization

Status: reviewed implementation fixes approved; M5 evidence tracked separately.
Reviewer: independent reviewer agent (`contract_correctness`). Date: 2026-10-14 UTC.
Scope: client priority/deadlines, catalog publication, scheduler/RQ wiring,
compatibility, provenance, and tests. Contract checkpoint: `193df8b8c`.

## Findings and Disposition

| ID | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| COR-I01 | Medium | Corrupt managed state returned nonretryable 400 | Resolved: invalid input remains 400; catalog/manifest faults become 500; regression |
| COR-I02 | Medium | Trickling headers could consume fallback budget | Resolved: per-read deadline transport covers headers and body; real-server regression |
| COR-I03 | Low | Server stubs and EDDE actual-source summary incomplete | Resolved: stubs updated; additive per-variable endpoint/revision maps and regression |
| COR-I04 | Medium | Query enum documentation did not validate processing options, so invalid requests could become retryable 500 | Resolved: early option membership checks return 400 before source IO; three API regressions |

No unresolved medium/high correctness finding in reviewed fixes. Reviewer also
independently verified default HTTPS acquisition of an actual NLCD GeoTIFF from
wepp.cloud (3 by 4 pixels, value 42). Name resolution and connection/TLS setup are
not a universal wall-clock guarantee; documentation states this limitation.
Final re-review approved COR-I04 closure, GDAL conversion exit-code checking,
and explicit model-success assertions in the reproducible acceptance scripts.

## Valid States and Evidence

Absent managed catalog retains legacy behavior; empty catalog is valid; populated
catalog resolves verified immutable revisions. Explicit empty endpoint list and
malformed URLs fail before IO. Hostile references and symlinks fail without
publication. Supported legacy clients retain logical catalog paths. Expected
revision mismatch and availability failures move to the next configured endpoint;
invalid request/auth and local IO failures do not.

Real fixture tests read all output pixels and exercise automatic adoption,
unchanged local extensions, concurrent publisher/sync merge, prior-release reads,
corrupt copy recovery, timeout and format behavior. Real forest scheduler/RQ
receipts and downstream project evidence are recorded in the acceptance artifact,
not inferred from passing unit tests.

## Completion Limits

Implementation review approval does not establish production deployment. M5
requires actual interruption and project prepared-input/output readback. The
initial corruption script alone did not prove process-death recovery; a separate
real-copy interruption script was added. The reviewer confirmed that retained
SIGKILL/retry and downstream rebuilt-soil/climate/WEPP/report evidence closes
those M5 gaps. M6–M8 remain outstanding.
