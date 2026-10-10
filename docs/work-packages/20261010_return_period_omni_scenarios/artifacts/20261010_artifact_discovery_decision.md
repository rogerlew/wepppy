# Artifact discovery correction checkpoint

Starting implementation: `d252ff056`. Operator reports missing undisturbed in
`eighty-five-synthetic`, then explicitly states readonly is not intuitive and
will not work. Existing commit/proceed authorization remains in force.

Applicable contracts: return-period-omni-scenarios-contract.md,
controller-contract.md, output-scope-contract.md, existing authorization/CSRF.
Normative delta: remove READONLY completion gate, accept empty/absent metadata
with loss evidence, permit established report staging from existing outputs
for selected writable children. Preserve explicit failed/running exclusion,
readonly editing policy, scope, auth, containment, and no-selection behavior.
Also skip Outlet initialization when its form is absent on report pages.

Evidence: actual child has current loss, EBE and totalwatsed Parquets; wepp.log
records Watershed Run Complete. No READONLY or staged report Parquets; parent's
scenario_run_state is empty. The initial contract was overrestrictive for valid
artifact-backed results. Deck warning separately comes from Project reset.

Compatibility/regression plan: test empty/absent state, same results with/without
marker, source staging on selection, no staging during discovery, missing source,
explicit failures, scope, shared inputs and escaping source/target symlinks.
Exercise real staged generation and CSV using copies of actual project outputs.
Do not alter original run data to manufacture completion. Derived event/rank
schemas and consumers remain unchanged. Test report-page Project bootstrap and
retained Outlet reset when its form exists. High security impact remains under
the package's existing classification; two independent reviews required.

Implementation conformance pending. Reviews and disposition recorded below.

Reviews: contract_correctness approved after correcting storage wording and
explicit staging/retry state rows. contract_security approved; disposition:
include query-engine cache containment, allow legitimate project-contained CLI
links, and do not require optional climate directories. No unresolved high or
medium contract findings. Both reviews read-only, before source changes.
