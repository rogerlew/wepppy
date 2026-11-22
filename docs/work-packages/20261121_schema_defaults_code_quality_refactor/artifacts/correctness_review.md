# Discovery correctness review

An independent source reviewer compared the production candidate 254ed7b78 with c82da0a94. The applicable public contracts are the [agent API](../../../schemas/rq-engine-agent-api-contract.md), [controller state](../../../schemas/rq-controller-state-contract.md) and [RQ response](../../../schemas/rq-response-contract.md) specifications.

## Admission and errors

All ten decorators, endpoint signatures and post-admission response and exception blocks match the baseline syntax trees. The shared admission helper checks JWT, accepted scope and run access before loading any controller. Unknown runs and configuration mismatches return 404. Invalid authority returns its diagnostic 409, and registry unavailability retains 503 with Retry-After. Existing HTTP boundaries translate unexpected authentication or controller failures into canonical 401 or 500 envelopes and log the cause. Keeping those catches preserves client-visible error handling. Consolidation removed 18 duplicated broad catches. Optional feature-export discovery retains one logged best-effort boundary so a backend failure still permits an outputs inventory.

## Discovery and artifact cases

The reviewer inspected all 41 operation documents, the distinct result and schema lists, SBS/RUSLE availability, case-insensitive ordering and the final operation count. The session route can still access the loader and its configuration error, and archived artifact probes can still import the digest helper.

The focused HTTP tests cover empty and populated output inventories, legacy job records, file digest changes, authorization denial, unknown resources and registry failures. The discovery probe exercises the registered app with fixed runtime snapshots. Its generated JSON is evidence for serialization and client-visible response content. The snapshot setup and job index are fixtures. This read-only refactor changes neither persistence nor queue wiring.

## Verdict

The independent source review found no required changes. The validation tracker records separate execution results.
