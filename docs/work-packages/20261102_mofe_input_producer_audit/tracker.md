# MOFE input producer audit tracker

**Started:** 2026-11-02 19:32 UTC.
**Phase:** Approved M2/M3 producer implementation; M4 producer validation and final review. Native acceptance HOLD.
**Contract ancestor:** `4579b11ce` (before production edits).
**Paired Rust commit:** `5e3540f684c8606f4140afcd72ed5a21df5ab85f`, pushed and verified on upstream main.

## Task board

- [x] Reconcile four requested read-only audit lanes and S01/NATIVE-03.
- [x] Renew failing producer baselines and pass two independent contract reviews.
- [x] User ratified MIPA-01: “approved. proceed”; commit standalone checkpoint.
- [x] M2: complete crop discovery, deterministic safe aliases and per-OFE Disturbed lookup.
- [x] M3: calendars/residue references, soil overrides/textures, numeric cover order, Rust slope/map validation.
- [x] Confirm stale deck counts and nested soil-stack risks; add narrow guards and actual-file tests.
- [x] Preserve linked source files, failed publication evidence and archive/restore identity.
- [x] Reconcile secondary synthesis provenance and distinct plant-definition review findings.
- [x] Copied actual-project producer preparation: 72 hillslopes, 235 elements; matching counts, year/crop lookup and repeat bytes; original unchanged.
- [x] Final correctness, QA and security reviews pass with no unresolved source findings.
- [ ] Final extended-test and benchmark-refresh disposition.
- [ ] Full M4 native acceptance: NATIVE-01/02/03, 9005 consumer, fresh outputs/reports.

## Decisions and evidence

The [execution report](artifacts/20261102_producer_execution.md) records repaired
boundaries, exact commands/results and residual acceptance limits. The
[approved checkpoint](artifacts/20261102_contract_decision.md) and
[canonical contract](../../schemas/mofe-input-identity-contract.md) preserve
normative behavior and rationale. The [active ExecPlan](prompts/active/implementation_execplan.md)
remains open for native acceptance.

No new coefficients, defaults, fallback policies or native capacity limits were
introduced. No-N landuse synthesis preserves the complete reusable common period;
explicit `sim_years=N` avoids materializing large periods. Crop provenance follows
scenario copies/renames; physical plant identity remains separate from original
coefficient-mapping keys. Safe ordinary native decks retain their bytes.

Supported forks were used. Calm-amalgamation lacks required MOFE soil files;
awake-versatility supplied the complete copied-project case. The first readback
script had an attribute typo after successful preparation; its failed log is
retained. Subsequent readback succeeds. Final v3 receipts also follow a clean guarded
multiprocessing probe; earlier bootstrap-error logs remain retained. Actual-project PMET values are uniform;
the separate Disturbed fixture supplies discriminating pairs/textures/classes.

Security review covers symlinks, hardlinks, visible failed attempts and canonical
archive/restore. Correctness and QA reviews are separate from native acceptance.
The installed Rust release extensions were not replaced. Existing projects and
unrelated dirty work were preserved; no branch switch or deployment occurred.

## Validation and next handoff

Focused management/soil/Disturbed/RAP/staging/archive checks pass on interim
snapshots (295, then 304 tests); final-source checks are recorded in the execution
report. Stubtest and test-stub checks pass; broad-exception count has no increase.
Rust tests pass 4 slope cases and 5 map cases, plus direct candidate-binding
readback. Scoped source changes are published upstream.

Full pytest stopped after 485 passes at the historical Disturbed report's pinned
management-source hash. The source changed; do not merely update its provenance
hash to claim refreshed benchmark execution. A continuation excluding that known
pin and already-executed native matrix found a placeholder slope fixture; replace
it with a real matching five-OFE deck and rerun affected tests. The final fresh benchmark passes 99 tests and reproduces all 768 outputs exactly;
report/provenance and 16 report/Usersum checks now pass. Full clean-suite status
must still be reported honestly, including any remaining failures.

Complete producer review/validation disposition before handoff. Native repairs,
selected-binary capacity/adapter checks, FC/HK ownership repair, 9005 readback,
fresh native histories and report refresh remain the next bounded work. Deployment
and existing-project regeneration require their own authorization; this package
must not claim unrestricted heterogeneous native correctness.
