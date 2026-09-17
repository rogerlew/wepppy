# PF-R02 CLI producer lineage checkpoint

Starting revision: `0f2826a25`. Proposed; implementation pending.
Authorization: operator requested execution of the freshness package, including
confirmed producer/consumer defects, additive provenance and ancestor commits.
No production deployment or named-project mutations are included.

Canonical delta: `docs/schemas/climate-parquet-lineage-contract.md` and the
post-fire `docs/production_m1.md` publication verification rule and specification
link. The RUSLE specification peak-intensity compatibility section remains
unchanged: all columns, types, aliases and scientific semantics are preserved. This is an
intended readiness and publication behavior change. Ten retained actual producer
probes show same-size restored-mtime edits and parse-time source/selection changes
can leave old rows ready; native PyArrow write failure removes prior output.

Bind source identity to rows in embedded metadata after parsing a retained
verified snapshot. A separate sidecar would introduce mismatched generations.
Independent hashes of today's CLI and old Parquet do not prove producer lineage.
The second interchange producer receives the same publication guarantee without
changing its existing calendar-only fast path or selection precedence.

Proofless legacy stays readable for reports/calendar/history, but does not prove
new post-fire readiness. Normal climate regeneration establishes provenance;
state polling never rebuilds or blesses legacy rows. This is the narrow fail-safe
replacement for the failed-export mtime guard, not a global legacy read ban.
Existing result-currentness checks remain independent. No parameterization,
queue wiring, source selection defaults or table columns change.

Security: preserve existing source/output links and modes and stricter post-fire
path authority; attempts retain source copies without broadening access.
Read/parse/write failures preserve prior output at export entrypoint only.
Earlier build-router directory cleanup is excluded. Cross-filesystem linked
output is an acceptance risk, not authorization for a new staging topology.

Regression and downstream plan are in the canonical contract. Independent
correctness/security review and measured full-path budget are required before
checkpoint commit and implementation. All review findings must be dispositioned.

Review refinements: history lives under visible project-root
`climate_artifacts/cli_parquet/attempts/` because normal climate rebuild removes
its working directory. Preserve this exact artifact module through skeletonize
and canonical archive/restore, without modifying build cleanup behavior. Final
selection reloads the owner (interchange repeats its own hint/fallback). Preserve
uncaught parser error propagation; failed redundant exports do not revoke matching
older proof. Strict bounded proof parsing and same-generation footer/inventory
checks include content=False finalizers. Existing MAX_TEXT bounds apply, without
changing scientific parameterization. Bounded footer reads remain permitted on
settled polls; zero full digest/payload rereads is the performance requirement.

Measured budget ratified from QA's two real copied CLI records (46/120 years,
1.18/3.11 MB): lineage readiness <=5 ms settled / <=40 ms cold or evicted;
full 120-year snapshot+export+metadata+publication <=1.5 s, added lineage <=200 ms.
Prototype measured settled1.25–1.44 ms, cold~12 ms, composed export~0.91 s,
added~101 ms. Bounded footer reads are included; full project sources/owner/raster
checks are separate existing state acceptance. No physical cold-storage claim.
Both independent reviews pass the behavior after refinements. Final implementation
must demonstrate these budgets, resource retention and runtime acceptance.

Implementation follow-up: the above5/40-ms approval records the original
prototype checkpoint. Actual strict-path measurements failed it. The explicit
[budget amendment](cli_lineage_budget_amendment.md) and
[independent QA ratification](cli_lineage_performance_contract_qa.md) correct the
component means to10/50ms, retaining the original miss and all access, payload,
export and runtime gates. Final implemented measurements remain separately
identified; the prototype is not retrospectively relabeled as complete.
