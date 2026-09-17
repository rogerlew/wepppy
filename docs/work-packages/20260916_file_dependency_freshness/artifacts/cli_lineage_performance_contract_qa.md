# CLI lineage performance-contract correction: independent QA ratification

**Ratified:** replace the prototype-derived local mean component budgets of
5 ms settled / 40 ms cold-or-evicted with **10 ms settled / 50 ms cold-or-evicted**,
for the retained 46-year/1.18-MB and 120-year/3.11-MB CLI workloads on warm local
NFS. Keep full export <=1.5 seconds for the 120-year case and added lineage export
cost <=200 ms. Final implemented measurement must satisfy these corrected budgets;
ratifying the correction alone is not a passing performance test.

This is an explicit correction, not a claim that the original gate passed.
`cli_lineage_implementation_performance_final.json/.log` preserves the original
actual failures: 8.28/10.78 ms settled and 43.85 ms mean eviction for the large
case. The original 5/40 gate and CLI-QA-P01 remain recorded as failed history.
The canonical contract and decision record must name this correction and link
the measured rationale before the implementation is accepted.

## Why the correction is defensible

The original prototype measured coherent footer parsing, comparison and a generic
verified digest. It omitted the production reader's mandatory component-by-component
directory opens. Profiling the actual implementation showed 14 open calls per
check, with 46–49% of profiled runtime spent opening directories/files on the
measured NFS mount. It was therefore an incomplete basis for the 5-ms budget.
The output remained correct and settled reads consumed zero CLI payload bytes;
the issue was observed latency, not hidden repeated scientific work.

A bounded optimization was implemented and measured before revising the budget.
Same-call parent descriptor reuse reduces opens from 14 to 8 and settled predicate
means from 7.60/9.72 ms in the unwrapped original profile to **5.82/6.98 ms**.
Each request still traverses and holds its own no-follow parent, verifies parent
and leaf associations, opens leaves for actual access, and closes its descriptors.
Security's independent nine-case probe verifies parent replacement, denied
directory/leaf access, symlinks and descriptor cleanup. No cross-request descriptor
cache, payload cache, new service or dependency was introduced.

The remaining 8 opens cost 2.43–2.63 ms per profiled check, alongside strict path
validation, final signatures and proof parsing. Removing those checks or retaining
directory authority across requests solely to save the remaining 1–2 ms would
change the reviewed integrity/access design. No observed user workflow requires
that escalation. The corrected 10-ms mean bounds measured normal behavior with
modest room for NFS scheduling variation; 50 ms covers actual source hashing on
admission/eviction with the same required guards. Neither is a cold-storage SLA or
permission to add unbounded work.

## Wider state impact and limits

`production.get_state` performs one rainfall source check normally, and can perform
a second when historical results require another model/frequency/policy snapshot.
Its upload-only source check does not validate CLI lineage. Increasing the allowed
settled component mean by 5 ms therefore adds at most **10 ms of allowed mean work**
to these existing call paths. Historical whole-state measurements were 213 ms
and 695 ms warm (`state_performance.json` and `state_performance_admission.json`).
The allowance difference is approximately 4.7%/1.4% of those observations. This is
a scale comparison, not a matched before/after measurement or proof of current
whole-state performance. Cold/evicted allowance likewise remains separate from
whole-project source admission.

The UI refresh is event-triggered with a 150-ms debounce, not a new fixed-rate
poll loop. This amendment changes neither refresh frequency nor owner/raster/
artifact work. The existing full-state and restarted browser/RQ acceptance gates
remain required and may reject a wider regression even if this component passes.

Keep byte/check invariants: no settled full CLI or Parquet payload rereads; bounded
coherent footer/framing reads; one selected CLI digest check in the standalone
lineage predicate; unchanged existing digest admission and 512-entry bounds.
Export must continue preserving rows/types, modes, owner selection and retained
attempt outcomes. These invariants prevent the more realistic latency budget from
becoming an allowance for repeated parsing, producer work or weakened authority.

## Final implemented gate

The isolated rerun uses the same actual benchmark under new
`cli_lineage_implementation_performance_budget_revision.json/.log` names. It
includes real copied Climate owners, publication-time getInstance, actual native
producers, predicate cold/admission/settled checks and three real 512-entry eviction
cycles per mode. Unique QA runids avoid named status channels; source files are
read-only and generated data remain disposable. Production module hashes include
the changed rainfall opener. Original failure records are retained unchanged.

**Final implemented performance gate: PASS.** The [acceptance record](cli_lineage_budget_acceptance.json)
binds the exact [final JSON](cli_lineage_implementation_performance_budget_revision.json)
by SHA-256; the adjacent [log](cli_lineage_implementation_performance_budget_revision.log)
retains execution. Both cases have unchanged start/end production module hashes.

| Actual mean / observed stage mean | 46 years | 120 years |
| --- | ---: | ---: |
| Settled predicate, 100 calls | 4.85 ms | 6.14 ms |
| Maximum cold/admission stage mean | 13.79 ms | 26.35 ms |
| Evicted predicate, 3 actual pressure cycles | 14.69 ms | 27.86 ms |
| Full export, warm owner, 3 calls | 394.14 ms | 876.46 ms |
| Full export including owner rehydration | 424.26 ms | 894.58 ms |
| Added warm export cost over original producer | 56.43 ms | 66.16 ms |

Every settled predicate check performs one CLI digest check, zero CLI payload
reads and 65,548 footer/framing bytes. Actual eviction filled both production
caches to 512. Both producers preserve exact rows/types; existing output remains
0640 and complete attempts retain 0600 snapshots/status inside 0700 directories.
Named owner inputs remain unchanged and each clone has a distinct QA status
identity. Full output/attempt evidence remains under
`/wc1/batch/qa-cli-lineage-implementation-68217fd84e3e` with its manifest.

CLI-QA-P01 is closed **under the explicitly amended 10/50-ms contract**, not by
claiming the original 5/40-ms gate passed. The original failure and intermediate
profile records remain unchanged. No runtime/test edits were made by the reviewer.
This scoped performance acceptance does not close the package or waive correctness,
security, combined affected tests, full-state, storage or deployed-workflow gates.
