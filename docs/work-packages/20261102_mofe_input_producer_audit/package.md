# MOFE input producer audit and repair

**Status:** Closed — authorized producer/native repairs and reference-preserving 9005/RAP acceptance complete; local revision 7 delivered and native release pushed. Explicit inherited limitations remain documented.
**Started:** 2026-11-02 19:32 UTC.
**Owner:** WEPPcloud maintainer; Codex coordinates the requested audit.

## Current execution and acceptance

The operator authorized MIPA-01 producer repair, MIPA-02 native ownership repair,
and MIPA-03 specialized 9005/RAP compatibility. The final scientific choice is
“preserve reference. that is anurag's domain”, recorded in
[ADR-0134](../../adrs/ADR-0134-specialized-revegetation-reference-port.md).
The [specialized consumer contract](../../schemas/specialized-revegetation-consumer-contract.md)
is the durable authority; the [MIPA-03 execution report](artifacts/20261103_specialized_consumer_execution.md)
records exact artifacts, consumer tests, complete configured workflow and residuals.

Native 1,750 tests, 31 watchlist cases, exact ordinary controls/observer parity,
actual matched routing and a 72-hill/235-OFE/35-year configured workflow pass.
Independent correctness, QA and security reviews pass. Security triage is **high**
for input file publication; the dedicated
[security review](artifacts/mipa03_implementation_security.md) records findings,
closure and actual service-identity evidence. The reviewed PDF/manifest were delivered with exact HTTPS bytes/MIME verified;
segmented broad Python validation is complete. No deployment or executable-default switch.

The inherited disturbance-age graphics overflow is explicitly retained under
reference/output-format preservation. All emitted water values and other graphics
fields are finite; no claim that all graphics cells are numeric is made. Reference
canopy, root-depth and logarithm behavior remains the scientific owner's domain.
Installed Rust promotion, Windows, field calibration, unresolved historical Roads
magnitude and bulk existing-project regeneration remain outside this package.

## Historical scaffold and earlier authority

The remainder preserves original audit planning and earlier milestone context.
Statements restricting native edits or marking findings open below describe the
original scope; the current execution section and milestone reports supersede them.

### Original purpose and scope

The user approved execution and MIPA-01; ancestor `4579b11ce` precedes repairs.
The [execution report](artifacts/20261102_producer_execution.md) records current
validation and limits. The [MIPA-01 checkpoint](artifacts/20261102_contract_decision.md) records accepted
calendar, crop-identity and slope compatibility decisions, renewed failing
baselines, and the contract-first ratification/ancestor gates. The operator now
authorizes MIPA-02 native correction and revision 6 of undeployed 261029 under the
[native checkpoint](artifacts/20261102_native_contract_decision.md). Deployment
and existing-project regeneration remain separately authorized work.
The audit-only scope described below is the original session's provenance.

Multiple overland flow elements (MOFEs) represent successive parts of a hillslope.
Every element must receive its intended soil, slope and management, and its
current crop must resolve to the intended Penman–Monteith coefficients. A
successful WEPP run does not prove that these input identities were preserved.

The user requested parallel audits of WEPPpy and wepppyo3 input producers and a
work-package scaffold addressing the confirmed `pmetpara.txt` coverage gap and
other supported findings. The original session authorized diagnosis and planning,
not production fixes. Four audit lanes covered management/PMET, other Python input
producers, Rust producers/bindings, and native consumer contracts.

The initial defect is that `get_plant_loop_names()` selects only `plants[0]`
from each management file. WEPP reads PMET coefficients by crop name, and an
unmatched crop receives the first PMET row. This is not an engine restriction to
OFE 1: later OFEs still execute PMET, potentially with unintended coefficients.

The reconciled audit also identifies residue-reference and rotation-calendar
defects, first-OFE soil-field selection, lexical RAP cover ordering, and invalid
Rust slope emission. Fifteen register entries comprise eleven producer findings,
one inherited API ambiguity and three native dependencies; the two calendar findings
may share a root cause that is not yet isolated. Evidence strength and
runtime limits are explicit for each entry; this is not an exhaustive producer
or deployed-project census.

Native prerequisites are material: the inspected source accepts 20 plant
scenarios but allocates six PMET coefficients, and its process-probe coefficient
index differs from EVAPPM's actual crop index. Do not claim a producer-only repair
is sufficient, or treat current probe output as authoritative without resolving
these dependencies for the exact selected binary.

NATIVE-03 incorporates S01's runtime-confirmed cross-OFE FC/HK ownership defect
as a downstream dependency. Correctly produced heterogeneous soil inputs can still
reach calculations that use another OFE's coefficients. Reuse the reviewed S01
evidence; keep producer acceptance separate from native ownership acceptance.
The finding remains open and native repair requires separate authorization.

## Deliverables

- [Audit findings and coverage](artifacts/audit_findings.md), separating confirmed
  source defects, reproduced behavior, risks, and unexamined surfaces.
- [Living implementation plan](prompts/completed/implementation_execplan.md) with
  bounded repair milestones and generated-artifact acceptance.
