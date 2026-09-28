# Watershed runtime budget

Status: active. Owner: Codex. Amendment: WRT-01.

Implement the operator-approved years × hillslopes timeout in all four continuous
watershed submission paths, preserving unrelated stages and no-prep inputs.
Complexity budget: one bounded policy helper and additive child RQ metadata;
no infrastructure, dependencies, model-input changes or process-control changes.
Security impact: low; longer authorized worker occupancy and bounded parsing of
already-authorized prepared inputs. Independent contract and final correctness
reviews required; include security/noninterference review of admission bounds.

Acceptance: 27-hour persisted budget for 1,000 years × 1,908 hillslopes; 12-hour floor;
rounding boundaries; single-storm unchanged; all four graph paths; no partial
children on invalid workload; fork metadata retained; real Redis serialized
timeout/metadata and live job-tree evidence. Deployment is separate.
