# Contract decision checkpoint

Starting implementation revision: 29a18e00f. Recorded 2026-09-11 UTC.
Classification: owner-requested intended UI/NoDb/RQ behavior change, not a
conformance fix. Operator authority is the conversation request for both-model
UI/task wiring and the subsequent exact decisions recorded in model_selection.md.

Normative delta: header/table/model radios; M1-only dNBR/K, M3-only Soils;
10 m ned13/2022 M3 source; additive model state/attempt/result identity and run
endpoint; real dedicated M3 task with honest integration_pending failure until
scientific composition; retain auto-enabled mods and all observable artifacts.
No scientific calculation change in this wiring checkpoint. ADR-0066 records
the accepted masking direction for the later numerical checkpoint.

Applicable canonical contracts: module specification.md, docs/model_selection.md,
docs/production_m1.md; docs/ui-docs/contracts/postfire-debris-flow-control-contract.md;
docs/ui-docs/controller-contract.md; docs/schemas/rq-response-contract.md,
weppcloud-csrf-contract.md, nodb-persistence-concurrency-contract.md;
docs/standards/artifact-observability-standard.md; feature-registry specification
and YAML (unchanged automatic dependencies); ADR-0066 and prior scientific ADRs
for unchanged coefficients/tool behavior. Module doc links distinguish pending
scientific changes from current local engine behavior.

Compatibility/regression plan is in package.md and active ExecPlan. Valid states:
absent/empty default M1, legacy M1 records, populated M1/M3 selections, active
jobs and different selected model, failed M3 receipt and retained prior result,
read-only/disconnected state. Malformed model, hostile JSON and unauthorized
requests fail at existing boundaries; missing prerequisite is expected 422.
M3 integration_pending is deliberate scaffold task failure with persistent
explicit error; it must not suppress the UI Run action by implementation status.

Security impact high: new dispatch admission/identity/freshness. Preserve auth,
containment, bounded inputs, locks and worker handoff. No general file path input,
new queue/service or migration. Evidence must include real NoDb/filesystem,
browser/RQ identity and observable retained diagnostics.

Review disposition: accepted by both independent reviewers; see contract_reviews.md.
Standalone checkpoint revision: being committed with explicit owner authority. No runtime edits
until the required reviewed ancestor exists. Owner explicitly granted commit authority with “authority is granted” on
2026-09-11.


Preflight scope: amend module preflight.py and Go checklist projection with the
canonical production_m1.md “Preflight completion task” policy. 🌋 reflects the
latest accepted result's own model/frequency; selection alone never invalidates
it. Validate both relevant and unrelated model dependency changes with Python
and `wctl run-preflight-tests` Go tests, plus actual development stream readback.