- [Tracker](tracker.md) with decisions, outstanding validation and handoff.
- Future repairs and independent correctness review after implementation is
  authorized; no remediation completion claim from this scaffold.

## Complexity budget

Reuse the current Python/Rust producers, management and soil parsers, existing
NoDb preparation services and native readers. Start with complete crop discovery
and faithful preservation of element identity; demonstrate actual writer output
before considering a larger change. No new dependency, service, queue, datastore,
privilege or deployment topology is permitted. Escalation requires retained
evidence that a bounded repair fails the real acceptance condition.

Do not change hydrological formulas, FC/WP policies, management defaults, native
fallback rules, uploaded inputs or existing project state as part of this audit.
Native code is a consumer reference, not an authorized repair target. Coordinate
with shared-artifact owners before any code edit or test execution.

## Generated artifact validation gate

Applicable to future repairs. Highest supported claim today: **diagnosed**, with
finding-specific confidence in the audit register. Acceptance follows intent and
reloaded durable state through generated MOFE intermediates, staged executable
files, native crop/OFE readback, fresh outputs and the corresponding report.
Capture relative-path hashes and semantic identities at every applicable stage.
Exercise the real producer and staging boundary without replacing it with mocks.

Use a copied actual heterogeneous MOFE project in a production-equivalent worker
environment, plus small discriminating fixtures. Record the chosen project and
exact binaries before execution; none is selected yet. Match native crop name
semantics, not row number. Require distinct crops on downstream OFEs and rotation
changes, and a single-OFE control. A file-existence assertion, green test suite or
model success banner cannot substitute for coefficient and element readback.

For NATIVE-03, compare each OFE's initialized FC capacity and HK exponent with
the operands actually consumed by drainage/percolation. Use distinct materials,
a repeated-material control, both retention policies and an actually executed
unsaturated HK branch. A later authorized native repair must assess all confirmed
shared consumers and quantify before/after runoff, drainage, storage and ET;
producer-only success cannot close the native finding.

## Compatibility and review gates

Preserve public APIs, run-scoped schemas, filenames, OFE ordering and legitimate
single-OFE/legacy behavior. Before future data/schema mutations, write a concrete
compatibility/regression plan and update the canonical contract outside this
package. Scope affected NoDb/UI-coupled changes under the contract-first standard.
Promote accepted durable rules before package closure.

Independent correctness review is required before implementation closeout, using
`docs/prompt_templates/correctness_review_template.md`. Security triage for this
read-only audit and documentation scaffold is **none**; no dedicated security
artifact is required now. Re-triage before implementation: changes to file/path,
upload, queue or subprocess boundaries require the repository's **high** triage
and a dedicated security review artifact. Do not infer authorization to change
those boundaries from the audit scope.

Parameterization changes are not authorized. If a proposed repair changes
fallback selection, defaults, thresholds or unit conversions, an ADR with decision
provenance is required before merge. Enumeration fixes must still quantify
previously misassigned coefficients and resulting output differences.

## Success criteria and signals

The scaffold is complete when all four audit reports are reconciled, concrete
findings have repair/acceptance tasks, uncovered surfaces are explicit, and docs
validation is retained. The repair package remains open until all confirmed
in-scope defects pass direct producer-to-consumer verification and independent
review, or receive an explicit documented disposition.

Health signals are complete crop lookup, consistent OFE identities/counts, and
preserved unaffected inputs. Danger signals are first-row PMET fallback for a
supported generated crop, mismatched element counts, silent truncation, or tests
that only assert file presence. No temporary mitigation is introduced. The
observation window for future repair covers regeneration, staging and one complete
representative native history; deployment and affected-run recovery are separate.

## Related work

The [rock/water program](../20261101_rock_water_development/package.md) completed
authorized local delivery, validation, commits and private retention. Native
correctness, general release and package closure remain HOLD for COR-S01-01.
Its [S01 final disposition](../20261101_rock_water_development/artifacts/S01-final-disposition.md)
and [correctness review](../20261101_rock_water_development/artifacts/20261102_correctness_review.md)
remain the evidence authority for NATIVE-03; this package does not reopen or
modify that evidence. Its runtime source is the separate release checkout at
`d2e14d96af5942409c9a315dc8594fcc164a702a`, not this audit's native reference
checkout at `04f1c4d26bcef217009c124151f877dcbf3985cb`.
The durable [whole-soil ownership contract](../../schemas/whole-soil-water-capacity-contract.md#known-native-coefficient-ownership-defect)
retains the adoption boundary. This package concerns MOFE identity through native
consumption; incorporation authorizes documentation and planning, not native
repair, retention-law adoption, deployment or existing-project regeneration.

Repository standards: [artifact validation](../../standards/generated-artifact-validation-standard.md),
[failure-class assessment](../../standards/hardening-lifecycle-standard.md#2a-failure-class-assessment-required),
and [contract-first changes](../../standards/contract-first-change-standard.md).
Existing contracts to extend before implementation are the
[MOFE management artifact contract](../../schemas/mofe-management-artifact-contract.md)
and [Disturbed mapping contract](../../schemas/disturbed-mofe-mapping-contract.md).
