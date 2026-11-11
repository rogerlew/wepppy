# Correctness and user-experience review - Dependency security gate

## Metadata

- **Reviewer**: independent `reviewer` agent, `/root/m0_correctness_review`
- **Date**: 2026-11-11 UTC
- **Source revision**: `2041fb8e267de3a1572d9fb4f4a62e725b75cc91`, dirty worktree
- **Scope**: M0 policy design; no evaluator/deploy-hook implementation exists
- **Canonical intent**: scope/policy artifact, especially Disposition Policy,
  Gate Behavior, and Ratified M0 policy; active ExecPlan M0-M4
- **Related reviews**: `20261110_operations_review.md`,
  `20261110_scanner_evaluation.md`, `20261110_security_review.md`
- **Gate status**: M0 checkpoint accepted after retained-evidence readback on
  2026-11-11; M1 and M4 final correctness review remain open.

## M0 Findings and Resolution

| ID | Severity | Finding | Resolution | Status |
| --- | --- | --- | --- | --- |
| COR-M0-01 | Medium | The disposition list included `Blocked follow-up`, while the original Critical/High rule prohibited merely undispositioned findings. A migration ticket could be mistaken for approval; advisory-only alias merging could apply one exception across different installations. | Concrete M0 proposal now explicitly keeps follow-up blocking without separate accepted risk, binds aliases to ecosystem/package/version/path, and rejects duplicate/conflicting exception records. | Resolved in proposed design; implementation tests pending |
| COR-M0-02 | Medium | The phrase *newly built common image* left retained rollback, batch-derived images, and worker-only presets ambiguous. Flag-based detection could skip a candidate or reject unrelated CAP repair. | Concrete M0 proposal now names full/web/worker/fork/archive/batch-derived activation, retained rollback evidence or accepted-risk requirements, CAP-only exclusion, and an immediate preactivation image-ID recheck. | Resolved in proposed design; implementation tests pending |

The reviewer reread the amended policy after reporting these findings. No open
High/Medium correctness ambiguity remained at that design review. That review
did not approve numeric freshness/retention limits, establish storage or runner
capacity, accept a vulnerability, or authorize production deployment. The later
M0 checkpoint below records completed baseline, tool and owner prerequisites;
deployed operation and retention qualification remain later gates.

The small Redis trial supports limited Debian-tool capability. Its findings are
not F6 common-image findings. This review reads the scanner evaluation's scoped
claims; it does not independently certify its raw trial files. No runtime
operation or production action was performed by this reviewer.

## Valid States and Operator Errors

These states are separate from command/input combinations; none is currently
claimed exhaustively tested.

| State | Valid state? | Required behavior | Direct evidence still required |
| --- | --- | --- | --- |
| Evidence absent on first candidate | Expected initial state | Generate evidence; fail before activation if generation fails | Real archive scan and missing-tool/database control-flow tests |
| Complete inventories, zero findings | Yes | Pass identity, coverage, freshness and policy checks | Positive fixture and reconciled candidate readback |
| Empty/truncated report or missing Python/Debian inventory | No approval evidence | Explicit schema/coverage failure; empty inventory is not a clean scan | Separate null/empty/missing-section fixtures |
| Findings with reviewed not-affected evidence or valid accepted risk | Conditional | Evaluate every occurrence and retain owner/expiry | Alias, multiple-version/path and approved-exception fixtures |
| Findings awaiting migration | Expected unresolved state | Block until an eligible separate accepted-risk record applies | Negative follow-up case and matching approved-risk control |
| Retained older image selected for rollback | Valid operator intent | Apply explicit rollback policy, with current evidence and exception checks | Retained image and fake activation ledger |
| CAP-only repair | Yes | Existing CAP workflow independent of common-image scanner availability | Scanner-absent excluded-mode test |
| Worker-only or batch-derived common image | Yes | Discover selected artifact without requiring `weppcloud` service | Rendered Compose variants and exact-ID fixtures |
| Malformed exception, conflicting duplicates, unknown severity/schema, changed image | No approval evidence | Bounded failure, retained receipt, running stack untouched | Negative policy cases and no-stop/down/up ledger |
| Exception/evidence at expiry boundary or future timestamp | Conditional | Deterministic UTC boundary; revalidate freshness before activation | Just-before/equal/just-after, skew and long-scan tests with fixed clock |

