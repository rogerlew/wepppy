# MOFE input producer audit tracker

**Started:** 2026-11-02 19:32 UTC.  
**Phase:** M1 executing; baselines renewed and contract checkpoint proposed; implementation not started.  
**Last updated:** 2026-11-02 (M1 execution).  
**Security triage:** none for current read-only/documentation scope; re-triage repairs.

## Task board

- [x] Dispatch four read-only audit lanes at the user's request.
- [x] Read package, ExecPlan and documentation standards; scaffold package.
- [x] Reconcile management/PMET audit, including MAN-03 round-trip failure.
- [x] Reconcile other WEPPpy producer audit.
- [x] Reconcile Rust producer/binding audit.
- [x] Reconcile native consumer audit.
- [x] Complete finding-specific repair and acceptance milestones.
- [x] Validate documentation and add root project-board entry.
- [x] Independent scaffold review; reconcile its two documentation findings.
- [x] Incorporate S01 as NATIVE-03 with separate runtime provenance and native acceptance gates.
- [x] Execute M1 container baselines; reproduce failures and run 21 passing focused tests.
- [x] Prepare proposed canonical identity contract and compatibility/regression checkpoint.
- [x] Complete two independent contract reviews and dispositions; both pass design readiness with no unresolved findings.
- [x] Operator ratified MIPA-01 and granted standalone checkpoint commit authority: “approved. proceed”.
- [ ] Record ancestor SHA before implementation.
- [ ] Implement bounded producer repairs, then native verification under separate authority where required.

## Decisions

- **2026-11-02, execution:** User requested execution of this package. Begin M1;
  retain new reproduction evidence and propose exact compatibility choices in
  [MIPA-01](artifacts/20261102_contract_decision.md). Production implementation
  waits for the contract-first ratification/ancestor gate. Native repair,
  deployment and existing-project regeneration remain excluded.

- **2026-11-02 19:32 UTC:** Audit and scaffold only. The user asked to dispatch
  agents and plan repairs; production implementation is not part of this turn.
- **2026-11-02 19:32 UTC:** Separate from the active rock/water program to preserve
  its running tests and scientific scope. No builds, broad tests or shared input
  changes during this audit.
- **2026-11-02 19:32 UTC:** Distinguish crop index from OFE index. PMET lookup is
  crop-based and missing names fall back to the first row; a later OFE can execute
  PMET while receiving unintended coefficients.
- **2026-11-02 19:38 UTC:** Track fourteen entries: eleven producer findings,
  inherited `min_length` ambiguity, and two native prerequisites. MAN-02/03 may
  share a root cause; actual round-trip failure is retained separately until
  isolated. No full native execution or field impact is inferred.
- **2026-11-02 19:38 UTC:** PMET array capacity and adapter mapping must be resolved
  for the selected engine before native acceptance. The missing-row fallback
  already writes the same out-of-bounds indices when crop count exceeds capacity.

- **2026-11-02, S01 incorporation:** At the user's request, add NATIVE-03 as
  the third native dependency (fifteen total entries). S01 confirms wrong-OFE
  FC/HK consumption under both retention policies. Reuse its reviewed evidence;
  do not rerun experiments or reclassify it as a producer defect. Correct generated
  inputs do not prove correct native consumption. Native repair still requires
  separate authorization; COR-S01-01 and the general-release HOLD remain open.

## Evidence and limitations

See [audit findings](artifacts/audit_findings.md). Baseline source revisions:
WEPPpy `41c8b53cfe93f9657a0ce53f602e3e134b48d172`, wepppyo3
`4d4c075421c4013cba99a0addc76482229e7f3f7`, native wepp-forest
`04f1c4d26bcef217009c124151f877dcbf3985cb`. These identify HEAD, not clean trees:
concurrent work is present, so retain source hashes for later reproductions.

Four reports and isolated repro scripts are retained in `artifacts/`. Actual
management writer artifacts and installed Rust writer artifacts include manifests;
Python soil override reproduction is a deliberately isolated AST-method probe.
The prior native PMET reader probe returned distinct pairs for two named crops
and the first pair for an absent crop. That proves reader behavior, not a complete
MOFE simulation. No implementation, deployment or project repair is claimed.

S01 runtime evidence binds the separate release checkout
`/workdir/wepp-forest-release-20261009` at
`d2e14d96af5942409c9a315dc8594fcc164a702a`, not the audit's `04f1c4d...`
reference. See [NATIVE-03](artifacts/native_contract_audit.md#native-03-fchk-consumers-use-another-ofes-coefficients)
for authoritative links and limits. Rock/water authorized local closeout is
complete; native correctness and its package closure remain HOLD. No shared
artifact change is needed to incorporate this dependency.

## Next handoff

Current execution handoff: both independent reviews of the
[proposed checkpoint](artifacts/20261102_contract_decision.md) pass. Obtain operator
ratification/commit authority, then commit only its scoped files. No contract
ancestor exists yet. Continue M2/M3 after recording its SHA here. The older
audit handoff below remains historical context.

Execute M1's contract/reproduction checkpoint only when implementation is
requested, then proceed by bounded repair slice. Coordinate edits/tests with active owners. Preserve existing dirty
files; do not reset, switch branches, rebuild shared binaries or edit the active
rock/water package. A future implementation needs a selected actual project,
native coefficient/OFE evidence and independent correctness review. Track producer
acceptance separately from NATIVE-03 resolution; inspect all confirmed shared
FC/HK consumers and measure repair consequences only after separate native authority.

## Verification and review

M1 execution: 21 focused tests pass, while direct container reproductions retain
PMET/residue/calendar and Rust slope failures. The calendar probe additionally
isolates a single-OFE multiple-rotation serializer/expansion failure. Package
doc-lint passes eleven Markdown files; affected schemas/project board pass.
Fourteen Markdown files have valid relative file links, three evidence manifests
verify, and all ten baseline source/fixture hashes remain unchanged. Both contract
reviews pass after disposition; no implementation or native acceptance is claimed.

S01 incorporation validation (2026-11-02): package doc-lint passes all eight
Markdown files with zero errors/warnings. Spelling previews for the five edited
package files produce no changes, and their relative file links resolve. The
project-board entry now includes NATIVE-03 and the current rock/water status.
This update changes documentation only; no native runs or regression suites ran.

`wctl doc-lint --path docs/work-packages/20261102_mofe_input_producer_audit`
passed for all eight Markdown files with zero errors/warnings, including the
final reconciliation check at 2026-11-02 19:38 UTC. `uk2us` preview of all eight
files returned no changes. `git diff --check` on the package and root tracker
passed. No broad test suite ran; this turn changes documentation and retained
audit probes only.

Independent agent `review_scaffold` found no blocking scope/safety issue. Its two
medium documentation findings were adding MAN-03 to the primary register/count
and updating stale tracker status; both are addressed. This is scaffold review,
not production correctness or security approval.

Remaining repair gates: authoritative contract updates; native capacity and
observation disposition; NATIVE-03 ownership resolution; real 9005 consumer selection; copied actual-project
acceptance; applicable focused/broad regressions; implementation correctness/QA;
security review if file/path/route boundaries change; and ADRs for parameterization
or fallback changes. Deployment and affected-project recovery remain separate.
