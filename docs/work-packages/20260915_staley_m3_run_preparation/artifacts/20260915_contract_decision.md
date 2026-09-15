# M3-RUN-01 contract decision — 2026-09-15

Starting implementation: e8edf2030. Operator authorization: “fix please with
units tests and rerun overpriced-sprawl”, following diagnosis of absent prepared
sources. Prior bounded acquisition authorization remains applicable; no Redis
credential rotation or production deployment is requested.

## Authority and exact delta

Amend module specification, production_m3.md, production_m3_runtime.md and the
postfire-debris-flow-control-contract.md. Retain NoDb persistence/concurrency,
RQ response, CSRF, source containment and scientific ADR contracts unchanged.
Discrepancy: missing user workflow, requiring an intended orchestration change,
not a change to scientific equations or soil builder policy.

An explicit Run M3 on an eligible basin with absent module soil_sources.json
acquires the existing bounded SDA lineage and original THICK window, activates
the verified receipt and continues calculation in the same job. Preflight,
state readers, M1 and numerical adapters never acquire. Existing valid populated
or present-empty pointers are reused; malformed metadata fails. Genuine prepared
zero coverage remains an explicit unavailable result. This avoids repeated
acquisition for intentionally empty or geographically unsupported sources.

Authority is checked before acquisition and again inside locked promotion.
After promotion only this attempt's source-pointer inventory may be rebased;
all other project inputs, raw cache/WAL state, model/frequency and attempt
identity must match. Pin the promoted pointer to the receipt's candidate hash.
Do not hold NoDb locks over network requests. Preserve retained failure evidence
and previous accepted results; a valid pointer may survive later run failure.

## Compatibility and regression plan

No endpoint, queue graph, pointer schema, scientific formula, unit or generated
WEPP input changes. Reuse schema-v1 pointers, including supported empty legacy
objects. Add only optional attempt source-preparation provenance. Snapshot rebasing
must not bless unrelated source changes. Hash soils, RUSLE and generated
wepp/runs inputs before/after the live run.

| Runtime state | Expected behavior / evidence |
| --- | --- |
| Never used / absent pointer | Acquire once, real locked activation, current numerical results |
| Present-empty / legacy schema-v1 | No network; explicit unavailable support retained |
| Populated | Reuse; no acquisition on rerun |
| Malformed/hostile | Explicit failure, no network/path escape or publication |
| Acquisition failure | Retained diagnostics, no new accepted result |
| Concurrent attempt/project/cache change | Refuse activation or snapshot rebasing/publication |
| Valid promotion then calculation failure | Preserve previous result, reuse pointer on retry |

Security impact: high because an authenticated Run now invokes existing outbound
reader in its worker. No new URL/payload surface; unchanged allowlisted endpoints,
byte/request/process budgets, redirect prohibition, containment and atomic promotion.
Required: two independent read-only contract reviews, dedicated final security
artifact, real filesystem/persistence boundary tests (only remote delivery mocked),
targeted and full Python tests, live normal browser/RQ run under worker identity.