Input coverage must separately exercise full/web/worker/batch/CAP modes,
overlay/rollback selection, scanner/database availability, and tag mutation
during scanning. Operator errors should name the failed category, image, private
receipt location, and recovery action without displaying rendered environment.
Disk/permission/retention failures leave incomplete evidence and must not start
cutover. Retry produces fresh evidence without overwriting an accepted receipt.

## Generated Artifact Evidence Chain at Initial Design Review

| Stage | Required semantics | Current review result |
| --- | --- | --- |
| Intent/source | Resolved deployment set and exact build inputs, including dirty-source provenance | Proposed; revision alone cannot identify local modifications |
| Persisted candidate | Immutable image ID and resolved tag mapping | Common-image acceptance pending |
| Generated reports | Parse schemas, image identity, inventories, occurrence dispositions and DB identity | Limited Debian fixture described; Python/common-image coverage pending |
| Prepared input | Candidate requirement/lock readback, static-builder lock binding, emitted assets, test-image base identity | Pending M1/M4 |
| Execution | Same database bytes used by scan; exact required tests in declared candidate runtime | Pending; scanner exit zero does not mean policy approval |
| Activation/user outcome | Final selection still matches, containers consume that ID, changed user workflows remain valid | Pending M3-M5; separate rollout authority required |

At initial review the supported claim was **M0 design reviewed**, not implemented
or environment validated. Source/documentation checks cannot prove production
identities, mounts, filesystem permissions or availability. Retain direct tests
of each writer/consumer and the actual candidate; fake command ledgers supplement
that evidence rather than replace it.

Raw security inventories are operator artifacts under the protected
retention contract, not project-run artifacts for browse UI exposure. Preserve
private receipt discoverability and hash-linked review summaries. Actual
deployed retention/storage qualification remains pending; owner ratification and
local storage readback are recorded in the final M0 checkpoint below.

## User and Operator Goal

Users retain working authentication, project access, model execution, artifact
viewing, and reports after compatible security upgrades. Operators receive an
accurate, actionable candidate gate that leaves the known-good stack running
when evidence is missing or a finding blocks promotion.

## Required State Matrix

| State | Expected behavior | Required evidence |
| --- | --- | --- |
| No findings | Gate passes only with fresh image-bound reports | Direct candidate gate |
| Blocking finding | Gate fails before any service stop/recreate | Failure-path deploy test |
| Missing/stale report | Explicit failure names missing identity/freshness | Contract test |
| Approved unexpired exception | Gate passes and records owner/expiry | Policy fixture |
| Expired/malformed exception | Gate fails explicitly | Negative policy fixture |
| Ordinary login/session | Existing auth/session behavior remains valid | Focused route/browser smoke if auth deps change |
| OAuth success/failure | Provider flow and negative validation remain correct | Focused OAuth tests if changed |
| Hostile parser input | Existing rejection/output-safety behavior remains intact | Parser-specific tests if changed |
| Existing/legacy run | Browse, reports, RQ, and model preparation remain usable | Relevant focused tests plus full suite |
| Empty/optional feature | No new import/startup failure from absent optional state | Startup/import controls |
| Native/geospatial boundary | Python/system ABI and representative artifact semantics match | No-cache build and direct readback |
| Frontend lock | Clean build, lint, and all primary npm tests pass | Exact lock hash and command receipts |

## M4 Required Review Checks

- [x] Pre-change full pytest and npm baselines are retained and hash-verified.
- [ ] Each dependency batch has focused valid and failure-path evidence.
- [ ] The common image rebuilds without cache and exposes reviewed versions.
- [ ] The SBOM and scan reports describe that same image.
- [ ] The test image derives from the reviewed common-image candidate.
- [ ] `wctl run-pytest tests --maxfail=1` exits zero after final changes.
- [ ] `wctl run-npm lint` and `wctl run-npm test` exit zero after final changes.
- [ ] No segmented or diagnostic run is substituted for a required full gate.
- [ ] Gate failure leaves the currently running production stack untouched.
- [ ] Resolved M0 design findings have direct implementation regressions.
- [ ] Final image and freshness checks run before activation, including long
      scan and changed-tag cases.
- [ ] Status claims distinguish local validation, environment validation, and
      deployment.

## M0 Baseline Test Repair Review

Reviewed the bounded diff in
`tests/weppcloud/test_usersum_template_wiring.py` after the primary agent reported
that the full baseline failed on its obsolete `runsTtlDeletionHelpUrl` assertion.
The canonical
`docs/ui-docs/contracts/runs-catalog-ttl-deletion-contract.md#presentation-contract`
requires one panel-level **How to keep your project** link using the specified
Usersum document ID. `wepppy/weppcloud/templates/user/runs2.html` already places
that link above the table controls; no runtime/template change is needed.

The replacement assertions require that exact anchor once and the document ID
once. They preserve the endpoint/document wiring check and detect duplication,
while removing a requirement for a JavaScript global that the current contract
does not require. Existing
`tests/weppcloud/routes/test_runs_catalog_contract.py::test_runs_help_is_once_above_table`
separately checks rendered placement/count and absence of per-row help code.

**Verdict: pass for this test-only repair; no High/Medium findings.** The diff
does not change dependency, authentication, TTL, or application behavior. The
source-string assertion remains sensitive to harmless template whitespace, an
existing test-style limitation rather than a release blocker. This review did
not rerun tests; focused and exact full-baseline receipts remain the primary
agent's validation obligation. Correcting this stale assertion does not convert
the failed full command into a passing baseline or waive its rerun.

## Final M0 Checkpoint Readback

On 2026-11-11, this reviewer independently parsed the private
`m0-20261111T0505/baseline-final/` receipts in the owner-selected store and
recomputed all ten manifest-member hashes and sizes. The manifest SHA-256 is
`321aa988535d4b05b2c3267b894adc28497ba1d41fbc641174992995323c2ba3`.
Its directory is 0700 and its files are 0600. Current requirements, frontend
lockfile and repaired test hashes match the retained `identity.json` values.

The complete `wctl run-pytest tests --maxfail=1` rerun exits zero, with 13,502
passed, 435 skipped and 6,029 warnings. Its command receipt spans
2026-11-11 06:14:22 to 07:17:46 UTC and records 3,803.88 seconds; the pytest
summary reports 3,784.78 seconds inside the wrapper. Both npm command receipts
exit zero; the test log confirms all 124 suites / 1,069 tests passed. The retained
stub-check log reports completeness. No full test was rerun by this reviewer.

The earlier failed full baseline remains retained; the successful rerun follows
the bounded, separately reviewed test repair above. Dependencies and production
behavior were unchanged. These are development-baseline results from recorded
image `sha256:b32d1c74915c7f7235c4f1bd02ff8e25808be7c8bac665e925a01785bc9f9afa`,
not acceptance of the preparatory common image or final dependency candidate.

External approval records bind Roger's policy decision and manual-transfer
clarification to current policy SHA-256
`2c381b5cf53b40278a1145d8bbf32e314647be8328010aaa9005ae414cd4e6be`;
this reviewer verified that current-file hash. ADR-0140 records the durable
decision. The independent security review approves confined Syft 1.57.1 to
Grype 0.121.3 evidence collection after the documented Trivy rejection; that
scoped specialist review supplies tool qualification, not production coverage.

**M0 checkpoint verdict: pass for proceeding with M1**, with no unresolved
High/Medium correctness findings at this boundary. Preserve the checkpoint
revision and these receipts. Fresh database evidence, common-image/native
coverage and advisory dispositions remain M1 work; candidate runtime testing,
manual CI evidence transfer, activation ordering and production-equivalent
validation remain M3/M4 gates. No stale database exception, risk acceptance,
production readiness or rollout approval is created by this verdict.

## Verdict

M0 checkpoint: **pass**, unresolved correctness findings High 0 / Medium 0.
The owner, full baseline and scoped scanner prerequisites are retained as
described above; later artifact and operational evidence remains open.

M4 final correctness: **pending**. Closure requires implementation-specific
independent review, every changed user/operation boundary to remain valid, all
three broad test commands to pass, and no unresolved High/Medium correctness
finding. This design checkpoint grants no release or deployment recommendation.
